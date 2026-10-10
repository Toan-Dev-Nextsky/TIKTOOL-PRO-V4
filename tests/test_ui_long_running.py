"""Long-running UI regressions; use hidden Tk widgets and no device commands."""
import queue
import tkinter as tk
import types
import unittest
from unittest.mock import Mock, patch

import BB_RB


class LongRunningUiTests(unittest.TestCase):
    def test_ticker_reclaims_offscreen_canvas_items(self):
        root = tk.Tk()
        root.withdraw()
        try:
            canvas = tk.Canvas(root, width=300, height=30)
            canvas.winfo_width = lambda: 300
            canvas.winfo_height = lambda: 30
            app = types.SimpleNamespace(
                performance_stats_hidden=True, performance_ticker_canvas=canvas,
                _performance_ticker_items=[], _performance_ticker_last_message=None,
                _animate_performance_ticker=lambda: None, after=lambda *_: 'timer',
            )
            for _ in range(12000):
                BB_RB.App._animate_performance_ticker(app)
            self.assertGreater(len(canvas.find_all()), 0)
            self.assertEqual(set(canvas.find_all()), set(app._performance_ticker_items))
            self.assertLess(len(canvas.find_all()), 10)
        finally:
            root.destroy()

    def test_screen_log_stays_bounded_and_retains_latest_message(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = types.SimpleNamespace(txt_log=tk.Text(root))
            for _ in range(3000):
                BB_RB.App._write_log(app, '[12:00:00] TEST: ' + 'x' * 200 + '\n', False)
            for _ in range(3000):
                BB_RB.App._write_log(app, '[12:00:00] TEST: short\n', False)
            BB_RB.App._write_log(app, '[12:00:00] TEST: LAST MESSAGE\n', False)
            content = app.txt_log.get('1.0', 'end-1c')
            self.assertLessEqual(len(content), BB_RB.UI_LOG_MAX_CHARS)
            self.assertLessEqual(len(content.splitlines()), BB_RB.UI_LOG_MAX_LINES)
            self.assertIn('LAST MESSAGE', content)
        finally:
            root.destroy()

    def test_full_log_saved_before_ui_payload_is_shortened(self):
        app = types.SimpleNamespace(ui_queue=queue.Queue(), _append_log_file=Mock(),
                                    _write_log=Mock())
        payload = 'x' * 100000 + 'END OF RAW OUTPUT'
        BB_RB.App.log(app, 'TEST', payload)
        self.assertIn(payload, app._append_log_file.call_args.args[0])
        _, args, _ = app.ui_queue.get_nowait()
        self.assertLess(len(args[0]), BB_RB.UI_LOG_ENTRY_MAX_CHARS + 100)

    def test_ui_queue_yields_after_slow_callback_without_dropping_work(self):
        calls = []
        app = types.SimpleNamespace(ui_queue=queue.Queue(), after=Mock(),
                                    _drain_ui_queue=Mock(), _append_log_file=Mock())
        for i in range(3):
            app.ui_queue.put((calls.append, (i,), {}))
        with patch.object(BB_RB.time, 'monotonic', side_effect=[0, 1]):
            BB_RB.App._drain_ui_queue(app)
        self.assertEqual([0], calls)
        self.assertEqual(2, app.ui_queue.qsize())
        app.after.assert_called_once()


if __name__ == '__main__':
    unittest.main()
