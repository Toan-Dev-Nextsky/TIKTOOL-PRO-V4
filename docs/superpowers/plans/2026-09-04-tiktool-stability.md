# TIKTOOL PRO V4 Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix every confirmed audit defect while guaranteeing that restore never edits, adds, or removes content inside a stored source backup.

**Architecture:** Add a Tkinter-independent `tiktool_core.py` safety layer for immutable backup staging, transactional transfer, operation ownership, command execution, configuration, license validation, and URL handling. Keep `BB_RB.py` as the GUI/orchestrator, but route worker-to-UI communication through a queue and run restore exclusively from staged copies.

**Tech Stack:** Python 3.11 standard library, Tkinter, `unittest`, `plistlib`, `hashlib`, `shutil`, `subprocess`, `threading`, `queue`.

**Spec:** `docs/superpowers/specs/2026-09-04-tiktool-stability-design.md`

## Global Constraints

- Stored source backups are read-only: never write, append, update, create, or delete anything inside them.
- Restore patches only a complete staged copy outside the source backup.
- Automated tests use temporary synthetic backups and never access a real iPhone or stored backup.
- Runtime dependencies remain Python 3.11 standard-library only.
- Preserve the existing Windows/Tkinter user workflow and current visual styling.
- Preserve unrelated user changes already present in the dirty working tree.

---

### Task 1: Immutable backup primitives

**Files:**
- Create: `tiktool_core.py`
- Create: `tests/__init__.py`
- Create: `tests/test_tiktool_core.py`

**Interfaces:**
- Produces: `validate_backup(path: str) -> tuple[bool, list[str]]`
- Produces: `backup_fingerprint(path: str) -> str`
- Produces: `create_restore_stage(source_backup: str, target_udid: str) -> RestoreStage`
- Produces: `cleanup_owned_job(job_root: str, missing_ok: bool = False) -> None`
- Produces: `transfer_backup_immutable(source: str, destination_root: str) -> str`

- [ ] **Step 1: Write failing tests for strict validation and fingerprints**

```python
class BackupSafetyTests(unittest.TestCase):
    def test_missing_status_is_rejected_without_creating_it(self):
        backup = make_backup(self.temp_dir, include_status=False)
        ok, errors = validate_backup(backup)
        self.assertFalse(ok)
        self.assertIn("Status.plist", " ".join(errors))
        self.assertFalse(os.path.exists(os.path.join(backup, "Status.plist")))

    def test_staging_patch_does_not_change_source_fingerprint(self):
        backup = make_backup(self.temp_dir, udid="OLD")
        before = backup_fingerprint(backup)
        stage = create_restore_stage(backup, "NEW")
        self.assertEqual(before, backup_fingerprint(backup))
        self.assertEqual("NEW", read_udid(stage.backup_path))
        cleanup_owned_job(stage.job_root)
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m unittest tests.test_tiktool_core.BackupSafetyTests -v`

Expected: import failure because `tiktool_core` does not exist.

- [ ] **Step 3: Implement strict read-only validation, fingerprinting, and staging**

```python
@dataclass(frozen=True)
class RestoreStage:
    job_root: str
    backup_path: str
    source_fingerprint: str

def validate_backup(path):
    missing = [name for name in REQUIRED_BACKUP_FILES if not os.path.isfile(os.path.join(path, name))]
    if missing:
        return False, [f"Missing {name}" for name in missing]
    with open(os.path.join(path, "Status.plist"), "rb") as stream:
        status = plistlib.load(stream)
    if str(status.get("SnapshotState", "")).lower() != "finished":
        return False, ["Status.plist is not finished"]
    return True, []

def create_restore_stage(source_backup, target_udid):
    source = _resolved_dir(source_backup)
    work_root = _work_root(os.path.dirname(source))
    job_root = tempfile.mkdtemp(prefix="restore-", dir=work_root)
    staged = os.path.join(job_root, os.path.basename(source))
    shutil.copytree(source, staged, copy_function=shutil.copy2)
    patch_staged_info(staged, target_udid)
    return RestoreStage(job_root, staged, backup_fingerprint(source))
```

