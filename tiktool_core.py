"""Safety-critical, Tkinter-independent primitives for TIKTOOL PRO V4."""

from __future__ import annotations

import hashlib
import base64
import codecs
import hmac
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import tempfile
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REQUIRED_BACKUP_FILES = (
    "Manifest.db",
    "Info.plist",
    "Manifest.plist",
    "Status.plist",
)
WORK_DIR_NAME = ".tiktool_work"
OWNED_JOB_PREFIXES = ("restore-", "backup-", "transfer-")
LICENSE_SECRET = base64.b64decode("J1+EGe8rOjhrROIE5Dygj2nnHTKH/9Bval0PMWI2w5E=")
LICENSE_PREFIX = "IPTP-"


class IntegrityError(RuntimeError):
    """Raised when a backup changes during a supposedly immutable operation."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    output: str
    lines: tuple[str, ...]
    timed_out: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out and not self.error


def _no_window_kwargs() -> dict:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return {"startupinfo": startupinfo, "creationflags": 0x08000000}


class ProcessRunner:
    """Run and track external tools with bounded lifetimes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: dict[int, tuple[subprocess.Popen, tuple[str, ...]]] = {}

    def _register(self, process: subprocess.Popen, command) -> None:
        with self._lock:
            self._active[process.pid] = (process, tuple(str(part) for part in command))

    def _unregister(self, process: subprocess.Popen) -> None:
        with self._lock:
            self._active.pop(process.pid, None)

    def active_snapshot(self) -> dict[int, tuple[str, ...]]:
        with self._lock:
            return {pid: command for pid, (_, command) in self._active.items()}

    @staticmethod
    def _stop_process(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                pass

    def _start(self, command) -> subprocess.Popen:
        process = subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            **_no_window_kwargs(),
        )
        self._register(process, command)
        return process

    def run_capture(self, command, timeout: float) -> CommandResult:
        try:
            process = self._start(command)
        except (OSError, ValueError) as exc:
            return CommandResult(127, "", (), error=str(exc))
        try:
            try:
                output_bytes, _ = process.communicate(timeout=timeout)
                timed_out = False
            except subprocess.TimeoutExpired:
                timed_out = True
                self._stop_process(process)
                output_bytes, _ = process.communicate()
            output = (output_bytes or b"").decode("utf-8", errors="replace").strip()
            lines = tuple(line.strip() for line in output.splitlines() if line.strip())
            return CommandResult(
                process.returncode if process.returncode is not None else -1,
                output,
                lines,
                timed_out=timed_out,
                error="Command timed out" if timed_out else "",
            )
        finally:
            self._unregister(process)

    def run_stream(self, command, on_line=None, timeout: float = 3600) -> CommandResult:
        try:
            process = self._start(command)
        except (OSError, ValueError) as exc:
            return CommandResult(127, "", (), error=str(exc))

        lines: list[str] = []
        read_errors: list[str] = []

        def emit(line: str) -> None:
            clean = line.strip()
            if not clean:
                return
            lines.append(clean)
            if on_line:
                lowered = clean.lower()
                is_error = any(
                    marker in lowered
                    for marker in ("error", "failed", "mberrordomain", "timed out")
                )
                try:
                    on_line(clean, is_err=is_error)
                except Exception as exc:
                    read_errors.append(str(exc))

        def reader() -> None:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            pending = ""
            try:
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    pending += decoder.decode(chunk)
                    while True:
                        positions = [pos for pos in (pending.find("\n"), pending.find("\r")) if pos >= 0]
                        if not positions:
                            break
                        position = min(positions)
                        emit(pending[:position])
                        pending = pending[position + 1 :]
                pending += decoder.decode(b"", final=True)
                emit(pending)
            except Exception as exc:
                read_errors.append(str(exc))

        reader_thread = threading.Thread(target=reader, daemon=True)
        reader_thread.start()
        timed_out = False
        try:
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                self._stop_process(process)
            reader_thread.join(timeout=3)
            if reader_thread.is_alive():
                read_errors.append("Output reader did not stop")
            return CommandResult(
                process.returncode if process.returncode is not None else -1,
                "\n".join(lines),
                tuple(lines),
                timed_out=timed_out,
                error="; ".join(read_errors) or ("Command timed out" if timed_out else ""),
            )
        finally:
            if process.stdout is not None:
                process.stdout.close()
            self._unregister(process)

    def terminate_all(self) -> None:
        with self._lock:
            processes = [process for process, _ in self._active.values()]
        for process in processes:
            self._stop_process(process)


