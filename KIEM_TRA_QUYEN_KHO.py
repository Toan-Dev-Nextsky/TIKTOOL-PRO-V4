"""Kiểm tra quyền NTFS của Kho A/B (hoặc cả một ổ/thư mục) đúng như thao tác Restore cần,
hỏi rồi sửa bằng icacls.

Không sửa dữ liệu backup thật: chỉ mở handle kiểm tra quyền và tạo/xóa file tạm của chính tool.
Cách dùng: KIEM_TRA_QUYEN_KHO.bat            -> chọn chế độ
           KIEM_TRA_QUYEN_KHO.bat E:         -> kiểm tra cả ổ E
           KIEM_TRA_QUYEN_KHO.bat F:\\backups -> kiểm tra một thư mục
           thêm --sau để kiểm tra từng file (chậm)
"""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FP = os.path.join(BASE_DIR, "settings.json")
SKIP_DIRS = (".tiktool_work",)
CHECK_PREFIX = ".tt_permcheck_"
ROOT_FIX_THRESHOLD = 30
SAMPLES_PER_UNIT = 5
SYSTEM_DIRS_ANYWHERE = {"$recycle.bin", "system volume information"}
SYSTEM_DIRS_AT_DRIVE_ROOT = {"windows", "program files", "program files (x86)", "programdata", "recovery",
                             "perflogs", "config.msi", "users", "$windows.~bt", "$windows.~ws", "$winreagent"}
FILE_ATTRIBUTE_REPARSE_POINT = 0x400

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

DELETE = 0x00010000
FILE_SHARE_ALL = 0x7
OPEN_EXISTING = 3
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_ATTRIBUTE_READONLY = 0x1
INVALID_ATTRS = 0xFFFFFFFF
INVALID_HANDLE = wintypes.HANDLE(-1).value
SE_FILE_OBJECT = 1
OWNER_SECURITY_INFORMATION = 1
SEE_MASK_NOCLOSEPROCESS = 0x40

kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                 wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.GetFileAttributesW.restype = wintypes.DWORD
kernel32.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
kernel32.LocalFree.argtypes = [ctypes.c_void_p]
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
advapi32.GetNamedSecurityInfoW.restype = wintypes.DWORD
advapi32.GetNamedSecurityInfoW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, wintypes.DWORD,
                                           ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
                                           ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
                                           ctypes.POINTER(ctypes.c_void_p)]
advapi32.LookupAccountSidW.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, wintypes.LPWSTR,
                                       ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR,
                                       ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD)]
advapi32.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]


class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR),
                ("lpParameters", wintypes.LPCWSTR), ("lpDirectory", wintypes.LPCWSTR),
                ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE), ("lpIDList", ctypes.c_void_p),
                ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY), ("dwHotKey", wintypes.DWORD),
                ("hIconOrMonitor", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]


KIND_LABEL = {
    "perm": "THIẾU QUYỀN (cần icacls)",
    "readonly": "Thuộc tính Chỉ đọc",
    "lock": "ĐANG BỊ KHÓA bởi chương trình khác",
    "other": "Lỗi khác",
}


def classify(code):
    if code == 5:
        return "perm"
    if code in (32, 33):
        return "lock"
    return "other"


def open_for_delete(path, is_dir):
    """0 nếu tài khoản hiện tại có quyền xóa/đổi tên, ngược lại trả mã WinError."""
    flags = FILE_FLAG_BACKUP_SEMANTICS if is_dir else 0
    handle = kernel32.CreateFileW(path, DELETE, FILE_SHARE_ALL, None, OPEN_EXISTING, flags, None)
    if handle == INVALID_HANDLE or handle is None:
        return ctypes.get_last_error()
    kernel32.CloseHandle(handle)
    return 0


def is_readonly(path):
    attrs = kernel32.GetFileAttributesW(path)
    return attrs != INVALID_ATTRS and bool(attrs & FILE_ATTRIBUTE_READONLY)


