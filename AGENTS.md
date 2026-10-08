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
- **Formulas for Dual Store Panel**:
  - "Đã chuyển" = `self.restore_done_count`
  - "Còn lại" = Number of valid backups currently in source store directory (`curr_src_count`)
  - "Tổng kho" = `curr_src_count + restore_done_count`
- **Connected Device Counter** ("Số thiết bị đang kết nối", "Tổng"): counts devices physically on USB (`trusted_cnt + untrusted_cnt` in `_sync_cards`), NOT `len(self.rows)` — cards of rebooting devices are retained by `RebootTracker`. `lbl_log_dev_info` holds only the number.
- **Restore Allocation Order**: `list_valid_backups` sorts with `backup_sort_key` (numeric folder prefix ascending, unnumbered last, then `Last Backup Date`, then name). Never rely on `os.listdir` order (NTFS is lexical).
- **Resetting Counters**:
  - Clicking the refresh button beside the transfer counters resets `restore_done_count = 0`, syncs to `settings.json`, and refreshes the labels.
