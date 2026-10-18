# Project Knowledge & Developer Guide (TIKTOOL PRO V4)

## Overview
TIKTOOL PRO V4 (`BB_RB.py`) is a Windows Tkinter/ttk desktop application for managing multi-device iOS automation: Dual-store Backup/Restore (Kho A <-> Kho B), Batch Activation, Language configuration, and IPA sideloading via USB.

## Commands & Verification
- **Compile Check**: `python -m py_compile BB_RB.py`
- **Run Unit Tests**: `python -m unittest discover -s tests`
- **Important Note when Running Tests**:
  - Always backup `settings.json` before running tests, as legacy unit tests may write directly to `settings.json` if not isolated with a temporary directory or mock.

## State Persistence & Counters (`settings.json`)
- **Key Counters**:
  - `restoreDoneCount`: Session transfer counter ("Đã chuyển"). Persisted across app restarts in `settings.json`.
  - `dailyRestoreDate` & `dailyRestoreCount`: Daily restore total ("Tổng hôm nay").
  - `hourlyRestoreDate` & `hourlyRestoreCounts`: Hourly restore breakdown & rating.
  - `dailyRestoreCount` must NEVER be derived from `restoreDoneCount` (the latter spans days); load logic lives in `_load_daily_restore_from_settings`.
- **Formulas for Dual Store Panel**:
  - "Đã chuyển" = `self.restore_done_count`
  - "Còn lại" = Number of valid backups currently in source store directory (`curr_src_count`)
  - "Tổng kho" = `curr_src_count + restore_done_count`
- **Connected Device Counter** ("Số thiết bị đang kết nối", "Tổng"): counts devices physically on USB (`trusted_cnt + untrusted_cnt` in `_sync_cards`), NOT `len(self.rows)` — cards of rebooting devices are retained by `RebootTracker`. `lbl_log_dev_info` holds only the number.
- **Restore Allocation Order**: `list_valid_backups` sorts with `backup_sort_key` (numeric folder prefix ascending, unnumbered last, then `Last Backup Date`, then name). Never rely on `os.listdir` order (NTFS is lexical).
- **Available Devices for Batch Operations**: always filter target devices via `self._available_udids()` instead of iterating `self.rows.keys()` directly, so rebooting devices (in `reboot_tracker.is_waiting()`) and absent devices (`_reboot_hidden_cards`) are excluded.
- **Resetting Counters**:
  - Clicking the refresh button beside the transfer counters resets `restore_done_count = 0`, syncs to `settings.json`, and refreshes the labels.

## Performance Card (Updated 2026-10-18)

- The performance card always shows the hour window, hourly device count, star rating, daily total, history button, and daily reset button.
- The scrolling messages, hide/show icons, covering overlay, animation timer, and password prompt for revealing statistics have been removed at the user's request.
- Legacy `performanceStatsHidden` settings are ignored and removed by `_save_settings_from_ui` when saving settings.
- AstroBot status messages are a separate component. The password confirmation for erasing device data is also separate from the removed statistics feature.
- The removal was applied to both `backup/before-refactor-v5-beta` and `backup/before-refactor`; see `CHANGELOG.md` for the change record and verification.