def owner_of(path):
    psid, psd = ctypes.c_void_p(), ctypes.c_void_p()
    if advapi32.GetNamedSecurityInfoW(path, SE_FILE_OBJECT, OWNER_SECURITY_INFORMATION,
                                      ctypes.byref(psid), None, None, None, ctypes.byref(psd)):
        return "?"
    try:
        name, dom = ctypes.create_unicode_buffer(256), ctypes.create_unicode_buffer(256)
        n, d, use = wintypes.DWORD(256), wintypes.DWORD(256), wintypes.DWORD()
        if advapi32.LookupAccountSidW(None, psid, name, ctypes.byref(n), dom, ctypes.byref(d), ctypes.byref(use)):
            return f"{dom.value}\\{name.value}" if dom.value else name.value
        sid = wintypes.LPWSTR()
        if advapi32.ConvertSidToStringSidW(psid, ctypes.byref(sid)):
            try:
                return f"{sid.value}  <-- SID cũ, tài khoản không còn tồn tại"
            finally:
                kernel32.LocalFree(ctypes.cast(sid, ctypes.c_void_p))
        return "?"
    finally:
        kernel32.LocalFree(psd)


def win_code(exc):
    return getattr(exc, "winerror", None) or (5 if isinstance(exc, PermissionError) else -1)


def check_temp_cycle(folder, make_dir=False):
    """Tạo -> đổi tên -> xóa một mục tạm của tool trong folder. Trả (kind, chi tiết) hoặc None."""
    created = renamed = None
    try:
        if make_dir:
            created = tempfile.mkdtemp(prefix=CHECK_PREFIX, dir=folder)
        else:
            fd, created = tempfile.mkstemp(prefix=CHECK_PREFIX, suffix=".tmp", dir=folder)
            with os.fdopen(fd, "wb") as stream:
                stream.write(b"tiktool permission check")
        renamed = created + ".mv"
        os.replace(created, renamed)
        created = None
        (os.rmdir if make_dir else os.unlink)(renamed)
        renamed = None
        return None
    except OSError as exc:
        return classify(win_code(exc)), f"tạo/đổi tên/xóa mục tạm thất bại: {exc.strerror or exc}"
    finally:
        for leftover in (created, renamed):
            if leftover and os.path.exists(leftover):
                try:
                    (os.rmdir if make_dir else os.unlink)(leftover)
                except OSError:
                    pass


def list_backups(store):
    try:
        names = sorted(os.listdir(store))
    except OSError:
        return []
    return [os.path.join(store, n) for n in names
            if n not in SKIP_DIRS and not n.startswith(CHECK_PREFIX)
            and os.path.isfile(os.path.join(store, n, "Info.plist"))]


def check_backup(backup, deep):
    issues = []
    code = open_for_delete(backup, True)
    if code:
        issues.append((classify(code), backup, f"không đổi tên được thư mục backup (WinError {code})"))
    info = os.path.join(backup, "Info.plist")
    if is_readonly(info):
        issues.append(("readonly", info, "Info.plist đang bật Chỉ đọc nên không ghi UDID được"))
    else:
        code = open_for_delete(info, False)
        if code:
            issues.append((classify(code), info, f"không thay thế được Info.plist (WinError {code})"))
    problem = check_temp_cycle(backup)
    if problem:
        issues.append((problem[0], backup, problem[1]))
    if deep:
        bad = 0
        for root, _, files in os.walk(backup):
            for name in files:
                path = os.path.join(root, name)
                code = open_for_delete(path, False)
                if code:
                    bad += 1
                    if bad <= 3:
                        issues.append((classify(code), path, f"không xóa được file khi chuyển khác ổ (WinError {code})"))
        if bad > 3:
            issues.append(("perm", backup, f"... tổng cộng {bad} file không xóa được"))
    return issues


def load_stores():
    with open(SETTINGS_FP, "r", encoding="utf-8") as stream:
        data = json.load(stream)
    return [(label, os.path.normpath(data.get(key, "") or "")) for label, key in (("A", "storeA"), ("B", "storeB"))]


