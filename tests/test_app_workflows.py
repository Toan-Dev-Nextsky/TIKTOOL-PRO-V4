import os
import plistlib
import sys
import tempfile
import threading
import types
import unittest
import queue
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import BB_RB  # noqa: E402
from tests.test_tiktool_core import make_backup, read_udid  # noqa: E402
from tiktool_core import CommandResult, RebootTracker, backup_fingerprint  # noqa: E402


def cmd_result(returncode=0, output="", timed_out=False, error=""):
    lines = tuple(line.strip() for line in output.splitlines() if line.strip())
    return CommandResult(returncode, output, lines, timed_out=timed_out, error=error)


class _FakeProcessRunner:
    """Trả về kết quả định trước cho từng lệnh ngoài, ghi lại lệnh đã chạy."""

    def __init__(self, results):
        self.results = list(results)
        self.commands = []

    def run_capture(self, command, timeout=None):
        self.commands.append(list(command))
        if not self.results:
            raise AssertionError(f"Không có kết quả giả lập cho lệnh: {command}")
        return self.results.pop(0)


class _Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


def make_worker_app():
    messages = []
    return types.SimpleNamespace(
        lock=threading.Lock(),
        active_backups=set(),
        active_restores=set(),
        active_activates=set(),
        rows={},
        var_tik=_Value(False),
        var_lite=_Value(False),
        var_patch_backup_lang=_Value(False),
        var_auto_activate_after_restore=_Value(False),
        log=lambda *args, **kwargs: messages.append((args, kwargs)),
        after=lambda delay, callback, *args: callback(*args),
        messages=messages,
        _update_card_progress=lambda *args, **kwargs: None,
        restore_done_count=0,
    )


class BackupWorkflowTests(unittest.TestCase):
    def test_failed_backup_does_not_delete_preexisting_udid_directory(self):
        """Catches failed-job cleanup deleting a valuable previous backup."""
        with tempfile.TemporaryDirectory() as target:
            udid = "TEST-UDID-123456"
            existing = Path(target, udid)
            existing.mkdir()
            valuable = existing / "valuable-data"
            valuable.write_bytes(b"keep me")
            app = make_worker_app()

            with patch.object(BB_RB, "pair_validate", return_value=True), patch.object(
                BB_RB, "run_stream", return_value=(1, ["failed"])
            ):
                BB_RB.App._backup_worker(app, udid, target)

            self.assertTrue(valuable.is_file())
            self.assertEqual(b"keep me", valuable.read_bytes())