- [ ] **Step 4: Add failing tests for cleanup scope and transactional transfer**

```python
def test_cleanup_rejects_non_work_path(self):
    backup = make_backup(self.temp_dir)
    with self.assertRaises(ValueError):
        cleanup_owned_job(backup)
    self.assertTrue(os.path.isdir(backup))

def test_transfer_preserves_full_fingerprint(self):
    source = make_backup(self.store_a)
    before = backup_fingerprint(source)
    destination = transfer_backup_immutable(source, self.store_b)
    self.assertEqual(before, backup_fingerprint(destination))
    self.assertFalse(os.path.exists(source))
```

- [ ] **Step 5: Implement guarded cleanup and verified transfer**

```python
def cleanup_owned_job(job_root, missing_ok=False):
    resolved = os.path.realpath(job_root)
    parent = os.path.dirname(resolved)
    if os.path.basename(parent) != WORK_DIR_NAME or not os.path.basename(resolved).startswith(JOB_PREFIXES):
        raise ValueError("Refusing to delete a non-owned path")
    if missing_ok and not os.path.exists(resolved):
        return
    shutil.rmtree(resolved)

def transfer_backup_immutable(source, destination_root):
    before = backup_fingerprint(source)
    destination = unique_destination(destination_root, os.path.basename(source))
    if same_volume(source, destination_root):
        os.rename(source, destination)
    else:
        temporary = create_transfer_destination(destination_root)
        shutil.copytree(source, temporary, copy_function=shutil.copy2)
        if backup_fingerprint(temporary) != before:
            cleanup_owned_job(os.path.dirname(temporary))
            raise IntegrityError("Destination fingerprint mismatch")
        os.rename(temporary, destination)
        shutil.rmtree(source)
    if backup_fingerprint(destination) != before:
        raise IntegrityError("Transferred backup fingerprint mismatch")
    return destination
```

- [ ] **Step 6: Run Task 1 tests and verify GREEN**

Run: `python -m unittest tests.test_tiktool_core.BackupSafetyTests -v`

Expected: all backup safety tests pass.

---

### Task 2: Operation registry, configuration, URL, and license helpers

**Files:**
- Modify: `tiktool_core.py`
- Modify: `tests/test_tiktool_core.py`

**Interfaces:**
- Produces: `OperationRegistry.begin(udid: str, kind: str) -> bool`
- Produces: `OperationRegistry.transition(udid: str, expected: str, new_kind: str) -> bool`
- Produces: `OperationRegistry.end(udid: str, kind: str) -> None`
- Produces: `load_concurrency(path: str, default: int = 4) -> int`
- Produces: `repair_ipas_path(settings: dict, base_dir: str) -> bool`
- Produces: `normalize_url(url: str) -> str`
- Produces: `machine_fingerprint()`, `make_license_key(fingerprint)`, `check_license_file(path)`

- [ ] **Step 1: Write failing registry and configuration tests**

```python
def test_registry_rejects_duplicate_and_tracks_transition(self):
    registry = OperationRegistry()
    self.assertTrue(registry.begin("u1", "restore"))
    self.assertFalse(registry.begin("u1", "backup"))
    self.assertTrue(registry.transition("u1", "restore", "auto_activate"))
    self.assertEqual({"u1": "auto_activate"}, registry.snapshot())

def test_concurrency_reads_four_and_clamps(self):
    write_json(self.config, {"threads": 4})
    self.assertEqual(4, load_concurrency(self.config))
    write_json(self.config, {"threads": 999})
    self.assertEqual(8, load_concurrency(self.config))
```

- [ ] **Step 2: Run selected tests and verify RED**

Run: `python -m unittest tests.test_tiktool_core.RegistryConfigTests -v`

Expected: missing interfaces fail imports or assertions.

