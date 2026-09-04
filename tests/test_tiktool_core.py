import json
import os
import plistlib
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tiktool_core import (  # noqa: E402
    OperationRegistry,
    ProcessRunner,
    backup_fingerprint,
    check_license_file,
    cleanup_owned_job,
    create_restore_stage,
    load_concurrency,
    make_license_key,
    normalize_url,
    repair_ipas_path,
    redact_log,
    transfer_backup_immutable,
    validate_license_key,
    validate_backup,
)


def make_backup(parent, name="1_iPhone", udid="OLD-UDID", include_status=True):
    backup = Path(parent, name)
    backup.mkdir(parents=True)
    with open(backup / "Info.plist", "wb") as stream:
        plistlib.dump(
            {
                "UniqueDeviceID": udid,
                "Product Version": "18.0",
                "Last Backup Date": "2026-09-04",
            },
            stream,
        )
    with open(backup / "Manifest.plist", "wb") as stream:
        plistlib.dump({"Version": "9.1"}, stream)
    (backup / "Manifest.db").write_bytes(b"sqlite-placeholder")
    data_dir = backup / "ab"
    data_dir.mkdir()
    (data_dir / "abcdef").write_bytes(b"valuable user data")
    if include_status:
        with open(backup / "Status.plist", "wb") as stream:
            plistlib.dump({"SnapshotState": "Finished", "IsFullBackup": True}, stream)
    return str(backup)


def read_udid(backup):
    with open(Path(backup, "Info.plist"), "rb") as stream:
        return plistlib.load(stream)["UniqueDeviceID"]


class BackupSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store_a = self.root / "store_a"
        self.store_b = self.root / "store_b"
        self.store_a.mkdir()
        self.store_b.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_status_is_rejected_without_creating_it(self):
        """Catches validators that mutate an incomplete backup to make it look valid."""
        backup = make_backup(self.store_a, include_status=False)

        ok, errors = validate_backup(backup)

        self.assertFalse(ok)
        self.assertIn("Status.plist", " ".join(errors))
        self.assertFalse(Path(backup, "Status.plist").exists())

    def test_non_finished_status_is_rejected(self):
        """Catches acceptance of interrupted backups whose snapshot never finished."""
        backup = make_backup(self.store_a)
        with open(Path(backup, "Status.plist"), "wb") as stream:
            plistlib.dump({"SnapshotState": "Uploading"}, stream)

        ok, errors = validate_backup(backup)

        self.assertFalse(ok)
        self.assertIn("not finished", " ".join(errors).lower())

    def test_restore_staging_patches_copy_without_changing_source(self):
        """Catches any restore preparation that writes to the stored source backup."""
        backup = make_backup(self.store_a, udid="ORIGINAL-UDID")
        before = backup_fingerprint(backup)

        stage = create_restore_stage(backup, "TARGET-UDID")
        try:
            self.assertEqual(before, backup_fingerprint(backup))
            self.assertEqual("ORIGINAL-UDID", read_udid(backup))
            self.assertEqual("TARGET-UDID", read_udid(stage.backup_path))
            self.assertNotEqual(os.path.realpath(backup), os.path.realpath(stage.backup_path))
        finally:
            cleanup_owned_job(stage.job_root)

    def test_cleanup_rejects_a_real_backup_path(self):
        """Catches broad cleanup code that can recursively delete user backups."""
        backup = make_backup(self.store_a)

        with self.assertRaises(ValueError):
            cleanup_owned_job(backup)

        self.assertTrue(Path(backup, "ab", "abcdef").is_file())

    def test_transfer_preserves_every_file_byte(self):
        """Catches transfers that silently alter backup contents."""
        backup = make_backup(self.store_a)
        before = backup_fingerprint(backup)

        destination = transfer_backup_immutable(backup, str(self.store_b))

        self.assertFalse(os.path.exists(backup))
        self.assertEqual(before, backup_fingerprint(destination))
        self.assertTrue(Path(destination, "ab", "abcdef").is_file())

    def test_source_and_destination_stores_must_differ(self):
        """Catches same-store transfers that report success without moving inventory."""
        backup = make_backup(self.store_a)

        with self.assertRaises(ValueError):
            transfer_backup_immutable(backup, str(self.store_a))

        self.assertTrue(os.path.isdir(backup))


