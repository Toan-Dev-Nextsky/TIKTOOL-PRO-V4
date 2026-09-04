# TIKTOOL PRO V4 Stability and Backup-Immutability Design

## Objective

Fix the confirmed correctness, data-safety, concurrency, subprocess, configuration, and observability defects in TIKTOOL PRO V4 while preserving the existing Windows/Tkinter workflow.

The non-negotiable requirement is that a stored source backup is immutable. The application may read it and may transfer the whole directory between Store A and Store B after a successful restore, but it must never open any file inside that backup for writing, change file contents or metadata intentionally, create a file inside it, or remove a file from it.

## Reference-tool finding

The extracted implementation in `C:\iphone_tool_v2` patches `Info.plist` inside the source backup before restore and moves that same folder after success. It has no rollback on restore failure. TIKTOOL PRO V4 must not copy this unsafe behavior.

The reference tool does avoid one V4 regression: when a backup command fails it reports failure without recursively deleting a pre-existing `<target>/<UDID>` directory.

## Scope

This stabilization covers:

- immutable source backups during restore;
- isolated, app-owned temporary output during backup;
- strict backup validation;
- safe transfer between Store A and Store B;
- per-device operation exclusion and accurate close protection;
- thread-safe Tkinter updates;
- bounded and tracked subprocess execution;
- correct Batch Activate and WebClip outcomes;
- reliable reboot state handling;
- configuration, URL, license, and logging defects identified by the audit;
- headless regression tests that do not require an iPhone.

The visual design and existing user-facing workflow remain unchanged except for clearer failure states and messages.

## Architecture

### Core safety module

Create a focused `tiktool_core.py` module for logic that does not depend on Tkinter:

- immutable backup inspection and fingerprints;
- creation and cleanup of app-owned staging jobs;
- transactional Store A/Store B transfer;
- backup path validation;
- operation registry;
- bounded subprocess execution;
- configuration and license helpers;
- URL normalization.

`BB_RB.py` remains the application entry point and owns the GUI, device cards, user commands, and orchestration.

### Backup immutability contract

For every source backup selected for restore:

1. Validate it read-only. `Status.plist` must already exist and report a finished snapshot. Validation must never synthesize or repair files.
2. Build a deterministic fingerprint from every relative path, file size, and SHA-256 file content.
3. Copy the complete backup to an app-owned staging directory outside the source backup, such as `<source-store>/.tiktool_work/restore-<job-id>/<backup-name>`.
4. Patch only the staged copy's `Info.plist` with the target UDID.
5. Run `idevicebackup2 restore` against the staged copy.
6. Delete only the job-specific staging directory, whether restore succeeds, fails, times out, or is cancelled.
7. Recompute the source backup fingerprint before any transfer. A mismatch is a hard failure: do not transfer the source and report an integrity violation.
8. After a successful restore, transfer the unmodified original directory to the opposite store.

The removed language-patch feature, its hidden Tk variable, its JSON setting, and `patch_backup_language()` are deleted. Language changes happen only through `ios.exe lang` after device activation.

### Transactional store transfer

Source and destination stores must resolve to different, non-nested directories.

- On the same volume, rename the source directory to a unique final destination and verify its fingerprint.
- Across volumes, copy to an app-owned temporary destination, verify the full fingerprint, atomically rename the temporary destination to its final name, and only then remove the source directory.
- A failed or mismatched copy leaves the source untouched and removes only the app-owned temporary destination.
- Name collisions receive a timestamp/sequence suffix without altering contents inside the backup.

Moving or deleting the whole source directory after a verified transfer is part of the existing A/B workflow. No file inside the backup is edited, added, or removed.

### Safe new-backup creation

Each backup operation receives a unique job root under `<target-store>/.tiktool_work/backup-<job-id>` and passes that root to `idevicebackup2`. The command can therefore create only job-owned output.

On success, the generated `<job-root>/<UDID>` directory is strictly validated and moved to its final numbered name. On failure, only that job root is removed. Existing backups in the target store are never used as command output and are never cleanup targets.

### Backup validation

A valid backup requires `Manifest.db`, `Info.plist`, `Manifest.plist`, and `Status.plist`. `Status.plist` must parse successfully and its snapshot state must indicate completion. Read-only inspection ignores `.tiktool_work` and other app-owned staging folders.

### Operation registry

Replace independent active sets with a lock-protected registry keyed by UDID. Only one mutating device operation may own a UDID at a time: backup, restore, activate, language, or WebClip.