class OperationRegistry:
    """Own at most one mutating operation per device UDID."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._operations: dict[str, str] = {}

    def begin(self, udid: str, kind: str) -> bool:
        with self._lock:
            if udid in self._operations:
                return False
            self._operations[udid] = kind
            return True

    def transition(self, udid: str, expected: str, new_kind: str) -> bool:
        with self._lock:
            if self._operations.get(udid) != expected:
                return False
            self._operations[udid] = new_kind
            return True

    def end(self, udid: str, kind: str) -> None:
        with self._lock:
            if self._operations.get(udid) == kind:
                del self._operations[udid]

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            return dict(self._operations)


class RebootTracker:
    """Keep temporary reboot state independent from USB presence polling."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._deadlines: dict[str, float] = {}

    def mark(self, udid: str, timeout: float, now: float | None = None) -> None:
        import time

        current = time.time() if now is None else now
        with self._lock:
            self._deadlines[udid] = current + max(0, timeout)

    def is_waiting(self, udid: str, now: float | None = None) -> bool:
        import time

        current = time.time() if now is None else now
        with self._lock:
            deadline = self._deadlines.get(udid)
            if deadline is None:
                return False
            if deadline < current:
                del self._deadlines[udid]
                return False
            return True

    def clear(self, udid: str) -> None:
        with self._lock:
            self._deadlines.pop(udid, None)


@dataclass(frozen=True)
class RestoreStage:
    job_root: str
    backup_path: str
    source_fingerprint: str


@dataclass(frozen=True)
class BackupJob:
    job_root: str
    output_path: str


def create_backup_job(target_root: str, udid: str) -> BackupJob:
    target = _resolved_dir(target_root)
    work_root = _work_root(target)
    job_root = tempfile.mkdtemp(prefix="backup-", dir=work_root)
    return BackupJob(job_root=job_root, output_path=os.path.join(job_root, udid))


def load_concurrency(path: str, default: int = 20) -> int:
    try:
        with open(path, "r", encoding="utf-8") as stream:
            value = int(json.load(stream).get("threads", default))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        value = default
    return max(1, min(32, value))


def normalize_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if re.match(r"^(?:https?|itms-apps)://", raw, flags=re.I):
        return raw
    return "https://" + raw


def redact_log(message: str) -> str:
    """Remove activation keys before a message is persisted to disk."""
    return re.sub(
        r"IPTP-[A-Za-z0-9_-]+",
        "[REDACTED-LICENSE]",
        str(message),
        flags=re.I,
    )


def repair_ipas_path(settings: dict, base_dir: str) -> bool:
    configured = str(settings.get("ipasDir") or "").strip()
    if configured and os.path.isdir(configured):
        return False
    bundled = os.path.join(os.path.abspath(base_dir), "ipas")
    os.makedirs(bundled, exist_ok=True)
    changed = os.path.normcase(os.path.abspath(configured or ".")) != os.path.normcase(bundled)
    settings["ipasDir"] = bundled
    return changed


def _read_windows_machine_guid() -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
        return str(value)
    except (OSError, ImportError):
        return ""


def machine_fingerprint() -> str:
    parts = []
    machine_guid = _read_windows_machine_guid()
    if machine_guid:
        parts.append(machine_guid)
    parts.append(platform.node() or "")
    parts.append(platform.system() + "-" + platform.release())
    if not any(parts):
        parts.append(str(uuid.getnode()))
    return "|".join(parts)


def make_license_key(fingerprint: str) -> str:
    signature = hmac.new(
        LICENSE_SECRET,
        str(fingerprint).encode("utf-8"),
        digestmod="sha256",
    ).digest()
    token = base64.urlsafe_b64encode(signature).decode("utf-8")[:24]
    return LICENSE_PREFIX + token


def validate_license_key(key: str, fingerprint: str) -> bool:
    return hmac.compare_digest((key or "").strip(), make_license_key(fingerprint))


def check_license_file(path: str, fingerprint: str | None = None) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as stream:
            key = str(json.load(stream).get("key") or "").strip()
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return validate_license_key(key, fingerprint or machine_fingerprint())