- [ ] **Step 3: Implement registry and configuration helpers**

```python
class OperationRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._operations = {}

    def begin(self, udid, kind):
        with self._lock:
            if udid in self._operations:
                return False
            self._operations[udid] = kind
            return True

def load_concurrency(path, default=4):
    try:
        value = int(read_json(path).get("threads", default))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        value = default
    return max(1, min(8, value))
```

- [ ] **Step 4: Write failing URL, IPA, and license tests**

```python
def test_fun_https_is_not_downgraded(self):
    self.assertEqual("https://example.fun/path", normalize_url("https://example.fun/path"))

def test_missing_ipa_path_falls_back_to_bundled(self):
    settings = {"ipasDir": os.path.join(self.temp_dir, "missing")}
    changed = repair_ipas_path(settings, self.base_dir)
    self.assertTrue(changed)
    self.assertEqual(os.path.join(self.base_dir, "ipas"), settings["ipasDir"])

def test_license_is_machine_bound(self):
    fingerprint = "test-machine"
    key = make_license_key(fingerprint)
    self.assertTrue(validate_license_key(key, fingerprint))
    self.assertFalse(validate_license_key(key, "other-machine"))
```

- [ ] **Step 5: Implement URL, IPA, and reference-compatible HMAC license helpers**

```python
def normalize_url(url):
    raw = (url or "").strip()
    if not raw:
        return ""
    if re.match(r"^(https?|itms-apps)://", raw, re.I):
        return raw
    return "https://" + raw

def validate_license_key(key, fingerprint):
    expected = make_license_key(fingerprint)
    return hmac.compare_digest((key or "").strip(), expected)
```

- [ ] **Step 6: Run Task 2 tests and verify GREEN**

Run: `python -m unittest tests.test_tiktool_core.RegistryConfigTests tests.test_tiktool_core.SettingsLicenseTests -v`

Expected: all tests pass without printing secrets.

---

### Task 3: Tracked subprocess runner

**Files:**
- Modify: `tiktool_core.py`
- Modify: `tests/test_tiktool_core.py`

**Interfaces:**
- Produces: `CommandResult(returncode: int, output: str, lines: tuple[str, ...], timed_out: bool, error: str)`
- Produces: `ProcessRunner.run_capture(command, timeout) -> CommandResult`
- Produces: `ProcessRunner.run_stream(command, on_line, timeout) -> CommandResult`
- Produces: `ProcessRunner.terminate_all() -> None`

- [ ] **Step 1: Write failing timeout and final-line tests**

```python
def test_capture_times_out_and_unregisters_process(self):
    result = self.runner.run_capture(python_command("import time; time.sleep(2)"), timeout=0.1)
    self.assertTrue(result.timed_out)
    self.assertEqual({}, self.runner.active_snapshot())

def test_stream_keeps_unterminated_final_line(self):
    seen = []
    result = self.runner.run_stream(python_command("print('tail', end='')"), seen.append, timeout=2)
    self.assertEqual(("tail",), result.lines)
    self.assertEqual(["tail"], seen)
```

- [ ] **Step 2: Run selected tests and verify RED**

Run: `python -m unittest tests.test_tiktool_core.ProcessRunnerTests -v`

Expected: `ProcessRunner` is missing.

- [ ] **Step 3: Implement one Popen-based tracked runner**

```python
@dataclass(frozen=True)
class CommandResult:
    returncode: int
    output: str
    lines: tuple
    timed_out: bool = False
    error: str = ""

class ProcessRunner:
    def _wait(self, process, timeout):
        try:
            return process.communicate(timeout=timeout), False
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            return process.communicate(), True
```

- [ ] **Step 4: Verify timeout, tracking, streaming, and full suite GREEN**

Run: `python -m unittest tests.test_tiktool_core.ProcessRunnerTests -v`

Expected: all runner tests pass and no child process remains registered.

---

### Task 4: Integrate immutable backup and restore workflows