class RestoreWorkflowTests(unittest.TestCase):
    def test_failed_restore_does_not_change_source_backup(self):
        """Catches restore preparation patching the stored source Info.plist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store_a = Path(temp_dir, "store_a")
            store_b = Path(temp_dir, "store_b")
            store_a.mkdir()
            store_b.mkdir()
            source = make_backup(store_a, udid="ORIGINAL-UDID")
            before = backup_fingerprint(source)
            app = make_worker_app()

            with patch.object(BB_RB, "pair_validate", return_value=True), patch.object(
                BB_RB, "run_stream", return_value=(1, ["restore failed"])
            ):
                BB_RB.App._restore_worker(
                    app,
                    "TARGET-UDID",
                    source,
                    str(store_b),
                    "A",
                )

            self.assertEqual("ORIGINAL-UDID", read_udid(source))
            self.assertEqual(before, backup_fingerprint(source))
            self.assertTrue(os.path.isdir(source))


class UiThreadTests(unittest.TestCase):
    def test_worker_log_enqueues_without_calling_tk_after(self):
        """Catches worker threads invoking Tk directly through `after()`."""
        ui_queue = queue.Queue()
        written = []
        app = types.SimpleNamespace(
            ui_queue=ui_queue,
            _write_log=lambda *args: written.append(args),
            _append_log_file=lambda message: None,
        )

        BB_RB.App.log(app, "abcdef123456", "hello")

        callback, args, kwargs = ui_queue.get_nowait()
        self.assertIs(callback, app._write_log)
        self.assertIn("abcdef", args[0])
        self.assertIn("hello", args[0])
        self.assertEqual({}, kwargs)
        self.assertEqual([], written)


class ConfirmationScrollerLayoutTests(unittest.TestCase):
    def test_confirmation_grid_defaults_to_three_columns(self):
        """Catches the restore confirmation reverting to a two-column layout."""
        self.assertEqual(3, BB_RB.CONFIRM_GRID_COLUMNS)

    def test_confirmation_scroller_places_bar_beside_canvas_and_resizes_content(self):
        """Catches mapped phones being clipped below the confirmation viewport."""
        calls = []

        class FakeFrame:
            def columnconfigure(self, *args, **kwargs):
                calls.append(("columnconfigure", args, kwargs))

            def rowconfigure(self, *args, **kwargs):
                calls.append(("rowconfigure", args, kwargs))

        class FakeCanvas:
            def create_window(self, *args, **kwargs):
                calls.append(("create_window", args, kwargs))
                return 7

            def configure(self, *args, **kwargs):
                calls.append(("canvas.configure", args, kwargs))

            def bind(self, event, callback):
                calls.append(("canvas.bind", (event,), {}))
                callback(types.SimpleNamespace(width=1234))

            def itemconfigure(self, *args, **kwargs):
                calls.append(("itemconfigure", args, kwargs))

            def bbox(self, tag):
                return (0, 0, 1234, 900)

            def grid(self, *args, **kwargs):
                calls.append(("canvas.grid", args, kwargs))

            def yview(self, *args):
                return None

        class FakeScrollbar:
            def set(self, *args):
                return None

            def grid(self, *args, **kwargs):
                calls.append(("scrollbar.grid", args, kwargs))

        class FakeContent:
            def bind(self, event, callback):
                calls.append(("content.bind", (event,), {}))

        BB_RB.configure_canvas_scroller(FakeFrame(), FakeCanvas(), FakeScrollbar(), FakeContent())

        self.assertIn(("canvas.grid", (), {"row": 0, "column": 0, "sticky": "nsew"}), calls)
        self.assertIn(("scrollbar.grid", (), {"row": 0, "column": 1, "sticky": "ns", "padx": (0, 4)}), calls)
        self.assertIn(("itemconfigure", (7,), {"width": 1234}), calls)


class RebootTests(unittest.TestCase):
    def test_reboot_state_survives_absence_until_expiry(self):
        """Catches polling deleting the reboot lock on the first USB disconnect."""
        tracker = RebootTracker()
        tracker.mark("u1", timeout=30, now=100)

        self.assertTrue(tracker.is_waiting("u1", now=129))
        self.assertFalse(tracker.is_waiting("u1", now=131))

    def test_verified_reconnect_clears_reboot_state(self):
        """Catches stale reboot state hiding a real post-reconnect trust result."""
        tracker = RebootTracker()
        tracker.mark("u1", timeout=30, now=100)
        tracker.clear("u1")

        self.assertFalse(tracker.is_waiting("u1", now=101))


class PipelineTruthTests(unittest.TestCase):
    def run_activate(self, app, capture_results, runner_results, set_language=False):
        runner = _FakeProcessRunner(runner_results)
        with patch.object(BB_RB, "which_tool", return_value="tool.exe"), patch.object(
            BB_RB, "_fixed_ios_exe", return_value="ios.exe"
        ), patch.object(BB_RB, "_ios_usable", return_value=(True, "ios.exe")), patch.object(
            BB_RB, "PROCESS_RUNNER", runner
        ), patch.object(
            BB_RB, "pair_validate", return_value=True
        ), patch.object(BB_RB.time, "sleep"), patch.object(
            BB_RB, "run_capture", side_effect=capture_results
        ):
            result = BB_RB.App._batch_activate_worker(
                app,
                "TEST-UDID",
                set_language=set_language,
                language_preset="ja_JP|ja",
            )
        return result, runner

    def make_app(self, set_language=False):
        app = make_worker_app()
        app.var_set_lang_after_active = _Value(set_language)
        app.var_lang_locale = _Value("ja_JP|ja")
        app.operations = BB_RB.OperationRegistry()
        return app

    def test_batch_activate_fails_when_skip_setup_fails(self):
        """Catches a failed Skip Setup being reported as a fully activated iPhone."""
        app = self.make_app()

        result, runner = self.run_activate(
            app,
            capture_results=[(0, "activated"), (0, "Activated")],
            runner_results=[cmd_result(1, "A cloud configuration is already present on this device")],
        )

        self.assertFalse(result)
        self.assertEqual(1, len(runner.commands))
        self.assertTrue(any("thất bại" in str(args).lower() for args, _ in app.messages))
        self.assertFalse(
            any("hoàn tất thành công" in str(args).lower() for args, _ in app.messages)
        )

    def test_batch_activate_fails_when_tool_is_missing(self):
        """Catches a missing ios.exe on a new machine passing as success."""
        app = self.make_app()

        with patch.object(BB_RB, "which_tool", return_value=None), patch.object(
            BB_RB, "_ios_usable", return_value=(False, "Không tìm thấy ios.exe")
        ):
            result = BB_RB.App._batch_activate_worker(app, "TEST-UDID")

        self.assertFalse(result)
        self.assertTrue(
            any("thiếu công cụ bắt buộc" in str(args).lower() for args, _ in app.messages)
        )

    def test_batch_activate_fails_when_device_stays_unactivated(self):
        """Catches ideviceactivation exiting zero while the iPhone is still unactivated."""
        app = self.make_app()

        result, runner = self.run_activate(
            app,
            capture_results=[(0, "activation ok"), (0, "Unactivated")],
            runner_results=[],
        )

        self.assertFalse(result)
        self.assertEqual([], runner.commands)
        self.assertTrue(
            any("vẫn ở trạng thái unactivated" in str(args).lower() for args, _ in app.messages)
        )

    def test_unconfirmed_skip_setup_is_not_reported_as_success(self):
        """Catches a Skip Setup timeout being logged as a finished activation."""
        app = self.make_app()

        result, _ = self.run_activate(
            app,
            capture_results=[(0, "activated"), (0, "Activated"), (0, "Activated")],
            runner_results=[cmd_result(-1, "", timed_out=True, error="Command timed out")] * 3,
        )

        self.assertFalse(result)
        self.assertTrue(
            any("không có phản hồi xác nhận" in str(args).lower() for args, _ in app.messages)
        )
        self.assertFalse(
            any("hoàn tất thành công" in str(args).lower() for args, _ in app.messages)
        )

    def test_batch_activate_succeeds_when_only_language_step_fails(self):
        """Catches a failed language command blocking an otherwise activated device."""
        app = self.make_app(set_language=True)

        result, _ = self.run_activate(
            app,
            capture_results=[(0, "activated"), (0, "Activated"), (0, "Activated")],
            runner_results=[cmd_result(0, "ok"), cmd_result(9, "language failed")],
            set_language=True,
        )

        self.assertTrue(result)
        self.assertTrue(
            any("lệnh đổi ngôn ngữ đã gửi" in str(args).lower() for args, _ in app.messages)
        )

    def test_webclip_with_no_devices_returns_cleanly(self):
        """Catches the removed refresh() method being called from a worker."""
        app = make_worker_app()
        app._post_ui = lambda callback, *args, **kwargs: None

        with patch.object(BB_RB, "_ios_usable", return_value=(True, "ios.exe")):
            result = BB_RB.App._push_webclip_all(app, "Test", "https://example.com")

        self.assertFalse(result)


class _ImmediateThread:
    def __init__(self, *, target, args=(), daemon=None, **kwargs):
        self.target = target
        self.args = args

    def start(self):
        self.target(*self.args)


class AutoActivateBatchTests(unittest.TestCase):
    def make_app(self):
        messages = []
        app = types.SimpleNamespace(
            lock=threading.Lock(),
            active_restores=set(),
            active_activates=set(),
            auto_activate_queue=[],
            auto_activate_batch_active=False,
            operations=BB_RB.OperationRegistry(),
            log=lambda *args, **kwargs: messages.append((args, kwargs)),
            _update_card_step=lambda *args, **kwargs: None,
            messages=messages,
        )
        app._run_auto_activate_batch = types.MethodType(BB_RB.App._run_auto_activate_batch, app)
        app._start_auto_activate_batch_if_ready = types.MethodType(
            BB_RB.App._start_auto_activate_batch_if_ready, app
        )
        app._auto_activate_launch = types.MethodType(BB_RB.App._auto_activate_launch, app)
        return app

    def test_auto_activate_waits_for_full_restore_batch_then_runs_batch_worker(self):
        """Catches Auto Activate starting one device while another restore is still running."""
        app = self.make_app()
        app.active_restores.add("still-restoring")
        app.operations.begin("u1", "auto_activate")
        app.operations.begin("u2", "auto_activate")
        calls = []
        app._batch_activate_worker = lambda *args, **kwargs: calls.append((args, kwargs))

        BB_RB.App._queue_auto_activate(app, "u1", True, "ja_JP|ja", True)
        BB_RB.App._queue_auto_activate(app, "u2", True, "ja_JP|ja", True)

        with patch.object(BB_RB.threading, "Thread", _ImmediateThread), patch.object(
            BB_RB.time, "sleep"
        ), patch.object(BB_RB, "get_connected_udids", return_value=["u1", "u2"]), patch.object(
            BB_RB, "ideviceinfo_k", return_value="iPhone"
        ), patch.object(BB_RB, "pair_validate", return_value=True), patch.object(
            BB_RB, "AUTO_ACTIVATE_SETTLE_SECONDS", 0
        ), patch.object(BB_RB, "AUTO_ACTIVATE_STABLE_SAMPLES", 1):
            self.assertFalse(BB_RB.App._start_auto_activate_batch_if_ready(app))
            self.assertEqual([], calls)

            app.active_restores.clear()
            self.assertTrue(BB_RB.App._start_auto_activate_batch_if_ready(app))

        self.assertEqual(["u1", "u2"], [args[0] for args, _ in calls])
        self.assertTrue(all(args[3] for args, _ in calls))
        self.assertTrue(all(args[4] == "auto_activate" for args, _ in calls))

    def test_auto_activate_runs_ready_devices_without_blocking_the_whole_batch(self):
        """Catches one disconnected iPhone preventing ready phones from using the manual Batch pipeline."""
        app = self.make_app()
        app.operations.begin("u1", "auto_activate")
        app.operations.begin("u2", "auto_activate")
        calls = []
        app._batch_activate_worker = lambda *args, **kwargs: calls.append((args, kwargs))

        BB_RB.App._queue_auto_activate(app, "u1", False, "ja_JP|ja", True)
        BB_RB.App._queue_auto_activate(app, "u2", False, "ja_JP|ja", True)

        with patch.object(BB_RB.threading, "Thread", _ImmediateThread), patch.object(
            BB_RB.time, "sleep"
        ), patch.object(BB_RB, "get_connected_udids", return_value=["u1"]), patch.object(
            BB_RB, "ideviceinfo_k", return_value="iPhone"
        ), patch.object(BB_RB, "pair_validate", return_value=True), patch.object(
            BB_RB, "AUTO_ACTIVATE_SETTLE_SECONDS", 0
        ), patch.object(BB_RB, "AUTO_ACTIVATE_READY_CHECKS", 1), patch.object(
            BB_RB, "AUTO_ACTIVATE_STABLE_SAMPLES", 1
        ):
            self.assertTrue(BB_RB.App._start_auto_activate_batch_if_ready(app))

        self.assertEqual(["u1"], [args[0] for args, _ in calls])
        self.assertEqual({"u1": "auto_activate"}, app.operations.snapshot())
        self.assertTrue(any("Không thấy lại 1 máy" in str(args) for args, _ in app.messages))

    def test_auto_activate_revalidates_pairing_before_running_pipeline(self):
        """Catches Auto Activate skipping the re-pair that a fresh PC needs after restore."""
        app = self.make_app()
        calls = []
        app._batch_activate_worker = lambda *args, **kwargs: calls.append((args, kwargs))

        with patch.object(BB_RB.time, "sleep"), patch.object(
            BB_RB, "ideviceinfo_k", return_value="iPhone"
        ), patch.object(BB_RB, "pair_validate", return_value=True) as paired:
            app._auto_activate_launch("u1", False, "ja_JP|ja", True)

        self.assertEqual(1, paired.call_count)
        self.assertEqual("u1", paired.call_args.args[0])
        self.assertEqual(["u1"], [args[0] for args, _ in calls])


if __name__ == "__main__":
    unittest.main()