def _resolved_dir(path: str) -> str:
    resolved = os.path.realpath(os.path.abspath(path))
    if not os.path.isdir(resolved):
        raise ValueError(f"Directory does not exist: {path}")
    return resolved


def _work_root(store_root: str) -> str:
    store = _resolved_dir(store_root)
    work = os.path.join(store, WORK_DIR_NAME)
    os.makedirs(work, exist_ok=True)
    return os.path.realpath(work)


def _is_owned_job_root(path: str) -> bool:
    resolved = os.path.realpath(os.path.abspath(path))
    parent = os.path.dirname(resolved)
    return (
        os.path.basename(parent) == WORK_DIR_NAME
        and os.path.basename(resolved).startswith(OWNED_JOB_PREFIXES)
    )


def _is_inside(path: str, parent: str) -> bool:
    resolved_path = os.path.realpath(os.path.abspath(path))
    resolved_parent = os.path.realpath(os.path.abspath(parent))
    try:
        return os.path.commonpath((resolved_path, resolved_parent)) == resolved_parent
    except ValueError:
        return False


def validate_backup(path: str) -> tuple[bool, list[str]]:
    """Validate an iOS backup without creating or modifying any file."""
    backup = os.path.realpath(os.path.abspath(path))
    if not os.path.isdir(backup):
        return False, [f"Backup directory does not exist: {path}"]

    errors = [
        f"Missing {name}"
        for name in REQUIRED_BACKUP_FILES
        if not os.path.isfile(os.path.join(backup, name))
    ]
    if errors:
        return False, errors

    try:
        with open(os.path.join(backup, "Status.plist"), "rb") as stream:
            status = plistlib.load(stream)
    except (OSError, plistlib.InvalidFileException, ValueError, TypeError) as exc:
        return False, [f"Invalid Status.plist: {exc}"]

    if str(status.get("SnapshotState", "")).strip().lower() != "finished":
        return False, ["Status.plist snapshot is not finished"]
    return True, []