def run_checks(stores, only=None):
    """Trả (tổng số backup, danh sách lỗi). only: giới hạn kiểm tra lại các đường dẫn này."""
    drives = {os.path.splitdrive(path)[0].lower() for _, path in stores if path}
    deep = len(drives) > 1
    issues, total = [], 0
    for label, store in stores:
        if not store or not os.path.isdir(store):
            issues.append(("other", store or f"Kho {label}", f"Kho {label} không tồn tại"))
            continue
        if only is None or store in only:
            problem = check_temp_cycle(store, make_dir=True)
            if problem:
                issues.append((problem[0], store, f"Kho {label}: không tạo/đổi tên thư mục được ({problem[1]})"))
        backups = list_backups(store)
        if only is not None:
            backups = [b for b in backups if b in only or store in only]
        print(f"  Kho {label}: {store}  ->  {len(backups)} bản backup{' (kiểm tra sâu từng file vì A/B khác ổ)' if deep else ''}")
        for index, backup in enumerate(backups, 1):
            issues.extend(check_backup(backup, deep))
            if index % 50 == 0:
                print(f"    ... đã kiểm tra {index}/{len(backups)}")
        total += len(backups)
    return total, issues


def backup_of(path, stores):
    """Thư mục con cấp 1 của kho/ổ chứa path (đơn vị để báo cáo và cấp quyền)."""
    for _, store in stores:
        if not store:
            continue
        base = store.rstrip("\\/") + os.sep
        if path.lower().startswith(base.lower()):
            return os.path.join(store, path[len(base):].split(os.sep)[0])
    return path