The registry rejects repeated button clicks with a clear message. Restore can hand ownership to post-restore activation without creating an untracked close-safety gap. The close dialog reads the registry, so its counts stay correct even when an operation is queued or transitioning.

### Tkinter thread boundary

The main thread owns every Tkinter widget and Tk variable. Workers receive immutable snapshots of required settings when they are started.

Workers send UI events and log entries to a standard-library `queue.Queue`. A main-thread `after()` loop drains the queue and invokes widget callbacks. Workers do not call widget methods, `StringVar.get()`, `after()`, or message boxes directly.

Device metadata commands run in the polling executor. `_sync_cards()` receives completed plain dictionaries and never executes a subprocess on the main thread. Poll results are coalesced so a slow UI cannot accumulate an unbounded callback backlog.

### Subprocess lifecycle

Both captured and streamed commands use one tracked runner:

- resolve the executable before launch;
- register every child process for close handling;
- apply an operation-specific timeout;
- terminate, then kill if required, on timeout or forced close;
- decode output with replacement;
- flush the final unterminated output line;
- return a structured result containing return code, output, timeout state, and error.

No worker may remain active forever because an external executable stopped responding.

### Pipeline correctness

- Batch Activate succeeds only if activate, skip setup, and any enabled language stage succeed. A failed language command produces an overall failure state.
- WebClip takes a device snapshot on the main thread. An empty snapshot displays “no devices” without calling a nonexistent `refresh()` method.
- WebClip participates in the operation registry and close protection.
- `.fun` URLs preserve explicit HTTPS; URLs without a scheme default to HTTPS. Safari/full-screen behavior is independent of transport security.
- The reboot cache retains the card and trusted display while the device is temporarily absent. It expires only after a bounded reconnect window or clears after a verified reconnect.

### Configuration and licensing

- Load `threads` from `apps_config.json`, validate it as an integer, and clamp it to a safe range of 1–8. The current configured value is 4.
- If the configured IPA directory does not exist, use the bundled `ipas` directory and persist the repaired path.
- Remove unused or misleading configuration keys when their associated feature no longer exists.
- Restore machine-bound license validation using the same fingerprint/HMAC behavior represented by the reference tool. Do not log license keys, secrets, or full fingerprints.

### Durable logging

Create one UTF-8 log file per application run under `logs/`. Log writes are lock-protected, redact sensitive values, and include timestamps, shortened UDIDs, command stage, return code, timeout, and integrity failures. The existing UI log remains available through the UI event queue.

## Error handling

- Failure to create or fully copy staging aborts before restore.
- Failure to patch the staged `Info.plist` aborts before restore.
- Restore failure or timeout removes staging only and leaves the source backup byte-for-byte unchanged.
- Source fingerprint mismatch aborts transfer and raises a prominent integrity error.
- Transfer failure preserves the source whenever the destination has not been fully verified.
- Cleanup errors are logged with the exact app-owned path but never broaden deletion scope.
- All recursive deletion helpers reject paths outside a resolved `.tiktool_work/<job-id>` directory.

## Testing strategy

Use Python's standard-library `unittest` so the project gains no runtime dependency. Tests create only temporary directories and fake subprocess/device boundaries.

Required regression coverage:

- a failed backup never removes a pre-existing `<target>/<UDID>` backup;
- cleanup accepts only a job-owned staging path;
- restore modifies the staged copy while the original fingerprint remains identical;
- failed restore leaves the original path and fingerprint unchanged;
- successful same-volume and simulated cross-volume transfers preserve fingerprints;
- incomplete backup without `Status.plist` is rejected and not modified;
- duplicate operations for one UDID are rejected and registry transitions remain tracked;
- workers enqueue UI work instead of calling Tkinter objects;
- captured and streamed subprocesses time out, are tracked, and preserve final output;
- failed language stage makes Batch Activate fail;
- empty-device WebClip exits cleanly;
- HTTPS `.fun` URLs remain HTTPS;
- configured concurrency equals 4 and is clamped for invalid values;
- missing IPA path falls back to the bundled directory;
- license validation accepts the correct machine key and rejects invalid keys without exposing secrets;
- reboot state survives temporary device disappearance and expires deterministically.

## Acceptance criteria

- No production restore code opens any file inside the selected source backup in write, append, update, or delete mode.
- No production restore code creates a file or directory inside the selected source backup.
- A before/after SHA-256 fingerprint proves the original backup is unchanged up to the point of verified whole-directory transfer.
- Every confirmed audit reproduction has an automated regression test that fails on the current code and passes after the fix.
- The complete test suite and syntax compilation pass without warnings or errors.
- No real iPhone or real stored backup is modified during automated verification.