class RegistryConfigTests(unittest.TestCase):
    def test_registry_rejects_overlap_and_tracks_transition(self):
        """Catches duplicate device workers and untracked restore-to-activate gaps."""
        registry = OperationRegistry()

        self.assertTrue(registry.begin("u1", "restore"))
        self.assertFalse(registry.begin("u1", "backup"))
        self.assertTrue(registry.transition("u1", "restore", "auto_activate"))
        self.assertEqual({"u1": "auto_activate"}, registry.snapshot())
        registry.end("u1", "auto_activate")
        self.assertEqual({}, registry.snapshot())

    def test_registry_does_not_end_a_different_owner(self):
        """Catches an old worker clearing the busy state of a newer operation."""
        registry = OperationRegistry()
        registry.begin("u1", "restore")

        registry.end("u1", "backup")

        self.assertEqual({"u1": "restore"}, registry.snapshot())

    def test_concurrency_reads_configured_value_and_clamps_extremes(self):
        """Catches the hard-coded twenty-worker USB overload regression."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Path(temp_dir, "apps_config.json")
            config.write_text(json.dumps({"threads": 4}), encoding="utf-8")
            self.assertEqual(4, load_concurrency(str(config)))
            config.write_text(json.dumps({"threads": 999}), encoding="utf-8")
            self.assertEqual(8, load_concurrency(str(config)))
            config.write_text(json.dumps({"threads": 0}), encoding="utf-8")
            self.assertEqual(1, load_concurrency(str(config)))


class SettingsLicenseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp.name, "app")
        self.base_dir.mkdir()
        (self.base_dir / "ipas").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_explicit_https_fun_url_is_not_downgraded(self):
        """Catches transport-security code that converts HTTPS to HTTP."""
        self.assertEqual(
            "https://example.fun/path",
            normalize_url("https://example.fun/path"),
        )
        self.assertEqual("https://example.fun", normalize_url("example.fun"))

    def test_missing_ipa_path_falls_back_to_bundled_directory(self):
        """Catches stale machine-specific IPA paths surviving startup."""
        settings = {"ipasDir": str(self.base_dir / "missing")}

        changed = repair_ipas_path(settings, str(self.base_dir))

        self.assertTrue(changed)
        self.assertEqual(str(self.base_dir / "ipas"), settings["ipasDir"])

    def test_license_key_is_bound_to_exact_machine_fingerprint(self):
        """Catches the application treating every installation as licensed."""
        key = make_license_key("machine-A")

        self.assertTrue(validate_license_key(key, "machine-A"))
        self.assertFalse(validate_license_key(key, "machine-B"))

    def test_license_file_accepts_valid_key_and_rejects_invalid_key(self):
        """Catches license.json being ignored or compared unsafely."""
        license_path = self.base_dir / "license.json"
        license_path.write_text(
            json.dumps({"key": make_license_key("machine-A")}),
            encoding="utf-8",
        )
        self.assertTrue(check_license_file(str(license_path), "machine-A"))
        license_path.write_text(json.dumps({"key": "invalid"}), encoding="utf-8")
        self.assertFalse(check_license_file(str(license_path), "machine-A"))

    def test_durable_log_redacts_license_keys(self):
        """Catches accidental persistence of machine-bound activation secrets."""
        message = "license=IPTP-abcdefghijklmnopqrstuvwxyz012345"

        redacted = redact_log(message)

        self.assertNotIn("IPTP-", redacted)
        self.assertIn("[REDACTED-LICENSE]", redacted)


class ProcessRunnerTests(unittest.TestCase):
    def setUp(self):
        self.runner = ProcessRunner()

    def tearDown(self):
        self.runner.terminate_all()

    def test_capture_timeout_terminates_and_unregisters_process(self):
        """Catches external tools hanging forever outside close protection."""
        result = self.runner.run_capture(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            timeout=0.1,
        )

        self.assertTrue(result.timed_out)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual({}, self.runner.active_snapshot())

    def test_stream_preserves_unterminated_final_output_line(self):
        """Catches the final subprocess error disappearing without a newline."""
        seen = []

        result = self.runner.run_stream(
            [sys.executable, "-c", "print('tail', end='')"],
            lambda line, is_err=False: seen.append((line, is_err)),
            timeout=2,
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual(("tail",), result.lines)
        self.assertEqual([("tail", False)], seen)
        self.assertEqual({}, self.runner.active_snapshot())

    def test_stream_marks_error_lines(self):
        """Catches streamed failure text being presented as a normal success line."""
        seen = []

        self.runner.run_stream(
            [sys.executable, "-c", "print('operation failed')"],
            lambda line, is_err=False: seen.append((line, is_err)),
            timeout=2,
        )

        self.assertEqual([("operation failed", True)], seen)


if __name__ == "__main__":
    unittest.main()