def backup_dir_of(path):
    """Thư mục backup gần nhất (có Info.plist) chứa path; không có thì trả về chính thư mục đó."""
    current = path if os.path.isdir(path) else os.path.dirname(path)
    probe = current
    while True:
        if os.path.isfile(os.path.join(probe, "Info.plist")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return current
        probe = parent


def normalize_target(text):
    text = text.strip().strip('"').strip()
    if len(text) == 1 and text.isalpha():
        text += ":"
    if len(text) == 2 and text[1] == ":":
        text += "\\"
    return os.path.normpath(os.path.abspath(text))


def scan_tree(start, unit_root, deep=False):
    """Duyệt cây thư mục, kiểm tra quyền xóa/đổi tên thư mục và file.

    Thư mục có Info.plist được coi là backup: kiểm tra thư mục, Info.plist và tạo/đổi tên/xóa file tạm.
    Chế độ nhanh (mặc định) không đi vào từng file bên trong backup vì quyền NTFS kế thừa từ thư mục;
    deep=True kiểm tra thêm từng file (rất chậm với ổ có hàng trăm backup).
    Mỗi thư mục cấp 1 chỉ giữ vài mẫu lỗi cho mỗi loại để không tràn màn hình/bộ nhớ.
    """
    issues, counts, per_unit = [], {}, {}
    stats = {"dirs": 0, "files": 0, "backups": 0}
    units = [("", unit_root)]
    drive_root = os.path.splitdrive(start)[0] + os.sep
    last_progress = [time.monotonic()]

    def progress():
        now = time.monotonic()
        if now - last_progress[0] >= 3:
            last_progress[0] = now
            print(f"    ... {stats['dirs']} thư mục, {stats['files']} file, {stats['backups']} backup", flush=True)

    seen = set()

    def add(kind, path, detail):
        if (kind, path) in seen:
            return
        seen.add((kind, path))
        counts[kind] = counts.get(kind, 0) + 1
        key = (backup_of(path, units), kind)
        per_unit[key] = per_unit.get(key, 0) + 1
        if per_unit[key] <= SAMPLES_PER_UNIT:
            issues.append((kind, path, detail))

    def on_error(exc):
        add(classify(win_code(exc)), exc.filename or start, f"không mở được thư mục ({exc.strerror or exc})")

    problem = check_temp_cycle(start, make_dir=True)
    if problem:
        add(problem[0], start, f"không tạo/đổi tên thư mục được ({problem[1]})")
    backup_tree = set()
    for root, dirs, files in os.walk(start, onerror=on_error):
        stats["dirs"] += 1
        progress()
        is_backup = "Info.plist" in files
        if is_backup and not deep:
            stats["backups"] += 1
            stats["files"] += 1
            dirs[:] = []
            for kind, path, detail in check_backup(root, False):
                add(kind, path, detail)
            continue
        keep = []
        for name in dirs:
            low = name.lower()
            if (low in SYSTEM_DIRS_ANYWHERE or name in SKIP_DIRS or name.startswith(CHECK_PREFIX)
                    or (root == drive_root and low in SYSTEM_DIRS_AT_DRIVE_ROOT)):
                continue
            path = os.path.join(root, name)
            attrs = kernel32.GetFileAttributesW(path)
            if attrs != INVALID_ATTRS and attrs & FILE_ATTRIBUTE_REPARSE_POINT:
                continue
            keep.append(name)
            code = open_for_delete(path, True)
            if code:
                add(classify(code), path, f"không đổi tên/xóa được thư mục (WinError {code})")
        dirs[:] = keep

        inside = is_backup or os.path.dirname(root) in backup_tree
        if inside:
            backup_tree.add(root)
        if is_backup:
            stats["backups"] += 1
            problem = check_temp_cycle(root)
            if problem:
                add(problem[0], root, problem[1])
        for name in files:
            path = os.path.join(root, name)
            stats["files"] += 1
            if stats["files"] % 2000 == 0:
                progress()
            if inside and is_readonly(path):
                add("readonly", path, "file trong backup bật Chỉ đọc (Restore/chuyển kho không ghi/xóa được)")
                continue
            code = open_for_delete(path, False)
            if code:
                add(classify(code), path, f"không xóa/thay thế được file (WinError {code})")

    for (unit, kind), n in per_unit.items():
        if n > SAMPLES_PER_UNIT:
            issues.append((kind, unit, f"... trong thư mục này có tổng cộng {n} mục lỗi loại này"))
    return stats, issues, counts


def scan_targets(targets, unit_root, deep=False):
    total = {"dirs": 0, "files": 0, "backups": 0}
    issues, counts = [], {}
    for target in targets:
        print(f"  Đang quét: {target}", flush=True)
        stats, found, found_counts = scan_tree(target, unit_root, deep)
        for key in total:
            total[key] += stats[key]
        issues.extend(found)
        for kind, n in found_counts.items():
            counts[kind] = counts.get(kind, 0) + n
    summary = [f"Thư mục đã quét : {total['dirs']}",
               f"File đã kiểm tra: {total['files']}",
               f"Backup phát hiện: {total['backups']}"]
    return summary, issues, counts


def report(summary, issues, stores, counts=None):
    if counts is None:
        counts = {}
        for kind, _, _ in issues:
            counts[kind] = counts.get(kind, 0) + 1
    bad_units = {backup_of(path, stores) for _, path, _ in issues}
    print()
    print("=" * 66)
    for line in summary:
        print(f"  {line}")
    print(f"  Thư mục/backup có vấn đề : {len(bad_units)}")
    for kind in ("perm", "readonly", "lock", "other"):
        if counts.get(kind):
            print(f"    - {KIND_LABEL[kind]}: {counts[kind]}")
    print("=" * 66)
    shown_owner = set()
    for kind, path, detail in issues[:40]:
        print(f"[{KIND_LABEL[kind]}] {path}\n    {detail}")
        if kind == "perm" and path not in shown_owner and os.path.exists(path):
            shown_owner.add(path)
            print(f"    Chủ sở hữu: {owner_of(path)}")
    if len(issues) > 40:
        print(f"... và {len(issues) - 40} lỗi khác")


def whoami():
    try:
        return subprocess.run(["whoami"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}"


def is_admin():
    try:
        return bool(shell32.IsUserAnAdmin())
    except OSError:
        return False


def run_elevated(plan_path):
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS
    info.lpVerb = "runas"
    info.lpFile = sys.executable
    info.lpParameters = f'"{os.path.abspath(__file__)}" --apply "{plan_path}"'
    info.nShow = 1
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        return ctypes.get_last_error()
    kernel32.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
    code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
    kernel32.CloseHandle(info.hProcess)
    return 0 if code.value == 0 else -int(code.value)


def apply_plan(plan_path):
    """Chạy trong cửa sổ Admin: bỏ Chỉ đọc và cấp quyền Modify cho đúng tài khoản chạy TikTool."""
    with open(plan_path, "r", encoding="utf-8-sig") as stream:
        plan = json.load(stream)
    failed = 0
    for folder in plan["readonly_dirs"]:
        pattern = os.path.join(folder, "*")
        print(f"attrib -R \"{pattern}\" /S /D")
        failed |= subprocess.run(["attrib", "-R", pattern, "/S", "/D"]).returncode
    for target in plan["targets"]:
        print(f"\nicacls \"{target}\" /grant \"{plan['account']}:(OI)(CI)M\" /T /C /Q")
        failed |= subprocess.run(["icacls", target, "/grant", f"{plan['account']}:(OI)(CI)M", "/T", "/C", "/Q"]).returncode
    print("\nĐã chạy xong. Cửa sổ chính sẽ tự kiểm tra lại.")
    input("Nhấn Enter để đóng cửa sổ Admin...")
    return 1 if failed else 0


def ask(question):
    try:
        return input(f"{question} (y/n): ").strip().lower() in ("y", "yes", "c", "co")
    except EOFError:
        return False


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    if len(sys.argv) == 3 and sys.argv[1] == "--apply":
        return apply_plan(sys.argv[2])

    account = whoami()
    print("KIỂM TRA QUYỀN KHO BACKUP - TIKTOOL PRO V4")
    print(f"Tài khoản Windows đang chạy: {account}")
    if is_admin():
        print("CẢNH BÁO: tool đang chạy bằng quyền Admin, kết quả có thể tốt hơn thực tế.\n"
              "          Nên đóng lại và mở bằng double-click bình thường (giống cách chạy TikTool).")
    print("Hãy đóng TikTool và các cửa sổ File Explorer đang mở Kho A/B trước khi kiểm tra.\n")

    args = sys.argv[1:]
    deep = "--sau" in args
    target = " ".join(a for a in args if a != "--sau").strip()
    if not target:
        print("Chọn chế độ kiểm tra:")
        print("  1. Kho A/B trong settings.json (mặc định)")
        print("  2. Cả một ổ đĩa hoặc một thư mục bất kỳ (ví dụ: E:   hoặc   F:\\backups)")
        try:
            if input("Chọn 1 hoặc 2 (Enter = 1): ").strip() == "2":
                target = input("Nhập ổ hoặc thư mục cần kiểm tra: ").strip()
                if not target:
                    print("Chưa nhập ổ/thư mục.")
                    return 1
                deep = ask("Kiểm tra sâu TỪNG FILE trong backup? (rất chậm, Enter/n = nhanh theo thư mục)")
        except EOFError:
            pass
        print()

    if target:
        root = normalize_target(target)
        if not os.path.isdir(root):
            print(f"Không tìm thấy ổ/thư mục: {root}")
            return 1
        stores = [("Ổ", root)]
        print(f"Kiểm tra toàn bộ: {root}  [{'SÂU từng file' if deep else 'NHANH theo thư mục'}]"
              "  (bỏ qua System Volume Information, $RECYCLE.BIN, thư mục Windows)")

        def recheck(paths):
            return scan_targets(paths, root, deep)

        summary, issues, counts = recheck([root])
    else:
        try:
            stores = load_stores()
        except (OSError, ValueError) as exc:
            print(f"Không đọc được {SETTINGS_FP}: {exc}")
            return 1

        def recheck(paths):
            total, found = run_checks(stores, only=set(paths))
            return [f"Tổng số backup đã kiểm tra : {total}"], found, None

        total, issues = run_checks(stores)
        summary, counts = [f"Tổng số backup đã kiểm tra : {total}"], None

    report(summary, issues, stores, counts)
    if not issues:
        print("\nKẾT LUẬN: Quyền NTFS OK. Nếu Restore vẫn lỗi lẻ tẻ thì nguyên nhân không phải do quyền\n"
              "(hãy xem log: file bị khóa tạm, lỗi Pair/USB, hoặc app bản cũ).")
        return 0

    if any(k == "lock" for k, _, _ in issues):
        print("\nGỢI Ý file bị khóa: đóng File Explorer đang mở kho, tạm tắt quét của phần mềm diệt virus,\n"
              "hoặc thêm thư mục Kho A/B vào danh sách loại trừ của Windows Defender.")

    fixable = [(k, p) for k, p, _ in issues if k in ("perm", "readonly")]
    if not fixable:
        return 1
    readonly_dirs = sorted({backup_dir_of(p) for k, p in fixable if k == "readonly"})
    store_paths = [s for _, s in stores if s and os.path.isdir(s)]
    perm_units = sorted({backup_of(p, stores) for k, p in fixable if k == "perm"})
    if any(p in store_paths for p in perm_units) or len(perm_units) > ROOT_FIX_THRESHOLD:
        targets = store_paths
    else:
        targets = perm_units

    if targets:
        print(f"\nSẽ cấp quyền Modify cho tài khoản \"{account}\" trên {len(targets)} thư mục:")
        for item in targets[:10]:
            print(f"  - {item}")
        if len(targets) > 10:
            print(f"  ... và {len(targets) - 10} thư mục khác")
    if readonly_dirs:
        print(f"\nSẽ bỏ thuộc tính Chỉ đọc trong {len(readonly_dirs)} thư mục backup:")
        for item in readonly_dirs[:10]:
            print(f"  - {item}")
        if len(readonly_dirs) > 10:
            print(f"  ... và {len(readonly_dirs) - 10} thư mục khác")
    if not ask("\nSửa ngay? Windows sẽ hỏi quyền Admin"):
        print("Đã bỏ qua, không thay đổi gì.")
        return 1

    fd, plan_path = tempfile.mkstemp(prefix="tt_permfix_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump({"account": account, "targets": targets, "readonly_dirs": readonly_dirs}, stream, ensure_ascii=False)
    try:
        result = apply_plan(plan_path) if is_admin() else run_elevated(plan_path)
    finally:
        os.unlink(plan_path)
    if result == 1223:
        print("Bạn đã từ chối quyền Admin, chưa sửa gì.")
        return 1
    if result > 0:
        print(f"Không mở được cửa sổ Admin (WinError {result}).")
        return 1

    print("\nKiểm tra lại các mục vừa sửa...")
    covered = [t.rstrip("\\/").lower() + os.sep for t in targets]
    only = sorted(set(targets) | {d for d in readonly_dirs
                                  if not any((d.lower() + os.sep).startswith(c) for c in covered)})
    summary, remaining, _ = recheck(only)
    remaining = [i for i in remaining if i[0] in ("perm", "readonly")]
    if not remaining:
        print("KẾT QUẢ: Đã sửa xong, tất cả mục lỗi quyền giờ đều OK.")
        return 0
    report(summary, remaining, stores)
    print("\nVẫn còn lỗi quyền. Có thể thư mục có quyền Deny riêng hoặc chủ sở hữu là SID cũ.\n"
          "Thử trong PowerShell (Run as administrator), thay <thư mục> bằng đường dẫn bị lỗi:\n"
          f"  takeown /F \"<thư mục>\" /R /D Y\n"
          f"  icacls \"<thư mục>\" /grant \"{account}:(OI)(CI)M\" /T /C /Q")
    return 1


if __name__ == "__main__":
    sys.exit(main())