def backup_fingerprint(path: str) -> str:
    """Hash the complete relative tree and every file byte deterministically."""
    backup = _resolved_dir(path)
    digest = hashlib.sha256()
    digest.update(b"TIKTOOL-BACKUP-FINGERPRINT-V1\0")

    for root, dir_names, file_names in os.walk(backup):
        dir_names.sort()
        file_names.sort()
        relative_root = os.path.relpath(root, backup)
        relative_root = "" if relative_root == "." else relative_root.replace(os.sep, "/")
        for directory in dir_names:
            relative = "/".join(part for part in (relative_root, directory) if part)
            digest.update(b"D\0" + relative.encode("utf-8", errors="surrogatepass") + b"\0")
        for filename in file_names:
            full_path = os.path.join(root, filename)
            if os.path.islink(full_path):
                raise IntegrityError(f"Symbolic links are not allowed in backups: {full_path}")
            relative = "/".join(part for part in (relative_root, filename) if part)
            size = os.path.getsize(full_path)
            digest.update(b"F\0" + relative.encode("utf-8", errors="surrogatepass") + b"\0")
            digest.update(str(size).encode("ascii") + b"\0")
            with open(full_path, "rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
    return digest.hexdigest()


def _patch_staged_info(staged_backup: str, target_udid: str, job_root: str) -> None:
    if not _is_owned_job_root(job_root) or not _is_inside(staged_backup, job_root):
        raise ValueError("Refusing to patch a backup outside an owned restore job")
    info_path = os.path.join(staged_backup, "Info.plist")
    with open(info_path, "rb") as stream:
        info = plistlib.load(stream)
    info["UniqueDeviceID"] = target_udid
    temporary = info_path + ".tmp"
    with open(temporary, "wb") as stream:
        plistlib.dump(info, stream)
    os.replace(temporary, info_path)


def create_restore_stage(source_backup: str, target_udid: str) -> RestoreStage:
    """Create and patch a disposable copy; the source is opened read-only."""
    source = _resolved_dir(source_backup)
    valid, errors = validate_backup(source)
    if not valid:
        raise ValueError("Invalid backup: " + "; ".join(errors))

    source_fingerprint = backup_fingerprint(source)
    work_root = _work_root(os.path.dirname(source))
    job_root = tempfile.mkdtemp(prefix="restore-", dir=work_root)
    staged = os.path.join(job_root, os.path.basename(source))
    try:
        shutil.copytree(source, staged, copy_function=shutil.copy2)
        if backup_fingerprint(source) != source_fingerprint:
            raise IntegrityError("Source backup changed while staging")
        if backup_fingerprint(staged) != source_fingerprint:
            raise IntegrityError("Staged backup does not match its source")
        _patch_staged_info(staged, target_udid, job_root)
        return RestoreStage(job_root, staged, source_fingerprint)
    except Exception:
        cleanup_owned_job(job_root, missing_ok=True)
        raise


def cleanup_owned_job(job_root: str, missing_ok: bool = False) -> None:
    """Remove only a direct, recognized child of a `.tiktool_work` directory.
    After the job folder is deleted, the parent `.tiktool_work` dir is also
    removed when it becomes empty so it never lingers in the store.
    """
    resolved = os.path.realpath(os.path.abspath(job_root))
    if not _is_owned_job_root(resolved):
        raise ValueError(f"Refusing to delete a non-owned path: {job_root}")
    if not os.path.exists(resolved):
        if missing_ok:
            return
        raise FileNotFoundError(resolved)
    shutil.rmtree(resolved)

    # Clean up the parent .tiktool_work dir if it is now empty
    work_dir = os.path.dirname(resolved)
    try:
        if os.path.basename(work_dir) == WORK_DIR_NAME and os.path.isdir(work_dir):
            if not os.listdir(work_dir):  # empty → safe to remove
                os.rmdir(work_dir)
    except Exception:
        pass  # Non-critical: leave it if something prevents removal


def _validate_distinct_stores(source: str, destination_root: str) -> tuple[str, str]:
    source_parent = os.path.realpath(os.path.dirname(source))
    destination = _resolved_dir(destination_root)
    try:
        common = os.path.commonpath((source_parent, destination))
    except ValueError:
        return source_parent, destination
    if source_parent == destination or common in (source_parent, destination):
        raise ValueError("Source and destination stores must be different and non-nested")
    return source_parent, destination


def _unique_destination(destination_root: str, name: str) -> str:
    candidate = os.path.join(destination_root, name)
    if not os.path.exists(candidate):
        return candidate
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for index in range(1, 10000):
        suffix = f"_{stamp}" if index == 1 else f"_{stamp}_{index}"
        candidate = os.path.join(destination_root, name + suffix)
        if not os.path.exists(candidate):
            return candidate
    raise FileExistsError(f"Could not reserve a unique destination for {name}")


def _same_volume(first: str, second: str) -> bool:
    first_drive = os.path.splitdrive(os.path.abspath(first))[0].lower()
    second_drive = os.path.splitdrive(os.path.abspath(second))[0].lower()
    return first_drive == second_drive


def transfer_backup_immutable(source: str, destination_root: str) -> str:
    """Transfer a whole verified backup without editing anything inside it."""
    source_path = _resolved_dir(source)
    _, destination_store = _validate_distinct_stores(source_path, destination_root)
    original_fingerprint = backup_fingerprint(source_path)
    destination = _unique_destination(destination_store, os.path.basename(source_path))

    if _same_volume(source_path, destination_store):
        os.rename(source_path, destination)
        try:
            if backup_fingerprint(destination) != original_fingerprint:
                raise IntegrityError("Transferred backup fingerprint mismatch")
        except Exception:
            if not os.path.exists(source_path) and os.path.exists(destination):
                os.rename(destination, source_path)
            raise
        return destination

    work_root = _work_root(destination_store)
    job_root = tempfile.mkdtemp(prefix="transfer-", dir=work_root)
    staged_destination = os.path.join(job_root, os.path.basename(source_path))
    try:
        shutil.copytree(source_path, staged_destination, copy_function=shutil.copy2)
        if backup_fingerprint(staged_destination) != original_fingerprint:
            raise IntegrityError("Destination fingerprint mismatch")
        if backup_fingerprint(source_path) != original_fingerprint:
            raise IntegrityError("Source backup changed during transfer")
        os.rename(staged_destination, destination)
        if backup_fingerprint(destination) != original_fingerprint:
            raise IntegrityError("Final destination fingerprint mismatch")
        shutil.rmtree(source_path)
        return destination
    except Exception:
        if os.path.exists(destination) and os.path.exists(source_path):
            shutil.rmtree(destination)
        raise
    finally:
        cleanup_owned_job(job_root, missing_ok=True)