**Files:**
- Modify: `BB_RB.py:1-486`
- Modify: `BB_RB.py:1619-2145`
- Create: `tests/test_app_workflows.py`

**Interfaces:**
- Consumes: `validate_backup`, `create_restore_stage`, `backup_fingerprint`, `cleanup_owned_job`, `transfer_backup_immutable`, `OperationRegistry`, `ProcessRunner`
- Produces: `_prepare_backup_job(target_root, udid)` and staged `_restore_worker(...)`

- [ ] **Step 1: Write failing backup regression test**

```python
def test_failed_backup_does_not_delete_existing_udid_directory(self):
    existing = os.path.join(self.target, self.udid)
    os.makedirs(existing)
    write_file(os.path.join(existing, "valuable"), b"keep")
    app = make_headless_app(command_result=failed_result())
    App._backup_worker(app, self.udid, self.target)
    self.assertTrue(os.path.isfile(os.path.join(existing, "valuable")))
```

- [ ] **Step 2: Run regression and verify RED**

Run: `python -m unittest tests.test_app_workflows.BackupWorkflowTests.test_failed_backup_does_not_delete_existing_udid_directory -v`

Expected: current code deletes the existing directory.

- [ ] **Step 3: Route new backups through unique app-owned job roots**

```python
job = create_backup_job(target_root, udid)
try:
    result = self.process_runner.run_stream(
        ["idevicebackup2", "-u", udid, "backup", "--full", job.job_root],
        on_line=on_line,
        timeout=BACKUP_TIMEOUT,
    )
    if not result.ok:
        return fail("Lỗi Backup")
    final_dst = finalize_backup_job(job, final_name)
finally:
    cleanup_owned_job(job.job_root, missing_ok=True)
```

- [ ] **Step 4: Write failing restore immutability tests**

```python
def test_failed_restore_never_changes_source_backup(self):
    source = make_backup(self.store_a, udid="OLD")
    before = backup_fingerprint(source)
    app = make_headless_app(command_result=failed_result())
    App._restore_worker(app, "NEW", source, self.store_b, "A", snapshot())
    self.assertEqual(before, backup_fingerprint(source))
    self.assertEqual("OLD", read_udid(source))
    self.assertTrue(os.path.isdir(source))
```

- [ ] **Step 5: Run restore test and verify RED**

Run: `python -m unittest tests.test_app_workflows.RestoreWorkflowTests.test_failed_restore_never_changes_source_backup -v`

Expected: current code patches source `Info.plist` to `NEW`.

- [ ] **Step 6: Restore only from a staged copy and transfer verified original**

```python
stage = create_restore_stage(backup_folder_full, target_udid)
try:
    staged_parent = os.path.dirname(stage.backup_path)
    staged_name = os.path.basename(stage.backup_path)
    result = self.process_runner.run_stream(
        ["idevicebackup2", "-u", target_udid, "-s", staged_name,
         "restore", staged_parent, "--settings", "--remove"],
        on_line=on_line,
        timeout=RESTORE_TIMEOUT,
    )
    if result.returncode != 0 or result.timed_out:
        return fail_restore(result)
    if backup_fingerprint(backup_folder_full) != stage.source_fingerprint:
        raise IntegrityError("Source backup changed during restore")
    destination = transfer_backup_immutable(backup_folder_full, target_after_restore)
finally:
    cleanup_owned_job(stage.job_root, missing_ok=True)
```

- [ ] **Step 7: Remove all production source-backup mutation paths**

Delete `patch_backup_language`, `ensure_status_plist`, the hidden patch variable, `patchBackupLangBeforeRestore`, and direct calls to `patch_info_plist` on source paths. Keep `patch_staged_info` only in `tiktool_core.py` and require its resolved path to be inside an owned restore job.

- [ ] **Step 8: Run workflow tests and verify GREEN**

Run: `python -m unittest tests.test_app_workflows -v`

Expected: backup failure preserves existing data; restore failure and success keep source contents unchanged before transfer.

---

