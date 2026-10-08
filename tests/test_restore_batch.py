import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import BB_RB
from tiktool_core import OperationRegistry, RebootTracker, RestoreBatchGate
from tests.test_app_workflows import make_worker_app
from tests.test_tiktool_core import make_backup, read_udid


class ObservedGate(RestoreBatchGate):
    def __init__(self, udids):
        super().__init__(udids)
        self.waiting = threading.Event()

    def wait(self):
        self.waiting.set()
        super().wait()


class RestoreBatchTests(unittest.TestCase):
    def test_available_devices_excludes_rebooting_and_hidden_cards(self):
        app = self.make_app([])
        app.rows = {'ready': Mock(), 'rebooting': Mock(), 'hidden': Mock()}
        app._reboot_hidden_cards = {'hidden'}
        app.reboot_tracker.mark('rebooting', 135)
        self.assertEqual(['ready'], BB_RB.App._available_udids(app))

    def make_app(self, udids):
        app = make_worker_app()
        app.active_restores.update(udids)
        app.reboot_tracker = RebootTracker()
        app.operations = OperationRegistry()
        for udid in udids:
            app.operations.begin(udid, 'restore')
        app._post_ui = lambda *_args: None
        app._count_restore_done = lambda: None
        app.auto_activate_queue = []
        app._start_auto_activate_batch_if_ready = Mock()
        app._queue_auto_activate = Mock()
        return app

    def test_reboot_waits_for_last_transfer_and_releases_single_usb_slot(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp, 'A')
            dest = Path(temp, 'B')
            source.mkdir()
            backups = [make_backup(source, name=f'{i}_iPhone') for i in range(2)]
            app = self.make_app(['fast', 'slow'])
            gate = ObservedGate(['fast', 'slow'])
            semaphore = threading.BoundedSemaphore(1)
            release_slow = threading.Event()
            slow_started = threading.Event()
            transferred = set()
            reboots = []
            commands = []

            def restore(cmd, on_line=None):
                commands.append(cmd)
                udid = cmd[cmd.index('-u') + 1]
                if udid == 'slow':
                    slow_started.set()
                    if not release_slow.wait(5):
                        raise RuntimeError('test timeout')
                transferred.add(udid)
                return 0, ['Restore Successful.']

            def reboot(cmd, timeout):
                reboots.append((cmd, set(transferred)))
                return 0, 'Restarting device'

            workers = [threading.Thread(target=BB_RB.App._restore_worker,
                        args=(app, udid, backup, str(dest), 'A', False, False, None, True, gate), daemon=True)
                       for udid, backup in zip(['fast', 'slow'], backups)]
            with patch.object(BB_RB, 'SEMAPHORE', semaphore), patch.object(BB_RB, 'pair_validate', return_value=True), \
                    patch.object(BB_RB, 'run_stream', side_effect=restore), patch.object(BB_RB, 'run_capture', side_effect=reboot), \
                    patch.object(BB_RB, 'which_tool', return_value='diagnostics'), patch.object(BB_RB.threading, 'Thread'):
                try:
                    workers[0].start()
                    self.assertTrue(gate.waiting.wait(2))
                    self.assertEqual([], reboots)
                    workers[1].start()
                    self.assertTrue(slow_started.wait(2), 'waiting worker must release USB slot')
                    self.assertEqual([], reboots)
                finally:
                    release_slow.set()
                    for worker in workers:
                        if worker.ident is not None:
                            worker.join(5)
            self.assertTrue(all(not worker.is_alive() for worker in workers))
            self.assertEqual(2, len(reboots))
            self.assertTrue(all(snapshot == {'fast', 'slow'} for _, snapshot in reboots))
            self.assertTrue(all('--no-reboot' in cmd for cmd in commands))
            self.assertEqual(2, app._restore_batch_moved_count)
            self.assertEqual(set(), app.active_restores)
            self.assertEqual({}, app.operations.snapshot())

    def test_failed_member_releases_gate_without_reboot_or_moving_its_backup(self):
        for failure in ('pair', 'prepare', 'transfer', 'exception'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                source = Path(temp, 'A')
                dest = Path(temp, 'B')
                source.mkdir()
                good = make_backup(source, name='1_good')
                bad = make_backup(source, name='2_bad', udid='ORIGINAL')
                if failure == 'prepare':
                    Path(bad, 'Status.plist').unlink()
                app = self.make_app(['good', 'bad'])
                gate = ObservedGate(['good', 'bad'])

                def restore(cmd, on_line=None):
                    if cmd[cmd.index('-u') + 1] == 'bad':
                        if failure == 'exception':
                            raise OSError('USB error')
                        return 1, ['Restore Aborted.']
                    return 0, ['Restore Successful.']

                workers = [threading.Thread(target=BB_RB.App._restore_worker,
                           args=(app, udid, backup, str(dest), 'A', False, False, None, True, gate), daemon=True)
                           for udid, backup in [('good', good), ('bad', bad)]]
                with patch.object(BB_RB, 'SEMAPHORE', threading.BoundedSemaphore(1)), \
                        patch.object(BB_RB, 'pair_validate', side_effect=lambda udid, **_: udid != 'bad' or failure != 'pair'), \
                        patch.object(BB_RB, 'run_stream', side_effect=restore), patch.object(BB_RB, 'run_capture', return_value=(0, '')) as reboot, \
                        patch.object(BB_RB, 'which_tool', return_value='diagnostics'), patch.object(BB_RB.threading, 'Thread'):
                    workers[0].start()
                    try:
                        self.assertTrue(gate.waiting.wait(2))
                    finally:
                        workers[1].start()
                        for worker in workers:
                            worker.join(5)
                self.assertTrue(all(not worker.is_alive() for worker in workers))
                self.assertEqual(1, reboot.call_count)
                self.assertEqual('good', reboot.call_args.args[0][2])
                self.assertTrue(Path(bad).is_dir())
                self.assertEqual('ORIGINAL', read_udid(bad))
                self.assertTrue(Path(dest, '1_good').is_dir())
                self.assertEqual({}, app.operations.snapshot())

    def test_reboot_failure_preserves_successful_transfer_and_skips_auto_activate(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp, 'A')
            dest = Path(temp, 'B')
            source.mkdir()
            backup = make_backup(source)
            app = self.make_app(['u1'])
            gate = RestoreBatchGate(['u1'])
            with patch.object(BB_RB, 'pair_validate', return_value=True), \
                    patch.object(BB_RB, 'run_stream', return_value=(0, ['Restore Successful.'])), \
                    patch.object(BB_RB, 'run_capture', return_value=(1, 'Disconnected')), \
                    patch.object(BB_RB, 'which_tool', return_value='diagnostics'):
                BB_RB.App._restore_worker(app, 'u1', backup, str(dest), 'A', True, False, None, True, gate)
            self.assertEqual(1, gate.reboot_failure_count())
            self.assertTrue(Path(dest, '1_iPhone').is_dir())
            self.assertEqual('u1', read_udid(str(dest / '1_iPhone')))
            app._queue_auto_activate.assert_not_called()
            self.assertFalse(app.reboot_tracker.is_waiting('u1'))
            self.assertEqual({}, app.operations.snapshot())

    def test_batch_members_are_registered_before_any_worker_starts(self):
        app = self.make_app([])
        app.btn_run_conf = Mock()
        app.btn_cancel_conf = Mock()
        app.var_active_store = Mock(get=lambda: 'A')
        app.lbl_path_b = Mock(cget=lambda _: 'B')
        app.var_set_lang_after_active = Mock(get=lambda: False)
        app.var_lang_locale = Mock(get=lambda: 'ja_JP|ja')
        app.pending_restore_map = [('u1', 'backup1'), ('u2', 'backup2')]
        app._begin_operation = app.operations.begin
        app._hide_confirm_frame = Mock()
        snapshots = []
        app._restore_worker = lambda *args: snapshots.append(set(app.active_restores))

        class ImmediateThread:
            def __init__(self, target, args, daemon):
                self.target, self.args = target, args
            def start(self):
                self.target(*self.args)

        with patch.object(BB_RB, 'which_tool', return_value='diagnostics'), patch.object(BB_RB.threading, 'Thread', ImmediateThread):
            BB_RB.App._execute_confirmed_restore(app)
        self.assertEqual([{'u1', 'u2'}, {'u1', 'u2'}], snapshots)


if __name__ == '__main__':
    unittest.main()