### Task 5: Thread-safe UI, operation ownership, polling, and reboot state

**Files:**
- Modify: `BB_RB.py:489-714`
- Modify: `BB_RB.py:1093-1383`
- Modify: `BB_RB.py:1705-1835`
- Modify: `BB_RB.py:2147-2265`
- Modify: `tests/test_app_workflows.py`

**Interfaces:**
- Consumes: `OperationRegistry`
- Produces: `App._post_ui(callback, *args, **kwargs)`
- Produces: `App._drain_ui_queue()`
- Produces: settings snapshots passed to every worker
- Produces: reboot-cache reconciliation from plain polling results

- [ ] **Step 1: Write failing UI queue and duplicate-operation tests**

```python
def test_worker_log_enqueues_without_calling_tk(self):
    app = make_queue_only_app()
    App.log(app, "abcdef123", "hello")
    event = app.ui_queue.get_nowait()
    self.assertIs(event.callback, app._write_log)

def test_duplicate_device_operation_is_rejected(self):
    app = make_headless_app()
    self.assertTrue(app.operations.begin("u1", "backup"))
    self.assertFalse(app.operations.begin("u1", "activate"))
```

- [ ] **Step 2: Run selected tests and verify RED**

Run: `python -m unittest tests.test_app_workflows.UiThreadTests -v`

Expected: current `log()` calls Tk `after()` and no registry exists.

- [ ] **Step 3: Implement a Python queue boundary and immutable worker snapshots**

```python
def _post_ui(self, callback, *args, **kwargs):
    self.ui_queue.put(UiEvent(callback, args, kwargs))

def _drain_ui_queue(self):
    for _ in range(UI_BATCH_SIZE):
        try:
            event = self.ui_queue.get_nowait()
        except queue.Empty:
            break
        event.callback(*event.args, **event.kwargs)
    self.after(UI_DRAIN_MS, self._drain_ui_queue)
```

Replace every worker-side `row.*`, Tk variable read, `messagebox`, and `self.after()` with `_post_ui` or a value captured before thread start.

- [ ] **Step 4: Move device metadata reads off the main thread and coalesce poll results**

The poller builds `{udid: {trusted, name, model, ios, ios_t, ecid}}` dictionaries in its executor. It keeps at most one pending UI sync event and updates that event's latest payload rather than queueing every 300 ms.

- [ ] **Step 5: Preserve reboot cards through temporary disappearance**

```python
if udid not in current_udids and self.reboot_tracker.is_waiting(udid, now):
    card = self.rows[udid]
    card.push_step("Hoàn tất • Đang khởi động lại...")
    continue
```

Clear the state only on verified reconnect or expiry; do not delete it in the generic disconnect branch.

- [ ] **Step 6: Run thread, registry, and reboot tests GREEN**

Run: `python -m unittest tests.test_app_workflows.UiThreadTests tests.test_app_workflows.RebootTests -v`

Expected: workers make no Tk calls and temporary disappearance retains state.

---

### Task 6: Pipeline outcomes, WebClip, settings, license, and durable logs

**Files:**
- Modify: `BB_RB.py:55-266`
- Modify: `BB_RB.py:1145-1383`
- Modify: `BB_RB.py:1619-1715`
- Modify: `settings.json`
- Modify: `tests/test_app_workflows.py`

**Interfaces:**
- Consumes: `ProcessRunner`, `normalize_url`, license helpers, `load_concurrency`, `repair_ipas_path`
- Produces: truthful Batch Activate result and empty-device-safe WebClip
- Produces: per-run `logs/tiktool-YYYYMMDD-HHMMSS.log`

- [ ] **Step 1: Write failing pipeline and WebClip tests**

```python
def test_language_failure_makes_batch_activate_fail(self):
    app = make_activate_app(results=[ok(), ok(), failed(9)])
    success = App._batch_activate_worker(app, "u1", activate_snapshot(set_language=True))
    self.assertFalse(success)
    self.assertNotIn("hoàn tất thành công", app.logged_text.lower())

def test_empty_device_webclip_returns_cleanly(self):
    app = make_webclip_app(device_ids=[])
    self.assertFalse(App._push_webclip_all(app, "X", "https://example.com", []))
    self.assertIn("không có thiết bị", app.notifications[0].lower())
```

- [ ] **Step 2: Run selected tests and verify RED**

Run: `python -m unittest tests.test_app_workflows.PipelineTests -v`

Expected: language failure reports success and WebClip calls missing `refresh()`.

- [ ] **Step 3: Implement truthful stage checks and explicit device snapshots**

```python
language = runner.run_capture(language_command, timeout=LANGUAGE_TIMEOUT)
if language.returncode != 0 or language.timed_out:
    fail_stage("Set Language", language)
    return False

def _push_webclip_all(self, label, url, device_ids):
    if not device_ids:
        self._notify("info", "Web App", "Không có thiết bị kết nối.")
        return False
```

- [ ] **Step 4: Apply configuration, URL, and license helpers at startup**

Initialize the semaphore with `load_concurrency(APPS_CONFIG_FP)`, repair and persist `ipasDir`, set `self.licensed = check_license_file(LICENSE_FILE)`, and apply locked/unlocked button state using the existing reference-tool behavior.

- [ ] **Step 5: Implement lock-protected durable logging**

```python
def _append_log_file(self, message):
    redacted = redact_log(message)
    with self.log_file_lock:
        with open(self.log_file_path, "a", encoding="utf-8", newline="") as stream:
            stream.write(redacted)
```

UI logs still flow through `_post_ui`; file logging is independent of Tkinter.

- [ ] **Step 6: Run pipeline/config/license/log tests GREEN**

Run: `python -m unittest tests.test_app_workflows.PipelineTests tests.test_app_workflows.StartupTests -v`

Expected: all tests pass and temporary log contains redacted UTF-8 entries.

---

### Task 7: Full verification and documentation alignment

**Files:**
- Modify: `docs/architecture/system_overview.md`
- Modify: `CHANGELOG.md`
- Modify: `.brain/brain.json`
- Modify: `.brain/session.json`
- Modify: `.brain/handover.md`
- Test: `tests/test_tiktool_core.py`
- Test: `tests/test_app_workflows.py`

**Interfaces:**
- Consumes: all interfaces from Tasks 1–6
- Produces: verified implementation and accurate project documentation

- [ ] **Step 1: Run the full regression suite**

Run: `python -m unittest discover -s tests -v`

Expected: every test passes; no real device tool is invoked.

- [ ] **Step 2: Run syntax and source-invariant checks**

Run: `python -m py_compile BB_RB.py tiktool_core.py tests/test_tiktool_core.py tests/test_app_workflows.py`

Run: `rg -n "patch_backup_language|ensure_status_plist|patchBackupLangBeforeRestore|self\.refresh\(\)" BB_RB.py tiktool_core.py`

Expected: compilation succeeds and the forbidden-pattern search returns no matches.

- [ ] **Step 3: Run a static source-backup mutation audit**

Inspect every caller of `open`, `os.remove`, `os.unlink`, `os.rename`, `shutil.move`, and `shutil.rmtree`. Confirm that write/delete operations target only staged jobs, new backup jobs, or verified whole-directory transfers.

- [ ] **Step 4: Update documentation with verified behavior**

Document version `4.4.0 Stability & Immutable Backup Edition`, staging-based restore, strict validation, operation registry, process timeouts, and test coverage. Remove claims that restore patches the source backup or synthesizes missing backup metadata.

- [ ] **Step 5: Review the final diff without modifying unrelated changes**

Run: `git diff --check`

Run: `git status --short`

Run: `git diff -- BB_RB.py tiktool_core.py tests docs/architecture/system_overview.md CHANGELOG.md .brain`

Expected: no whitespace errors, no unexpected files, and no edits to real backup directories or binary tools.
