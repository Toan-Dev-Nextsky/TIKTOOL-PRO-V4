import os
import sys
import re
import time
import shutil
import json
import sqlite3
import hashlib
import plistlib
import threading
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ================== BẢNG MÀU UI/UX PRO MAX (MODERN HIGH-CONTRAST LIGHT DASHBOARD) ==================
COLOR_BG_DARK = "#F1F5F9"          # Nền chính Slate-100 (Dịu mắt, sang trọng)
COLOR_APP_BG = "#F1F5F9"           # Nền tổng thể
COLOR_HEADER_BG = "#FFFFFF"        # Header Trắng Thuần Sạch Sẽ
COLOR_PANEL_BG = "#FFFFFF"         # Nền Panel Cấu hình Trắng
COLOR_DEVICE_ZONE = "#F1F5F9"      # Nền Khung Thiết bị Slate-100
COLOR_CONFIRM_ZONE = "#FFFFFF"     # Nền Khung Phân bổ List Trắng
COLOR_CARD_BG = "#FFFFFF"          # Nền Thẻ Thiết Bị Trắng

COLOR_WHITE_BORDER = "#CBD5E1"     # Viền phân cách Slate-300
COLOR_BORDER_MD = "#E2E8F0"        # Viền mềm Slate-200

COLOR_ACCENT = "#0284C7"           # Xanh Dương Chọn Tab Restore (Sky-600)
COLOR_DISABLED = "#E2E8F0"         # Nền Tab Không Chọn (Slate-200)
COLOR_TEXT_WHITE = "#0F172A"       # Chữ Đen Than Sắc Nét (Slate-900, 100% Readability)
COLOR_TEXT_MUTED = "#64748B"       # Chữ Xám Phụ (Slate-500)
COLOR_LOG_TEXT = "#F8FAFC"         # Chữ Nhật ký Sáng trong Terminal Đen OLED

# BUNDLE IDS TIKTOK & PATHS
BIDS_TIKTOK = ["com.ss.iphone.ugc.tiktok", "com.zhiliaoapp.musically", "com.ss.iphone.ugc.Aweme"]
BIDS_TIKTOK_LITE = ["com.ss.iphone.ugc.tiktok.lite", "com.zhiliaoapp.musicallylite"]
REQ_BACKUP_FILES = ["Manifest.db", "Info.plist", "Manifest.plist"]

# PRESETS NGÔN NGỮ PHỔ BIẾN
LANG_PRESETS = [
    ("Tiếng Nhật (Japan)", "ja_JP|ja"),
    ("Tiếng Việt (Vietnam)", "vi_VN|vi"),
    ("Tiếng Anh (US)", "en_US|en"),
    ("Tiếng Trung (Giản thể)", "zh_CN|zh"),
    ("Tiếng Trung (Phồn thể)", "zh_TW|zh"),
    ("Tiếng Hàn (Korea)", "ko_KR|ko"),
    ("Tiếng Pháp (France)", "fr_FR|fr"),
    ("Tiếng Đức (Germany)", "de_DE|de")
]

# ================== CẤU HÌNH HỆ THỐNG ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)

os.environ["PATH"] = BASE_DIR + os.pathsep + os.environ.get("PATH", "")

SETTINGS_FP = os.path.join(BASE_DIR, "settings.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
IPAS_DIR = os.path.join(BASE_DIR, "ipas")
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(IPAS_DIR, exist_ok=True)

MAX_CONCURRENCY = 20
SEMAPHORE = threading.Semaphore(MAX_CONCURRENCY)
_sema = SEMAPHORE  # Alias semaphore hỗ trợ worker set language
PAIR_LOCK = threading.Lock()

# CACHE HỆ THỐNG
TRUSTED_CACHE = set()
RESTORE_LOCK_CACHE = {} 

DEFAULT_SETTINGS = {
    "storeA": os.path.join(BASE_DIR, "backups_A"),
    "storeB": os.path.join(BASE_DIR, "backups_B"),
    "generalBackupDir": os.path.join(BASE_DIR, "backups"),
    "ipasDir": IPAS_DIR,
    "removeTikTok": False,
    "removeTikTokLite": True,
    "deepFlags": True,
    "langLocale": "ja_JP|ja",            # Mặc định là tiếng Nhật
    "patchBackupLangBeforeRestore": False, # Bật/Tắt can thiệp trực tiếp file Backup
    "setLangAfterActive": True,           # Đặt ngôn ngữ tự động sau khi Batch Activate
    "active": "A"                         # Kho nguồn mặc định: "A" (A->B) hoặc "B" (B->A)
}

def get_no_window_kwargs():
    kwargs = {}
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs["startupinfo"] = startupinfo
        kwargs["creationflags"] = 0x08000000
    return kwargs

def _ts(): return datetime.now().strftime("%H:%M:%S")

def which_tool(tool_name):
    ext = ".exe" if os.name == "nt" else ""
    local_path = os.path.join(BASE_DIR, tool_name + ext)
    if os.path.isfile(local_path): return local_path
    return shutil.which(tool_name)

def _fixed_ios_exe():
    """Hàm tìm kiếm đường dẫn thi hành ios.exe"""
    return which_tool("ios") or "ios.exe"

def _ios_usable():
    """Kiểm tra ios.exe có khả dụng hay không"""
    exe = _fixed_ios_exe()
    if os.path.isfile(exe) or shutil.which("ios"):
        return True, exe
    return False, "Không tìm thấy công cụ ios.exe trong thư mục gốc ứng dụng."

def parse_ios_ver(v_str):
    try:
        p = [int(x) for x in str(v_str).replace("iOS", "").strip().split(".")]
        while len(p) < 3: p.append(0)
        return tuple(p[:3])
    except Exception: return (0, 0, 0)

def _parse_lang_preset(preset: str):
    """Hàm phụ trợ tách chuỗi Locale/Language"""
    preset = (preset or "").strip()
    if "|" in preset:
        locale, lang = preset.split("|", 1)
        return locale.strip(), lang.strip()
    return "ja_JP", "ja"  # Mặc định Tiếng Nhật

def run_capture(cmd_list):
    """Chạy lệnh thu thập output ngắn hạn"""
    try:
        p = subprocess.run(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **get_no_window_kwargs())
        return p.returncode, p.stdout.strip()
    except Exception as e:
        return -1, str(e)

# ================== CAN THIỆP TRỰC TIẾP FILE BACKUP (FIX DIGEST ERROR 205) ==================
def patch_backup_language(backup_folder_path, lang_code="ja", locale_code="ja_JP", log_fn=None):
    """
    Sửa trực tiếp ngôn ngữ & locale trong thư mục Backup iPhone (Đã fix triệt để lỗi MBErrorDomain/205)
    """
    manifest_db = os.path.join(backup_folder_path, "Manifest.db")
    if not os.path.exists(manifest_db):
        if log_fn: log_fn("Không tìm thấy Manifest.db trong thư mục Backup!", is_err=True)
        return False

    domain = "HomeDomain"
    relative_path = "Library/Preferences/.GlobalPreferences.plist"
    
    try:
        conn = sqlite3.connect(manifest_db)
        cursor = conn.cursor()
        cursor.execute("SELECT fileID FROM Files WHERE domain=? AND relativePath=?", (domain, relative_path))
        row = cursor.fetchone()
        
        if not row:
            if log_fn: log_fn("Không tìm thấy .GlobalPreferences.plist trong Database Backup!", is_err=True)
            conn.close()
            return False

        file_id = row[0]
        target_file_path = os.path.join(backup_folder_path, file_id[:2], file_id)

        if not os.path.exists(target_file_path):
            target_file_path = os.path.join(backup_folder_path, file_id)
            if not os.path.exists(target_file_path):
                if log_fn: log_fn(f"Không thấy file vật lý {file_id} trong Backup!", is_err=True)
                conn.close()
                return False

        # 1. Đọc & Cập nhật Plist
        with open(target_file_path, "rb") as f:
            plist_data = plistlib.load(f)

        plist_data["AppleLanguages"] = [f"{lang_code}-VN", lang_code]
        plist_data["AppleLocale"] = locale_code

        with open(target_file_path, "wb") as f:
            plistlib.dump(plist_data, f, fmt=plistlib.FMT_BINARY)

        # 2. Xóa Digest signature blob (file = NULL) để iOS không bị lệch mã băm Digest (MBErrorDomain 205)
        cursor.execute("UPDATE Files SET file = NULL, flags = 1 WHERE fileID = ?", (file_id,))
        conn.commit()
        conn.close()
        
        if log_fn: log_fn(f"Đã can thiệp file Backup ➔ Ngôn ngữ: {lang_code}/{locale_code} (Fixed Digest 205)")
        return True
    except Exception as e:
        if log_fn: log_fn(f"Lỗi khi patch ngôn ngữ Backup: {e}", is_err=True)
        return False

# ================== HELPER FUNCTIONS ==================
def check_device_trust(udid):
    """Kiểm tra Trust siêu tốc với timeout tối đa 0.5s"""
    if udid in TRUSTED_CACHE:
        return True

    exe = which_tool("idevicepair")
    if not exe: return False
    try:
        p = subprocess.run([exe, "-u", udid, "validate"], 
                           stdout=subprocess.PIPE, 
                           stderr=subprocess.PIPE, 
                           timeout=0.5, 
                           **get_no_window_kwargs())
        is_ok = (p.returncode == 0)
        if is_ok:
            TRUSTED_CACHE.add(udid)
        return is_ok
    except Exception:
        return False

def run_stream(cmd_list, on_line=None):
    last = []
    try:
        p = subprocess.Popen(cmd_list, cwd=BASE_DIR, env=os.environ.copy(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, **get_no_window_kwargs())
    except Exception as e:
        if on_line: on_line(f"Lỗi: {e}", is_err=True)
        return 127, []

    buffer = bytearray()
    while True:
        try: chunk = p.stdout.read(1)
        except Exception: break
        if not chunk:
            if p.poll() is not None: break
            time.sleep(0.01)
            continue
        char = chunk[0]
        if char in (10, 13):
            if buffer:
                try: s = buffer.decode("utf-8", errors="replace").strip()
                except Exception: s = ""
                if s:
                    last.append(s)
                    if len(last) > 200: last.pop(0)
                    if on_line:
                        low = s.lower()
                        is_err = ("error" in low) or ("failed" in low) or ("mberrordomain" in low)
                        on_line(s, is_err=is_err)
                buffer.clear()
        else: buffer.append(char)
    p.wait()
    return p.returncode, last

def get_connected_udids():
    exe = which_tool("idevice_id")
    if not exe: return []
    try:
        out = subprocess.check_output([exe, "-l"], text=True, encoding="utf-8", errors="ignore", **get_no_window_kwargs())
        return [line.strip() for line in out.splitlines() if re.fullmatch(r"[0-9a-fA-F-]{16,}", line.strip())]
    except Exception: return []

def ideviceinfo_k(u, k):
    exe = which_tool("ideviceinfo")
    if not exe: return ""
    for _ in range(2):
        try: return subprocess.check_output([exe, "-u", u, "--simple", "-k", k], timeout=1.0, text=True, encoding="utf-8", errors="ignore", **get_no_window_kwargs()).strip()
        except Exception: time.sleep(0.1)
    return ""

def pair_validate(udid, log_fn):
    with PAIR_LOCK:
        code, _ = run_stream(["idevicepair", "-u", udid, "validate"], on_line=lambda s, **_: log_fn(s))
        if code != 0:
            code2, _ = run_stream(["idevicepair", "-u", udid, "pair"], on_line=lambda s, **_: log_fn(s))
            return code2 == 0
        return True

# ================== PRO RESTORE CORE HELPERS ==================
def ensure_status_plist(root):
    sp = os.path.join(root, "Status.plist")
    if os.path.exists(sp) and os.path.getsize(sp) > 0:
        return True
    payload = {"SnapshotState": "Finished", "Version": 2, "Date": datetime.now(), "IsFullBackup": True}
    try:
        with open(sp, "wb") as f:
            plistlib.dump(payload, f)
        return True
    except Exception:
        return False

def verify_backup_layout(folder):
    miss = [f for f in REQ_BACKUP_FILES if not os.path.exists(os.path.join(folder, f))]
    if not miss and not os.path.exists(os.path.join(folder, "Status.plist")):
        ensure_status_plist(folder)
    return miss

def read_backup_info(folder_path):
    info_plist = os.path.join(folder_path, "Info.plist")
    if not os.path.exists(info_plist): return None
    try:
        with open(info_plist, "rb") as f: pl = plistlib.load(f)
        v = pl.get("Product Version") or "0.0"
        lb = pl.get("Last Backup Date")
        last_dt = lb if isinstance(lb, datetime) else None
        return {
            "path": folder_path,
            "folder_name": os.path.basename(folder_path),
            "udid": pl.get("UniqueDeviceID") or "UNKNOWN",
            "ios_str": str(v),
            "ios_t": parse_ios_ver(v),
            "last_dt": last_dt
        }
    except Exception: return None

def list_valid_backups(parent_dir):
    out = []
    try:
        subs = [d for d in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, d))]
    except Exception: subs = []
    for d in subs:
        full = os.path.join(parent_dir, d)
        if not verify_backup_layout(full):
            b_info = read_backup_info(full)
            if b_info:
                out.append(b_info)
    out.sort(key=lambda bk: (bk["last_dt"] or datetime.min), reverse=False)
    return out

def patch_info_plist(backup_root, udid, log_fn=None):
    fp = os.path.join(backup_root, "Info.plist")
    if not os.path.exists(fp): return False
    try:
        with open(fp, "rb") as f: data = plistlib.load(f)
        old = data.get("UniqueDeviceID")
        if old != udid:
            data["UniqueDeviceID"] = udid
            with open(fp, "wb") as f: plistlib.dump(data, f)
            if log_fn: log_fn(f"Patch UDID: {old} → {udid}")
        return True
    except Exception as e:
        if log_fn: log_fn(f"Lỗi Patch UDID: {e}", is_err=True)
        return False

def uninstall_app_any(udid, bundle_ids, label_name, card, log_fn):
    if card: card.push_step(f"Gỡ {label_name}...")
    ok = False
    for bid in bundle_ids:
        cmd = ["ideviceinstaller", "-u", udid, "uninstall", bid]
        rc, _ = run_stream(cmd, on_line=lambda s, is_err=False: log_fn(s, is_err=is_err))
        if rc == 0: ok = True; break
    if card: card.push_step(f"Gỡ {label_name} {'thành công' if ok else 'bỏ qua'}")
    return ok

# ================== CARD THIẾT BỊ LƯỚI 3 COLUMNS ==================
class DeviceCard(tk.Frame):
    def __init__(self, master, udid, info, app_ref=None):
        is_trusted = info.get("trusted", True)
        border_col = "#10B981" if is_trusted else "#EF4444"
        
        super().__init__(master, bg="#FFFFFF", highlightbackground=border_col, highlightthickness=1, bd=0)
        self.udid = udid
        self.info = info
        self.app_ref = app_ref

        # Dòng 1: Tiêu đề thiết bị (Trái) & Nút thao tác nhanh (Phải)
        top_row = tk.Frame(self, bg="#FFFFFF")
        top_row.pack(fill="x", padx=6, pady=(4, 1))

        if not is_trusted:
            title_txt = f"⚠️ {info.get('name', 'iPhone')} • NOT TRUST"
            title_color = "#E11D48"
        else:
            title_txt = f"📱 {info.get('name', 'iPhone')} • iOS {info.get('ios', '?')}"
            title_color = "#0F172A"

        self.lbl_top = tk.Label(top_row, text=title_txt, font=("Segoe UI", 10, "bold"), fg=title_color, bg="#FFFFFF", anchor="w")
        self.lbl_top.pack(side="left")

        if self.app_ref:
            btn_single_act = tk.Button(top_row, text="⚡ Active", font=("Segoe UI", 8, "bold"), bg="#059669", activebackground="#10B981", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", padx=6, pady=2, command=self._trigger_single_active)
            btn_single_act.pack(side="right", padx=(2, 0))

            btn_single_lng = tk.Button(top_row, text="🌐 Lang", font=("Segoe UI", 8, "bold"), bg="#2563EB", activebackground="#1D4ED8", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", padx=6, pady=2, command=self._trigger_single_lang)
            btn_single_lng.pack(side="right")

        # Dòng 2: Model & ECID tinh gọn 1 dòng duy nhất
        ecid_str = info.get('ecid', '—') or '—'
        model_str = info.get('model', 'N/A') or 'N/A'
        lbl_sub = tk.Label(self, text=f"Model: {model_str}  •  ECID: {ecid_str}", font=("Consolas", 9), fg="#0284C7", bg="#FFFFFF", anchor="w")
        lbl_sub.pack(fill="x", padx=6, pady=(0, 2))

        # Dòng 3: Trạng thái bước hiện tại (lbl_step)
        step_txt = "Sẵn sàng" if is_trusted else "⚠️ BẤM TIN CẬY"
        step_fg = "#059669" if is_trusted else "#DC2626"
        step_bg = "#FFFFFF" if is_trusted else "#FEF2F2"

        self.lbl_step = tk.Label(self, text=step_txt, font=("Segoe UI", 9, "bold"), fg=step_fg, bg=step_bg, anchor="w")
        self.lbl_step.pack(fill="x", padx=6, pady=(0, 2))

        # Dòng 4: Thanh tiến trình + % nhãn
        prog_f = tk.Frame(self, bg="#FFFFFF")
        prog_f.pack(fill="x", padx=6, pady=(0, 4))

        self.pb = ttk.Progressbar(prog_f, mode="determinate", style="WinXP.Horizontal.TProgressbar")
        self.pb.pack(side="left", fill="x", expand=True)

        self.lbl_task = tk.Label(prog_f, text="0%", font=("Consolas", 9, "bold"), fg="#64748B", bg="#FFFFFF", width=4, anchor="e")
        self.lbl_task.pack(side="right", padx=(2, 0))

    def _trigger_single_lang(self):
        if self.app_ref:
            threading.Thread(target=self.app_ref._set_language_locale_worker, args=(self.udid,), daemon=True).start()

    def _trigger_single_active(self):
        if self.app_ref:
            threading.Thread(target=self.app_ref._batch_activate_worker, args=(self.udid,), daemon=True).start()

    def update_trust_status(self, is_trusted, info):
        self.info = info
        border_col = "#10B981" if is_trusted else "#EF4444"
        self.configure(highlightbackground=border_col, highlightthickness=1)

        if not is_trusted:
            title_txt = f"⚠️ {info.get('name', 'iPhone')} • NOT TRUST"
            title_color = "#E11D48"
            step_txt = "⚠️ BẤM TIN CẬY"
            step_fg = "#DC2626"
            step_bg = "#FEF2F2"
        else:
            title_txt = f"📱 {info.get('name', 'iPhone')} • iOS {info.get('ios', '?')}"
            title_color = "#0F172A"
            step_txt = "Sẵn sàng"
            step_fg = "#059669"
            step_bg = "#FFFFFF"

        self.lbl_top.config(text=title_txt, fg=title_color)
        self.lbl_step.config(text=step_txt, fg=step_fg, bg=step_bg)

    def set_pct(self, p):
        try:
            val = float(str(p).replace("%", "").strip())
            self.pb["value"] = val
            self.lbl_task.config(text=f"{int(val)}%")
        except Exception: pass

    def set_task(self, text):
        self.lbl_task.config(text=text)

    def push_step(self, text):
        self.lbl_step.config(text=text)

# ================== MAIN APP (BB MANAGER PRO) ==================
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("BB MANAGER PRO - FULL RESTORE & LANGUAGE ENGINE")
        self.geometry("1280x920")
        self.configure(bg="#F1F5F9")

        self.rows = {}
        self.lock = threading.Lock()
        self.last_json_mtime = 0
        self.pending_restore_map = []
        self.current_mode = "RESTORE"
        self.licensed = True
        self.restore_done_count = 0  # Bộ đếm restore thành công trong phiên

        # Variables
        self.var_lang_locale = tk.StringVar(value=DEFAULT_SETTINGS["langLocale"])
        self.var_patch_backup_lang = tk.BooleanVar(value=DEFAULT_SETTINGS["patchBackupLangBeforeRestore"])
        self.var_set_lang_after_active = tk.BooleanVar(value=DEFAULT_SETTINGS["setLangAfterActive"])
        self.var_active_store = tk.StringVar(value="A")  # Kho nguồn: A hoặc B

        self._setup_style()
        self._setup_ui()
        self._start_json_sync_loop()
        self._start_polling()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("WinXP.Horizontal.TProgressbar", troughcolor="#E2E8F0", background="#0284C7", borderwidth=0, relief="flat", thickness=6)

    def _setup_ui(self):
        # 1. TOP BRANDING & CONTROLS PANEL (Clean Light Surface)
        top_card = tk.Frame(self, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        top_card.pack(fill="x", side="top", padx=12, pady=(10, 4))

        # --- HÀNG 1: LOGO & CẤU HÌNH NGÔN NGỮ ---
        row1 = tk.Frame(top_card, bg="#FFFFFF")
        row1.pack(fill="x", padx=10, pady=(8, 8))

        # Bên trái: Logo + Thông tin Developer
        left_logo = tk.Frame(row1, bg="#FFFFFF")
        left_logo.pack(side="left")

        box_logo = tk.Frame(left_logo, bg="#EFF6FF", highlightbackground="#3B82F6", highlightthickness=1)
        box_logo.pack(side="left", padx=(0, 10))

        lbl_logo = tk.Label(box_logo, text="BB PRO", font=("Segoe UI", 13, "bold"), fg="#1D4ED8", bg="#EFF6FF")
        lbl_logo.pack(padx=10, pady=2)

        lbl_dev = tk.Label(left_logo, text="Developer by Tumaemo • Full iPhone Tool Pro Engine Synchronized", font=("Segoe UI", 9), fg="#64748B", bg="#FFFFFF")
        lbl_dev.pack(side="left")

        # Bên phải: Cấu hình ngôn ngữ
        right_lang = tk.Frame(row1, bg="#FFFFFF")
        right_lang.pack(side="right")

        lbl_lang_title = tk.Label(right_lang, text="🌐 CẤU HÌNH NGÔN NGỮ:", font=("Segoe UI", 9, "bold"), fg="#0F172A", bg="#FFFFFF")
        lbl_lang_title.pack(side="left", padx=(0, 6))

        self.lbl_current_lang = tk.Label(right_lang, text=f"[Hiện tại: {self.var_lang_locale.get()}]", font=("Consolas", 9, "bold"), fg="#0284C7", bg="#F1F5F9", highlightbackground="#CBD5E1", highlightthickness=1)
        self.lbl_current_lang.pack(side="left", padx=(0, 6), ipady=2, ipadx=4)

        btn_change_lang = tk.Button(right_lang, text="⚙️ ĐỔI NGÔN NGỮ POPUP", font=("Segoe UI", 8, "bold"), bg="#D97706", activebackground="#F59E0B", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.open_lang_popup)
        btn_change_lang.pack(side="left", padx=(0, 6), ipady=3, ipadx=6)

        btn_only_set_lang = tk.Button(right_lang, text="🌐 CHỈ ĐỔI NGÔN NGỮ LỆNH (TẤT CẢ)", font=("Segoe UI", 8, "bold"), bg="#2563EB", activebackground="#3B82F6", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.set_language_locale_all)
        btn_only_set_lang.pack(side="left", ipady=3, ipadx=6)

        # Đường kẻ phân cách nhẹ
        sep = tk.Frame(top_card, bg="#E2E8F0", height=1)
        sep.pack(fill="x", padx=10)

        # --- HÀNG 2: KÍCH HOẠT THIẾT BỊ (BATCH ACTIVATE) ---
        row2 = tk.Frame(top_card, bg="#FFFFFF")
        row2.pack(fill="x", padx=10, pady=(8, 8))

        lbl_act_title = tk.Label(row2, text="⚡ KÍCH HOẠT THIẾT BỊ:", font=("Segoe UI", 9, "bold"), fg="#0F172A", bg="#FFFFFF")
        lbl_act_title.pack(side="left", padx=(0, 8))

        btn_batch_activate = tk.Button(row2, text="⚡ BATCH ACTIVATE (ALL)", font=("Segoe UI", 9, "bold"), bg="#059669", activebackground="#10B981", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.batch_activate_all)
        btn_batch_activate.pack(side="left", padx=(0, 10), ipady=3, ipadx=8)

        chk_lang_after_active = tk.Checkbutton(
            row2,
            text="🔑 Đặt ngôn ngữ sau khi Active",
            font=("Segoe UI", 9, "bold"),
            fg="#0F172A",
            bg="#FFFFFF",
            selectcolor="#F1F5F9",
            activebackground="#FFFFFF",
            activeforeground="#0F172A",
            variable=self.var_set_lang_after_active,
            command=self._save_settings_from_ui
        )
        chk_lang_after_active.pack(side="left")

        # Badge luồng xử lý bên phải
        flow_badge = tk.Frame(row2, bg="#F8FAFC", highlightbackground="#E2E8F0", highlightthickness=1)
        flow_badge.pack(side="right")

        lbl_f1 = tk.Label(flow_badge, text="Activate", font=("Consolas", 8, "bold"), fg="#059669", bg="#F8FAFC")
        lbl_f1.pack(side="left", padx=(6, 2), pady=2)
        lbl_farr1 = tk.Label(flow_badge, text="->", font=("Consolas", 8), fg="#94A3B8", bg="#F8FAFC")
        lbl_farr1.pack(side="left", pady=2)
        lbl_f2 = tk.Label(flow_badge, text="Skip Setup", font=("Consolas", 8, "bold"), fg="#4F46E5", bg="#F8FAFC")
        lbl_f2.pack(side="left", padx=2, pady=2)
        lbl_farr2 = tk.Label(flow_badge, text="->", font=("Consolas", 8), fg="#94A3B8", bg="#F8FAFC")
        lbl_farr2.pack(side="left", pady=2)
        lbl_f3 = tk.Label(flow_badge, text="Set Lang", font=("Consolas", 8, "bold"), fg="#0284C7", bg="#F8FAFC")
        lbl_f3.pack(side="left", padx=(2, 6), pady=2)

        # 2. KHUNG CHUYỂN TAB & CẤU HÌNH (RESTORE & BACKUP)
        self.frame_tab_section = tk.Frame(self, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        self.frame_tab_section.pack(fill="x", padx=12, pady=4)

        # Thanh nút bấm Tab
        self.frame_tab_control = tk.Frame(self.frame_tab_section, bg="#F1F5F9")
        self.frame_tab_control.pack(fill="x", padx=4, pady=4)

        self.btn_tab_restore = tk.Button(self.frame_tab_control, text="[↺] KHÔI PHỤC (RESTORE PRO)", font=("Segoe UI", 10, "bold"), bg="#0284C7", fg="#FFFFFF", relief="flat", bd=0, command=self._switch_to_restore, cursor="hand2")
        self.btn_tab_restore.pack(side="left", padx=(0, 4), ipady=6, expand=True, fill="x")

        self.btn_tab_backup = tk.Button(self.frame_tab_control, text="[💾] SAO LƯU (BACKUP)", font=("Segoe UI", 10, "bold"), bg="#E2E8F0", fg="#475569", relief="flat", bd=0, command=self._switch_to_backup, cursor="hand2")
        self.btn_tab_backup.pack(side="left", ipady=6, expand=True, fill="x")

        # Nội dung panel bên trong
        self.panel_content = tk.Frame(self.frame_tab_section, bg="#FFFFFF")
        self.panel_content.pack(fill="x", padx=6, pady=4)

        self.frame_restore_panel = tk.Frame(self.panel_content, bg="#FFFFFF")
        self.frame_backup_panel = tk.Frame(self.panel_content, bg="#FFFFFF")

        self._setup_restore_panel()
        self._setup_backup_panel()
        self._switch_to_restore()

        # 3. CONTAINER GIỮA (LƯỚI THIẾT BỊ KẾT NỐI / BẢNG PHÂN BỔ)
        self.middle_container = tk.Frame(self, bg="#F1F5F9")
        self.middle_container.pack(fill="both", expand=True, padx=12, pady=4)

        # 3A. KHUNG THIẾT BỊ KẾT NỐI
        self.frame_dev_zone = tk.Frame(self.middle_container, bg="#F1F5F9")
        self.frame_dev_zone.pack(fill="both", expand=True)

        dev_title_bar = tk.Frame(self.frame_dev_zone, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        dev_title_bar.pack(fill="x", padx=2, pady=(0, 6))

        left_dev_bar = tk.Frame(dev_title_bar, bg="#FFFFFF")
        left_dev_bar.pack(side="left", padx=10, pady=4)

        lbl_dev_title = tk.Label(left_dev_bar, text="📱 THIẾT BỊ KẾT NỐI", font=("Segoe UI", 10, "bold"), fg="#0F172A", bg="#FFFFFF")
        lbl_dev_title.pack(side="left", padx=(0, 6))

        # Badge đếm số thiết bị nhỏ gọn, không chiếm diện tích của bộ đếm kho
        box_dev_badge = tk.Frame(left_dev_bar, bg="#EFF6FF", highlightbackground="#3B82F6", highlightthickness=1)
        box_dev_badge.pack(side="left")
        self.lbl_stat_total_dev = tk.Label(box_dev_badge, text="0 máy", font=("Segoe UI", 9, "bold"), fg="#1D4ED8", bg="#EFF6FF")
        self.lbl_stat_total_dev.pack(padx=8, pady=1)

        # Cụm BỘ ĐẾM KHO ƯU TIÊN NỔI BẬT (TỔNG KHO, ĐÃ CHUYỂN, CÒN LẠI)
        right_stat_bar = tk.Frame(dev_title_bar, bg="#FFFFFF")
        right_stat_bar.pack(side="right", padx=6, pady=3)

        # 1. Thẻ TỔNG KHO 📁 (Sáng rõ nét)
        card_tk = tk.Frame(right_stat_bar, bg="#F8FAFC", highlightbackground="#CBD5E1", highlightthickness=1)
        card_tk.pack(side="left", padx=4)
        lbl_c1_t = tk.Label(card_tk, text="TỔNG KHO 📁", font=("Segoe UI", 8, "bold"), fg="#64748B", bg="#F8FAFC")
        lbl_c1_t.pack(padx=14, pady=(2, 0))
        self.lbl_stat_tong_kho = tk.Label(card_tk, text="0", font=("Segoe UI", 13, "bold"), fg="#0F172A", bg="#F8FAFC")
        self.lbl_stat_tong_kho.pack(padx=14, pady=(0, 2))

        # 2. Thẻ ĐÃ CHUYỂN 📁 (Xanh nổi bật)
        card_dc = tk.Frame(right_stat_bar, bg="#ECFDF5", highlightbackground="#10B981", highlightthickness=1)
        card_dc.pack(side="left", padx=4)
        lbl_c2_t = tk.Label(card_dc, text="ĐÃ CHUYỂN 📁", font=("Segoe UI", 8, "bold"), fg="#059669", bg="#ECFDF5")
        lbl_c2_t.pack(padx=14, pady=(2, 0))
        self.lbl_stat_da_chuyen = tk.Label(card_dc, text="0", font=("Segoe UI", 13, "bold"), fg="#059669", bg="#ECFDF5")
        self.lbl_stat_da_chuyen.pack(padx=14, pady=(0, 2))

        # 3. Thẻ CÒN LẠI (Cam nổi bật)
        card_cl = tk.Frame(right_stat_bar, bg="#FFFBEB", highlightbackground="#F59E0B", highlightthickness=1)
        card_cl.pack(side="left", padx=4)
        lbl_c3_t = tk.Label(card_cl, text="CÒN LẠI", font=("Segoe UI", 8, "bold"), fg="#D97706", bg="#FFFBEB")
        lbl_c3_t.pack(padx=14, pady=(2, 0))
        self.lbl_stat_con_lai = tk.Label(card_cl, text="0", font=("Segoe UI", 13, "bold"), fg="#D97706", bg="#FFFBEB")
        self.lbl_stat_con_lai.pack(padx=14, pady=(0, 2))

        # Nút Reset nhanh cho bộ đếm chuyển
        btn_reset_cnt = tk.Button(right_stat_bar, text="↺", font=("Segoe UI", 9, "bold"), fg="#64748B", bg="#F1F5F9", activebackground="#E2E8F0", activeforeground="#0F172A", relief="flat", bd=0, cursor="hand2", command=self._reset_restore_counter)
        btn_reset_cnt.pack(side="left", padx=(3, 2), ipady=4, ipadx=4)

        self.dev_canvas = tk.Canvas(self.frame_dev_zone, bg="#F1F5F9", highlightthickness=0)
        self.dev_scrollbar = ttk.Scrollbar(self.frame_dev_zone, orient="vertical", command=self.dev_canvas.yview)
        self.grid_container = tk.Frame(self.dev_canvas, bg="#F1F5F9")

        self.dev_canvas.bind('<Configure>', self._on_canvas_configure)
        self.grid_container.bind("<Configure>", lambda e: self.dev_canvas.configure(scrollregion=self.dev_canvas.bbox("all")))
        self.dev_canvas_window = self.dev_canvas.create_window((0, 0), window=self.grid_container, anchor="nw")
        self.dev_canvas.configure(yscrollcommand=self.dev_scrollbar.set)

        self.dev_canvas.pack(side="left", fill="both", expand=True, padx=2, pady=(0, 4))
        self.dev_scrollbar.pack(side="right", fill="y", pady=(0, 4))

        # 3B. KHUNG PHÂN BỔ BẢNG BACKUP DẠNG LIST (2-LAYER MATCHING ENGINE)
        self.frame_confirm_zone = tk.Frame(self.middle_container, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)

        confirm_title_bar = tk.Frame(self.frame_confirm_zone, bg="#F8FAFC")
        confirm_title_bar.pack(fill="x", padx=10, pady=6)

        lbl_conf_title = tk.Label(confirm_title_bar, text="📋 PHÂN BỔ THÔNG MINH (2-LAYER MATCHING ENGINE)", font=("Segoe UI", 10, "bold"), fg="#D97706", bg="#F8FAFC")
        lbl_conf_title.pack(side="left")

        self.conf_canvas = tk.Canvas(self.frame_confirm_zone, bg="#FFFFFF", highlightthickness=0)
        self.conf_scrollbar = ttk.Scrollbar(self.frame_confirm_zone, orient="vertical", command=self.conf_canvas.yview)
        self.conf_list_container = tk.Frame(self.conf_canvas, bg="#FFFFFF")

        self.conf_list_container.bind("<Configure>", lambda e: self.conf_canvas.configure(scrollregion=self.conf_canvas.bbox("all")))
        self.conf_canvas.create_window((0, 0), window=self.conf_list_container, anchor="nw")
        self.conf_canvas.configure(yscrollcommand=self.conf_scrollbar.set)

        self.conf_canvas.pack(side="top", fill="both", expand=True, padx=10, pady=4)
        self.conf_scrollbar.pack(side="right", fill="y", pady=4)

        self.conf_btn_bar = tk.Frame(self.frame_confirm_zone, bg="#FFFFFF")
        self.conf_btn_bar.pack(side="bottom", fill="x", padx=10, pady=8)

        self.btn_run_conf = tk.Button(self.conf_btn_bar, text="XÁC NHẬN RESTORE CHUYỂN KHO", font=("Segoe UI", 11, "bold"), bg="#059669", activebackground="#10B981", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self._execute_confirmed_restore)
        self.btn_run_conf.pack(fill="x", pady=(0, 4), ipady=6)

        self.btn_cancel_conf = tk.Button(self.conf_btn_bar, text="HỦY BỎ", font=("Segoe UI", 10, "bold"), bg="#EF4444", activebackground="#DC2626", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self._hide_confirm_frame)
        self.btn_cancel_conf.pack(fill="x", pady=(0, 2), ipady=4)

        # 4. KHU VỰC THỐNG KÊ STATUS DƯỚI CÙNG (CLEAN PILL BADGES)
        frame_trust_status = tk.Frame(self, bg="#FFFFFF", highlightbackground="#CBD5E1", highlightthickness=1)
        frame_trust_status.pack(fill="x", side="bottom", padx=12, pady=(0, 6))

        box_trusted = tk.Frame(frame_trust_status, bg="#ECFDF5", highlightbackground="#10B981", highlightthickness=1)
        box_trusted.pack(side="left", padx=(8, 4), pady=6)

        self.lbl_trust_count = tk.Label(box_trusted, text="Trust : 0", font=("Segoe UI", 9, "bold"), fg="#059669", bg="#ECFDF5", anchor="center")
        self.lbl_trust_count.pack(padx=12, pady=4)

        self.box_count = tk.Frame(frame_trust_status, bg="#F1F5F9", highlightbackground="#CBD5E1", highlightthickness=1)
        self.box_count.pack(side="left", padx=4, pady=6)

        self.lbl_dev_count = tk.Label(self.box_count, text=" 0 ", font=("Segoe UI", 9, "bold"), fg="#0F172A", bg="#F1F5F9")
        self.lbl_dev_count.pack(padx=12, pady=4)

        box_untrusted = tk.Frame(frame_trust_status, bg="#FEF2F2", highlightbackground="#EF4444", highlightthickness=1)
        box_untrusted.pack(side="left", padx=4, pady=6)

        self.lbl_untrust_count = tk.Label(box_untrusted, text="Not Trust : 0", font=("Segoe UI", 9, "bold"), fg="#DC2626", bg="#FEF2F2", anchor="center")
        self.lbl_untrust_count.pack(padx=12, pady=4)

        # Ô đếm Restore thành công
        box_restore_done = tk.Frame(frame_trust_status, bg="#EFF6FF", highlightbackground="#0284C7", highlightthickness=1)
        box_restore_done.pack(side="left", padx=4, pady=6)

        self.lbl_restore_done_status = tk.Label(box_restore_done, text="Restored : 0", font=("Segoe UI", 9, "bold"), fg="#0284C7", bg="#EFF6FF", anchor="center")
        self.lbl_restore_done_status.pack(padx=12, pady=4)

        # 5. NHẬT KÝ HỆ THỐNG (TERMINAL OLED DARK BOX)
        frame_log = tk.Frame(self, bg="#FFFFFF", height=135, highlightbackground="#CBD5E1", highlightthickness=1)
        frame_log.pack(fill="x", side="bottom", padx=12, pady=(0, 4))
        frame_log.pack_propagate(False)

        lbl_log_head = tk.Label(frame_log, text="NHẬT KÝ HỆ THỐNG", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#F1F5F9")
        lbl_log_head.pack(fill="x", anchor="w", padx=2, pady=(2, 0))

        self.txt_log = tk.Text(frame_log, font=("Consolas", 9), bg="#0F172A", fg="#F8FAFC", bd=0, highlightthickness=0)
        self.txt_log.pack(fill="both", expand=True, padx=6, pady=4)
        self.txt_log.tag_config("err", foreground="#EF4444")

    # ================== POPUP ĐỔI NGÔN NGỮ ==================
    def open_lang_popup(self):
        """Hiện Popup chọn ngôn ngữ"""
        pop = tk.Toplevel(self)
        pop.title("Cấu Hình Ngôn Ngữ / Locale")
        pop.geometry("440x380")
        pop.configure(bg="#FFFFFF")
        pop.resizable(False, False)
        pop.transient(self)
        pop.grab_set()

        lbl_t = tk.Label(pop, text="CHỌN NGÔN NGỮ VÀ LOCALE", font=("Segoe UI", 11, "bold"), fg="#0F172A", bg="#FFFFFF")
        lbl_t.pack(pady=(14, 4))

        lbl_sub = tk.Label(pop, text="Chọn ngôn ngữ có sẵn bên dưới hoặc tự nhập định dạng locale|lang:", font=("Segoe UI", 8), fg="#64748B", bg="#FFFFFF", wraplength=400)
        lbl_sub.pack(pady=(0, 10))

        frame_lb = tk.Frame(pop, bg="#FFFFFF")
        frame_lb.pack(fill="both", expand=True, padx=20)

        lb = tk.Listbox(frame_lb, bg="#F8FAFC", fg="#0F172A", selectbackground="#2563EB", selectforeground="#FFFFFF", font=("Segoe UI", 9), bd=0, highlightbackground="#CBD5E1", highlightthickness=1)
        lb.pack(fill="both", expand=True)

        for name, code in LANG_PRESETS:
            lb.insert("end", f"  {name}  ➜  ({code})")

        frame_custom = tk.Frame(pop, bg="#FFFFFF")
        frame_custom.pack(fill="x", padx=20, pady=12)

        lbl_c = tk.Label(frame_custom, text="Tùy chỉnh (locale|lang):", font=("Segoe UI", 9, "bold"), fg="#0F172A", bg="#FFFFFF")
        lbl_c.pack(side="left")

        ent_custom = tk.Entry(frame_custom, font=("Consolas", 9), bg="#F8FAFC", fg="#0284C7", insertbackground="#0F172A", bd=0, highlightbackground="#CBD5E1", highlightthickness=1)
        ent_custom.pack(side="right", fill="x", expand=True, padx=(8, 0), ipady=3)
        ent_custom.insert(0, self.var_lang_locale.get())

        def on_select_preset(evt):
            sel = lb.curselection()
            if sel:
                idx = sel[0]
                val = LANG_PRESETS[idx][1]
                ent_custom.delete(0, "end")
                ent_custom.insert(0, val)

        lb.bind("<<ListboxSelect>>", on_select_preset)

        def apply_lang():
            val = ent_custom.get().strip()
            if not val or "|" not in val:
                messagebox.showerror("Định dạng sai", "Vui lòng nhập đúng định dạng: locale|lang\nVí dụ: ja_JP|ja hoặc vi_VN|vi", parent=pop)
                return
            self.var_lang_locale.set(val)
            self.lbl_current_lang.config(text=f"[Hiện tại: {val}]")
            self._save_settings_from_ui()
            pop.destroy()

        btn_save = tk.Button(pop, text="ÁP DỤNG & LƯU", font=("Segoe UI", 10, "bold"), bg="#10B981", activebackground="#059669", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=apply_lang)
        btn_save.pack(fill="x", padx=20, pady=(0, 16), ipady=6)

    # ================== LOGIC SET LANGUAGE / LOCALE WORKER (LỆNH TRỰC TIẾP CHỦ ĐỘNG) ==================
    def _set_language_locale_worker(self, udid):
        """Hàm đặt ngôn ngữ chủ động bằng lệnh ios.exe qua USB"""
        task = "Set Language"
        row = self.rows.get(udid)
        if not _sema.acquire(timeout=1):
            if row:
                row.set_task("Đang chờ slot…")
            _sema.acquire()
        try:
            locale, lang = _parse_lang_preset(self.var_lang_locale.get())
            ios_exe = _fixed_ios_exe()
            
            if row:
                row.set_pct(10)
                row.set_task(f"{task} 10%")
                row.push_step(f"Đang đổi sang {lang}/{locale}...")
                
            cmd = [ios_exe, "lang", f"--setlocale={locale}", f"--setlang={lang}", f"--udid={udid}", "--nojson"]
            self.log(udid, "RUN: " + " ".join(cmd))
            
            rc, out = run_capture(cmd)
            self.log(udid, out or f"exit {rc}", is_err=(rc != 0))
            
            if row:
                if rc == 0:
                    row.set_pct(100)
                    row.set_task(f"Đặt {lang}/{locale} thành công")
                    row.push_step(f"Đã đổi {lang}/{locale}")
                else:
                    row.set_task(f"Đặt {lang}/{locale} lỗi (rc={rc})")
                    row.push_step(f"Lỗi Set Lang (rc={rc})")
        finally:
            _sema.release()

    def set_language_locale_all(self):
        """Kích hoạt đổi ngôn ngữ cho tất cả thiết bị bằng lệnh ios.exe"""
        if not self.licensed:
            messagebox.showwarning("Chưa kích hoạt", "Vui lòng kích hoạt để dùng tính năng này.")
            return
        ok, msg = _ios_usable()
        if not ok:
            messagebox.showerror("Set Language/Locale", f"Không tìm thấy ios.exe hợp lệ.\n\n{msg}")
            return
        if not self.rows:
            messagebox.showinfo("Set Language/Locale", "Không có thiết bị kết nối.")
            return
                
        loc, lng = _parse_lang_preset(self.var_lang_locale.get())
        self.log("SYSTEM", f"Bắt đầu cài đặt ngôn ngữ {lng}/{loc} bằng lệnh cho toàn bộ máy...")
        for udid in list(self.rows.keys()):
            threading.Thread(target=self._set_language_locale_worker, args=(udid,), daemon=True).start()

    # ================== BATCH ACTIVATE ENGINE ==================
    def batch_activate_all(self):
        """Kích hoạt hàng loạt tất cả thiết bị: Activate → Skip Setup → Set Lang"""
        # Kiểm tra ios.exe
        ok, msg = _ios_usable()
        if not ok:
            messagebox.showerror("Batch Activation", f"Không tìm thấy ios.exe hợp lệ để skip setup.\n\n{msg}")
            return

        # Kiểm tra ideviceactivation.exe
        if not which_tool("ideviceactivation"):
            messagebox.showerror("Batch Activation", "Không tìm thấy ideviceactivation.exe")
            return

        if not self.rows:
            messagebox.showinfo("Batch Activation", "Không có thiết bị.")
            return

        self.log("SYSTEM", "Bắt đầu Batch Activate cho toàn bộ thiết bị...")
        for udid in list(self.rows.keys()):
            threading.Thread(target=self._batch_activate_worker, args=(udid,), daemon=True).start()

    def _batch_activate_worker(self, udid):
        """Worker xử lý kích hoạt từng thiết bị: 3 giai đoạn Activate → Skip Setup → Set Lang"""
        task = "Batch Activate"
        row = self.rows.get(udid)

        # Quản lý semaphore
        if not _sema.acquire(timeout=1):
            if row:
                row.set_task("Đang chờ slot…")
            _sema.acquire()

        try:
            # === GIAI ĐOẠN 1: ideviceactivation activate (5% → 40%) ===
            if row:
                row.set_pct(5)
                row.set_task(f"{task} 5%")
                row.push_step("Đang kích hoạt...")

            idevact = which_tool("ideviceactivation")
            cmd = [idevact, "activate", "-u", udid, "-b"]
            self.log(udid, "RUN: " + " ".join(cmd))

            rc, out = run_capture(cmd)
            self.log(udid, out or f"exit {rc}", is_err=(rc != 0))

            # Kiểm tra kết quả activate
            low = (out or "").lower()
            activate_ok = (rc == 0) or ("already activated" in low) or ("device is already activated" in low)

            if not activate_ok:
                if row:
                    row.set_task(f"{task} lỗi")
                    row.push_step("Activate thất bại")
                self.log(udid, "Kích hoạt thất bại!", is_err=True)
                return

            # === GIAI ĐOẠN 2: ios.exe prepare --skip-all (45% → 75%) ===
            if row:
                row.set_pct(45)
                row.set_task(f"{task} 45%")
                row.push_step("Skip Setup Assistant...")

            ios_exe = _fixed_ios_exe()
            cmd2 = [ios_exe, "prepare", "--skip-all", f"--udid={udid}", "--nojson"]
            self.log(udid, "RUN: " + " ".join(cmd2))

            rc2, out2 = run_capture(cmd2)
            self.log(udid, out2 or f"exit {rc2}", is_err=(rc2 != 0))

            # Kiểm tra kết quả skip setup
            low2 = (out2 or "").lower()
            skip_ok = (rc2 == 0) or ('"ok"' in low2) or (low2.strip() == "ok")

            if not skip_ok:
                if row:
                    row.set_task(f"{task} lỗi")
                    row.push_step("Skip Setup lỗi")
                self.log(udid, "Skip Setup Assistant thất bại!", is_err=True)
                return

            if row:
                row.set_pct(80)
                row.set_task(f"{task} 80%")
                row.push_step("Skip Setup OK")

            # === GIAI ĐOẠN 3: Set Language & Locale (80% → 100%) ===
            if self.var_set_lang_after_active.get():
                locale, lang = _parse_lang_preset(self.var_lang_locale.get())

                cmd3 = [ios_exe, "lang", f"--setlocale={locale}", f"--setlang={lang}", f"--udid={udid}", "--nojson"]
                self.log(udid, "RUN: " + " ".join(cmd3))

                rc3, out3 = run_capture(cmd3)
                self.log(udid, out3 or f"exit {rc3}", is_err=(rc3 != 0))

            # === HOÀN TẤT ===
            if row:
                row.set_pct(100)
                row.set_task(f"{task} thành công")
                row.push_step("Đã kích hoạt ✓")
            self.log(udid, "Batch Activate hoàn tất thành công.")

        finally:
            _sema.release()

    # ================== CHỌN KHO NGUỒN & ĐẾM BACKUP ==================
    def _on_store_switch(self):
        """Cập nhật UI khi đổi kho nguồn A/B và đếm số backup cả 2 kho"""
        active = self.var_active_store.get()
        path_a = self.lbl_path_a.cget("text").strip()
        path_b = self.lbl_path_b.cget("text").strip()
        count_a = self._count_backups_in_dir(path_a)
        count_b = self._count_backups_in_dir(path_b)

        # Cập nhật cụm thống kê TỔNG KHO, ĐÃ CHUYỂN, CÒN LẠI
        curr_src_count = count_a if active == "A" else count_b
        transferred = self.restore_done_count
        total_scope = curr_src_count + transferred
        remaining = curr_src_count

        if hasattr(self, "lbl_stat_tong_kho"):
            self.lbl_stat_tong_kho.config(text=str(total_scope))
        if hasattr(self, "lbl_stat_da_chuyen"):
            self.lbl_stat_da_chuyen.config(text=str(transferred))
        if hasattr(self, "lbl_stat_con_lai"):
            self.lbl_stat_con_lai.config(text=str(remaining))

        if hasattr(self, "lbl_title_a"):
            if active == "A":
                self.lbl_title_a.config(text=f"MỤC NHẬP (KHO A: {count_a} iPhone)", fg="#34D399")
                self.lbl_title_b.config(text=f"MỤC XUẤT (KHO B: {count_b} iPhone)", fg="#FBBF24")
                self.btn_label_a.config(bg="#10B981")
                self.btn_label_b.config(bg="#F59E0B")
                self.box_a.config(highlightbackground="#10B981", highlightthickness=2)
                self.box_b.config(highlightbackground="#F59E0B", highlightthickness=1)
                self.lbl_flow_direction.config(text="A ➜ B", fg="#34D399")
                self.btn_start_restore.config(
                    text=f"⚡ BẮT ĐẦU RESTORE PRO (A ➜ B • {count_a} iPhone)", 
                    bg="#059669", 
                    activebackground="#10B981"
                )
                self.lbl_store_info.config(text=f"📱 Nguồn Kho A ({count_a} iPhone) ➜ Đích Kho B ({count_b} iPhone)", fg="#34D399")
            else:
                self.lbl_title_a.config(text=f"MỤC XUẤT (KHO A: {count_a} iPhone)", fg="#FBBF24")
                self.lbl_title_b.config(text=f"MỤC NHẬP (KHO B: {count_b} iPhone)", fg="#34D399")
                self.btn_label_a.config(bg="#F59E0B")
                self.btn_label_b.config(bg="#10B981")
                self.box_a.config(highlightbackground="#F59E0B", highlightthickness=1)
                self.box_b.config(highlightbackground="#10B981", highlightthickness=2)
                self.lbl_flow_direction.config(text="B ➜ A", fg="#FB923C")
                self.btn_start_restore.config(
                    text=f"⚡ BẮT ĐẦU RESTORE PRO (B ➜ A • {count_b} iPhone)", 
                    bg="#EA580C", 
                    activebackground="#F97316"
                )
                self.lbl_store_info.config(text=f"📱 Nguồn Kho B ({count_b} iPhone) ➜ Đích Kho A ({count_a} iPhone)", fg="#FB923C")

        self._save_settings_from_ui()

    def _count_backups_in_dir(self, dir_path):
        """Đếm số thư mục backup hợp lệ trong một thư mục"""
        if not os.path.isdir(dir_path):
            return 0
        backups = list_valid_backups(dir_path)
        return len(backups)

    def _count_restore_done(self):
        self.restore_done_count += 1
        self._update_restore_counter()
        self._on_store_switch()

    def _reset_restore_counter(self):
        self.restore_done_count = 0
        self._update_restore_counter()
        self._on_store_switch()

    def _update_restore_counter(self):
        if hasattr(self, "lbl_restore_done"):
            self.lbl_restore_done.config(text=f"Đã Restore: {self.restore_done_count}")
        if hasattr(self, "lbl_restore_done_status"):
            self.lbl_restore_done_status.config(text=f"Restored : {self.restore_done_count}")
        if hasattr(self, "lbl_stat_da_chuyen"):
            self.lbl_stat_da_chuyen.config(text=str(self.restore_done_count))

    def _on_canvas_configure(self, event):
        self.dev_canvas.itemconfig(self.dev_canvas_window, width=event.width)

    # ---------------- BẢNG CẤU HÌNH RESTORE ----------------
    def _setup_restore_panel(self):
        f = self.frame_restore_panel
        f.columnconfigure((0, 1), weight=1)

        # === HÀNG 0: CHỌN KHO NGUỒN (RADIO A / B) + THÔNG TIN SỐ LƯỢNG ===
        store_select_bar = tk.Frame(f, bg="#0D1524", highlightbackground="#2D3B54", highlightthickness=1)
        store_select_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(2, 6))

        lbl_store_title = tk.Label(store_select_bar, text="📦 CHỌN KHO NGUỒN:", font=("Segoe UI", 9, "bold"), fg="#E2E8F0", bg="#0D1524")
        lbl_store_title.pack(side="left", padx=(10, 5), pady=5)

        rb_a = tk.Radiobutton(store_select_bar, text="Kho A ➜ B", font=("Segoe UI", 9, "bold"), fg="#34D399", bg="#0D1524", selectcolor="#050811", activebackground="#0D1524", activeforeground="#34D399", variable=self.var_active_store, value="A", command=self._on_store_switch)
        rb_a.pack(side="left", padx=8, pady=5)

        rb_b = tk.Radiobutton(store_select_bar, text="Kho B ➜ A", font=("Segoe UI", 9, "bold"), fg="#FBBF24", bg="#0D1524", selectcolor="#050811", activebackground="#0D1524", activeforeground="#FBBF24", variable=self.var_active_store, value="B", command=self._on_store_switch)
        rb_b.pack(side="left", padx=8, pady=5)

        # Thông tin số lượng backup trong kho nguồn
        self.lbl_store_info = tk.Label(store_select_bar, text="📱 Kho nguồn: đang quét...", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#0D1524")
        self.lbl_store_info.pack(side="left", padx=15, pady=5)

        # Hiện tại chiều chuyển
        self.lbl_flow_direction = tk.Label(store_select_bar, text="A ➜ B", font=("Segoe UI", 10, "bold"), fg="#34D399", bg="#0D1524")
        self.lbl_flow_direction.pack(side="right", padx=15, pady=5)

        # === HÀNG 1: KHO A & KHO B (MỤC NHẬP / MỤC XUẤT) ===
        # Ô Kho A
        col_a = tk.Frame(f, bg="#151E2E")
        col_a.grid(row=1, column=0, sticky="ew", padx=4, pady=2)
        col_a.columnconfigure(0, weight=1)

        self.lbl_title_a = tk.Label(col_a, text="MỤC NHẬP (KHO A)", font=("Segoe UI", 9, "bold"), fg="#34D399", bg="#151E2E", anchor="w")
        self.lbl_title_a.pack(fill="x", pady=(0, 2))

        self.box_a = tk.Frame(col_a, bg="#0D1524", highlightbackground="#10B981", highlightthickness=2, bd=0)
        self.box_a.pack(fill="x")
        self.box_a.columnconfigure(1, weight=1)

        self.btn_label_a = tk.Button(self.box_a, text="📂 Chọn", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg="#10B981", activebackground="#059669", activeforeground="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=lambda: self._browse("STORE_A"))
        self.btn_label_a.grid(row=0, column=0, padx=6, pady=6)

        self.lbl_path_a = tk.Label(self.box_a, text=DEFAULT_SETTINGS["storeA"], font=("Consolas", 9), fg="#F8FAFC", bg="#0D1524", anchor="w", cursor="hand2")
        self.lbl_path_a.grid(row=0, column=1, sticky="ew", padx=4, pady=6)
        self.lbl_path_a.bind("<Button-1>", lambda e: self._browse("STORE_A"))

        # Ô Kho B
        col_b = tk.Frame(f, bg="#151E2E")
        col_b.grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        col_b.columnconfigure(0, weight=1)

        self.lbl_title_b = tk.Label(col_b, text="MỤC XUẤT (KHO B)", font=("Segoe UI", 9, "bold"), fg="#FBBF24", bg="#151E2E", anchor="w")
        self.lbl_title_b.pack(fill="x", pady=(0, 2))

        self.box_b = tk.Frame(col_b, bg="#0D1524", highlightbackground="#F59E0B", highlightthickness=1, bd=0)
        self.box_b.pack(fill="x")
        self.box_b.columnconfigure(1, weight=1)

        self.btn_label_b = tk.Button(self.box_b, text="📂 Chọn", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg="#F59E0B", activebackground="#D97706", activeforeground="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=lambda: self._browse("STORE_B"))
        self.btn_label_b.grid(row=0, column=0, padx=6, pady=6)

        self.lbl_path_b = tk.Label(self.box_b, text=DEFAULT_SETTINGS["storeB"], font=("Consolas", 9), fg="#F8FAFC", bg="#0D1524", anchor="w", cursor="hand2")
        self.lbl_path_b.grid(row=0, column=1, sticky="ew", padx=4, pady=6)
        self.lbl_path_b.bind("<Button-1>", lambda e: self._browse("STORE_B"))

        # CHECKBOX CAN THIỆP TRỰC TIẾP FILE BACKUP
        box_opt = tk.Frame(f, bg="#151E2E")
        box_opt.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=(6, 4))

        chk_patch_lang = tk.Checkbutton(
            box_opt, 
            text="🔑 Can thiệp ngôn ngữ trực tiếp vào file Backup trước khi Restore", 
            font=("Segoe UI", 9, "bold"), 
            fg="#F8FAFC", 
            bg="#151E2E", 
            selectcolor="#0D1524", 
            activebackground="#151E2E", 
            activeforeground="#F8FAFC", 
            variable=self.var_patch_backup_lang, 
            command=self._save_settings_from_ui
        )
        chk_patch_lang.pack(side="left")

        # BỘ ĐẾM RESTORE THÀNH CÔNG
        box_restore_pill = tk.Frame(box_opt, bg="#0C4A6E", highlightbackground="#0284C7", highlightthickness=1)
        box_restore_pill.pack(side="right", padx=4)

        self.lbl_restore_done = tk.Label(box_restore_pill, text="Đã Restore: 0", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#0C4A6E")
        self.lbl_restore_done.pack(padx=8, pady=2)

        self.btn_start_restore = tk.Button(f, text="⚡ BẮT ĐẦU RESTORE PRO", font=("Segoe UI", 11, "bold"), bg="#059669", activebackground="#10B981", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.start_restore_all)
        self.btn_start_restore.grid(row=3, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 6), ipady=7)

        # Quét số lượng backup ban đầu
        self.after(500, self._on_store_switch)

    # ---------------- BẢNG CẤU HÌNH BACKUP ----------------
    def _setup_backup_panel(self):
        f = self.frame_backup_panel
        f.columnconfigure(0, weight=1)

        box_top = tk.Frame(f, bg="#151E2E")
        box_top.pack(fill="x", padx=4, pady=4)
        box_top.columnconfigure(0, weight=1)

        col_bk = tk.Frame(box_top, bg="#151E2E")
        col_bk.grid(row=0, column=0, sticky="ew")

        lbl_title_bk = tk.Label(col_bk, text="KHO BACKUP", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#151E2E", anchor="w")
        lbl_title_bk.pack(fill="x", pady=(0, 2))

        box_bk = tk.Frame(col_bk, bg="#0D1524", highlightbackground="#2D3B54", highlightthickness=1, bd=0)
        box_bk.pack(fill="x")
        box_bk.columnconfigure(1, weight=1)

        btn_label_gen = tk.Button(box_bk, text="📂 Chọn", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg="#2563EB", activebackground="#1D4ED8", activeforeground="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=lambda: self._browse("GEN_DIR"))
        btn_label_gen.grid(row=0, column=0, padx=6, pady=6)

        self.lbl_path_gen = tk.Label(box_bk, text=DEFAULT_SETTINGS["generalBackupDir"], font=("Consolas", 9), fg="#F8FAFC", bg="#0D1524", anchor="w", cursor="hand2")
        self.lbl_path_gen.grid(row=0, column=1, sticky="ew", padx=4, pady=6)
        self.lbl_path_gen.bind("<Button-1>", lambda e: self._browse("GEN_DIR"))

        box_chk = tk.Frame(box_top, bg="#151E2E")
        box_chk.grid(row=0, column=1, sticky="e", padx=(12, 0), pady=(16, 0))

        self.var_tik = tk.BooleanVar(value=False)
        tk.Checkbutton(box_chk, text="Gỡ TikTok", font=("Segoe UI", 9, "bold"), fg="#F8FAFC", bg="#151E2E", selectcolor="#0D1524", activebackground="#151E2E", activeforeground="#F8FAFC", variable=self.var_tik, command=self._save_settings_from_ui).pack(side="left", padx=8)

        self.var_lite = tk.BooleanVar(value=True)
        tk.Checkbutton(box_chk, text="Gỡ TikTok Lite", font=("Segoe UI", 9, "bold"), fg="#F8FAFC", bg="#151E2E", selectcolor="#0D1524", activebackground="#151E2E", activeforeground="#F8FAFC", variable=self.var_lite, command=self._save_settings_from_ui).pack(side="left", padx=8)

        self.btn_start_backup = tk.Button(f, text="💾 BẮT ĐẦU SAO LƯU (BACKUP ALL)", font=("Segoe UI", 11, "bold"), bg="#2563EB", activebackground="#1D4ED8", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.start_backup_all)
        self.btn_start_backup.pack(fill="x", padx=4, pady=(4, 6), ipady=7)

    # ---------------- TAB SWITCH ----------------
    def _switch_to_restore(self):
        self.current_mode = "RESTORE"
        self.btn_tab_restore.config(bg="#0284C7", fg="#FFFFFF")
        self.btn_tab_backup.config(bg="#1A263B", fg="#94A3B8")

        self.frame_backup_panel.pack_forget()
        self.frame_restore_panel.pack(fill="x")

    def _switch_to_backup(self):
        self.current_mode = "BACKUP"
        self.btn_tab_backup.config(bg="#0284C7", fg="#FFFFFF")
        self.btn_tab_restore.config(bg="#1A263B", fg="#94A3B8")

        self.frame_restore_panel.pack_forget()
        self.frame_backup_panel.pack(fill="x")

    # ---------------- JSON SYNC ----------------
    def _start_json_sync_loop(self):
        def _check():
            try:
                if os.path.exists(SETTINGS_FP):
                    mtime = os.path.getmtime(SETTINGS_FP)
                    if mtime > self.last_json_mtime:
                        self.last_json_mtime = mtime
                        with open(SETTINGS_FP, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            self._apply_settings_to_ui(data)
            except Exception: pass
            self.after(1000, _check)

        self.after(500, _check)

    def _apply_settings_to_ui(self, data):
        if "storeA" in data and self.lbl_path_a.cget("text") != data["storeA"]: self.lbl_path_a.config(text=data["storeA"])
        if "storeB" in data and self.lbl_path_b.cget("text") != data["storeB"]: self.lbl_path_b.config(text=data["storeB"])
        if "generalBackupDir" in data and self.lbl_path_gen.cget("text") != data["generalBackupDir"]: self.lbl_path_gen.config(text=data["generalBackupDir"])
        if "removeTikTok" in data: self.var_tik.set(bool(data["removeTikTok"]))
        if "removeTikTokLite" in data: self.var_lite.set(bool(data["removeTikTokLite"]))
        if "patchBackupLangBeforeRestore" in data: self.var_patch_backup_lang.set(bool(data["patchBackupLangBeforeRestore"]))
        if "setLangAfterActive" in data: self.var_set_lang_after_active.set(bool(data["setLangAfterActive"]))
        if "active" in data and data["active"] in ("A", "B"): self.var_active_store.set(data["active"])
        if "langLocale" in data and data["langLocale"]:
            self.var_lang_locale.set(data["langLocale"])
            loc, lng = _parse_lang_preset(data["langLocale"])
            self.lbl_current_lang.config(text=f" Hiện tại: {lng}/{loc} ({data['langLocale']}) ")
        self._on_store_switch()

    def _save_settings_from_ui(self):
        try:
            data = DEFAULT_SETTINGS.copy()
            if os.path.exists(SETTINGS_FP):
                with open(SETTINGS_FP, "r", encoding="utf-8") as f: data.update(json.load(f))

            data["storeA"] = self.lbl_path_a.cget("text").strip()
            data["storeB"] = self.lbl_path_b.cget("text").strip()
            data["generalBackupDir"] = self.lbl_path_gen.cget("text").strip()
            data["removeTikTok"] = self.var_tik.get()
            data["removeTikTokLite"] = self.var_lite.get()
            data["langLocale"] = self.var_lang_locale.get()
            data["patchBackupLangBeforeRestore"] = self.var_patch_backup_lang.get()
            data["setLangAfterActive"] = self.var_set_lang_after_active.get()
            data["active"] = self.var_active_store.get()

            with open(SETTINGS_FP, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.last_json_mtime = os.path.getmtime(SETTINGS_FP)
        except Exception: pass

    def _browse(self, mode):
        curr = BASE_DIR
        if mode == "STORE_A": curr = self.lbl_path_a.cget("text")
        elif mode == "STORE_B": curr = self.lbl_path_b.cget("text")
        elif mode == "GEN_DIR": curr = self.lbl_path_gen.cget("text")

        p = filedialog.askdirectory(initialdir=curr)
        if p:
            if mode == "STORE_A": self.lbl_path_a.config(text=p)
            elif mode == "STORE_B": self.lbl_path_b.config(text=p)
            elif mode == "GEN_DIR": self.lbl_path_gen.config(text=p)
            self._save_settings_from_ui()
            self._on_store_switch()

    def log(self, udid, line, is_err=False):
        prefix = (udid[:6] + "...") if udid else "SYSTEM"
        msg = f"[{_ts()}] {prefix}: {line}\n"
        self.after(0, self._write_log, msg, is_err)

    def _write_log(self, msg, is_err):
        try:
            if is_err: self.txt_log.insert("end", msg, "err")
            else: self.txt_log.insert("end", msg)
            self.txt_log.see("end")
        except Exception: pass

    def _build_info(self, u, is_trusted=True):
        if not is_trusted:
            return {
                "name": "iPhone (Not Trust)",
                "model": "N/A",
                "ios": "?",
                "ios_t": (0, 0, 0),
                "imei": "—",
                "sn": "—",
                "ecid": "—",
                "trusted": False
            }

        ios_str = ideviceinfo_k(u, "ProductVersion")
        dev_name = ideviceinfo_k(u, "DeviceName")
        return {
            "name": dev_name if dev_name else "iPhone",
            "model": ideviceinfo_k(u, "ProductType") or "",
            "ios": ios_str if ios_str else "?",
            "ios_t": parse_ios_ver(ios_str),
            "imei": ideviceinfo_k(u, "InternationalMobileEquipmentIdentity") or ideviceinfo_k(u, "IMEI") or "",
            "sn": ideviceinfo_k(u, "SerialNumber") or "",
            "ecid": ideviceinfo_k(u, "UniqueChipID") or "",
            "trusted": True
        }

    # ================== POLLING SIÊU TỐC TỰ ĐỘNG LÀM SẠCH CACHE KHÔNG DELAY ==================
    def _start_polling(self):
        def _poll():
            with ThreadPoolExecutor(max_workers=20) as executor:
                while True:
                    udids = get_connected_udids()
                    current_set = set(udids)
                    
                    for cached_u in list(TRUSTED_CACHE):
                        if cached_u not in current_set:
                            TRUSTED_CACHE.remove(cached_u)

                    if udids:
                        untrusted_targets = [u for u in udids if u not in TRUSTED_CACHE]
                        futures = {u: executor.submit(check_device_trust, u) for u in untrusted_targets}
                        new_results = {u: f.result() for u, f in futures.items()}
                        
                        trust_results = {u: (True if u in TRUSTED_CACHE else new_results.get(u, False)) for u in udids}
                    else:
                        trust_results = {}

                    try:
                        self.after(0, self._sync_cards, udids, trust_results)
                    except Exception:
                        break

                    time.sleep(0.3)

        threading.Thread(target=_poll, daemon=True).start()

    def _relayout_cards_3x4(self):
        for col in range(3):
            self.grid_container.columnconfigure(col, weight=1, uniform="col")

        udid_list = list(self.rows.keys())
        for idx, udid in enumerate(udid_list):
            r = idx // 3
            c = idx % 3
            card = self.rows[udid]
            card.grid_forget()
            card.grid(row=r, column=c, padx=4, pady=3, sticky="ew")

    def _sync_cards(self, current_udids, trust_results):
        with self.lock:
            need_relayout = False
            trusted_cnt = 0
            untrusted_cnt = 0
            now_ts = time.time()

            for udid in list(self.rows.keys()):
                if udid not in current_udids:
                    self.rows[udid].destroy()
                    del self.rows[udid]
                    if udid in RESTORE_LOCK_CACHE: del RESTORE_LOCK_CACHE[udid]
                    need_relayout = True
                    self.log(udid, "Đã ngắt kết nối.")

            for udid in current_udids:
                is_locked_reboot = (udid in RESTORE_LOCK_CACHE and RESTORE_LOCK_CACHE[udid] > now_ts)
                
                if is_locked_reboot:
                    is_trusted = True
                else:
                    is_trusted = trust_results.get(udid, False)

                if is_trusted: trusted_cnt += 1
                else: untrusted_cnt += 1

                if udid not in self.rows:
                    info = self._build_info(udid, is_trusted=is_trusted)
                    card = DeviceCard(self.grid_container, udid, info, app_ref=self)
                    self.rows[udid] = card
                    need_relayout = True
                    self.log(udid, f"Kết nối: {info['name']} • iOS {info['ios']}")
                else:
                    card = self.rows[udid]
                    if is_locked_reboot:
                        card.push_step("Hoàn tất • Đang khởi động lại...")
                    else:
                        if card.info.get("trusted") != is_trusted:
                            info = self._build_info(udid, is_trusted=is_trusted)
                            card.update_trust_status(is_trusted, info)
                            if is_trusted:
                                self.log(udid, f"Đã xác nhận Trust: {info['name']} • iOS {info['ios']}")

            if need_relayout:
                self._relayout_cards_3x4()

            self.lbl_dev_count.config(text=f" {len(self.rows)} ")
            self.lbl_trust_count.config(text=f"Trust : {trusted_cnt}")
            self.lbl_untrust_count.config(text=f"Not Trust : {untrusted_cnt}")
            if hasattr(self, "lbl_stat_total_dev"):
                self.lbl_stat_total_dev.config(text=f"{len(self.rows)} máy")

    # BẢNG PHÂN BỔ HIỂN THỊ CHI TIẾT
    def _show_confirm_frame(self, confirm_items):
        for widget in self.conf_list_container.winfo_children():
            widget.destroy()

        self.btn_run_conf.config(state="normal", bg="#059669")
        self.btn_cancel_conf.config(state="normal", bg="#EF4444")

        self.conf_list_container.columnconfigure(0, weight=1, uniform="conf_col")
        self.conf_list_container.columnconfigure(1, weight=1, uniform="conf_col")

        for idx, item in enumerate(confirm_items):
            r = idx // 2
            c = idx % 2

            cell_f = tk.Frame(self.conf_list_container, bg="#0D1524", highlightbackground="#2D3B54", highlightthickness=1, bd=0)
            cell_f.grid(row=r, column=c, padx=5, pady=4, sticky="ew")

            m_color = "#34D399" if "UDID" in item['match_type'] else "#FBBF24"

            lbl_line1_stt = tk.Label(cell_f, text=f"{idx + 1}. 📂 {item['folder_name']} (iOS {item['bk_ios']})", font=("Segoe UI", 9, "bold"), fg="#38BDF8", bg="#0D1524", anchor="w")
            lbl_line1_stt.pack(side="top", anchor="w", padx=8, pady=(6, 0))

            lbl_line1_dev = tk.Label(cell_f, text=f"   ➔ 📱 {item['dev_name']} (iOS {item['dev_ios']}) [{item['match_type']}]", font=("Segoe UI", 9, "bold"), fg=m_color, bg="#0D1524", anchor="w")
            lbl_line1_dev.pack(side="top", anchor="w", padx=8, pady=(2, 0))

            lbl_line2_udid = tk.Label(cell_f, text=f"   UDID TARGET: {item['udid']}", font=("Consolas", 8), fg="#94A3B8", bg="#0D1524", anchor="w")
            lbl_line2_udid.pack(side="top", anchor="w", padx=8, pady=(2, 6))

        self.frame_dev_zone.pack_forget()
        self.frame_confirm_zone.pack(fill="both", expand=True)

    def _hide_confirm_frame(self):
        self.frame_confirm_zone.pack_forget()
        self.frame_dev_zone.pack(fill="both", expand=True)

    def _execute_confirmed_restore(self):
        self.btn_run_conf.config(state="disabled", bg="#94A3B8")
        self.btn_cancel_conf.config(state="disabled", bg="#94A3B8")

        # Xác định kho đích theo lựa chọn radio
        active = self.var_active_store.get()
        if active == "A":
            target_root = self.lbl_path_b.cget("text").strip()
            src_label = "A"
        else:
            target_root = self.lbl_path_a.cget("text").strip()
            src_label = "B"

        for target_udid, bk_path in self.pending_restore_map:
            threading.Thread(target=self._restore_worker, args=(target_udid, bk_path, target_root, src_label), daemon=True).start()
        
        self.after(1200, self._hide_confirm_frame)

    # ================== WORKER BACKUP (CƠ CHẾ ĐẶT TÊN 1_iPhone, 2_iPhone...) ==================
    def start_backup_all(self):
        if not self.rows:
            messagebox.showwarning("CẢNH BÁO", "Không có thiết bị kết nối!")
            return
        target_root = self.lbl_path_gen.cget("text").strip()
        os.makedirs(target_root, exist_ok=True)
        self._save_settings_from_ui()

        for udid in list(self.rows.keys()):
            threading.Thread(target=self._backup_worker, args=(udid, target_root), daemon=True).start()

    def _generate_next_backup_foldername(self, target_root, base_device_name="iPhone"):
        existing = os.listdir(target_root)
        
        stt = 1
        for f in existing:
            if os.path.isdir(os.path.join(target_root, f)) and not f.startswith("TMP_"):
                stt += 1

        candidate = f"{stt}_{base_device_name}"
        
        if os.path.exists(os.path.join(target_root, candidate)):
            dup_idx = 1
            while True:
                dup_candidate = f"{candidate}_{dup_idx}"
                if not os.path.exists(os.path.join(target_root, dup_candidate)):
                    candidate = dup_candidate
                    break
                dup_idx += 1
                
        return candidate

    def _backup_worker(self, udid, target_root):
        row = self.rows.get(udid)
        if not SEMAPHORE.acquire(timeout=1):
            if row: row.push_step("Đang chờ slot...")
            SEMAPHORE.acquire()
        try:
            if not pair_validate(udid, log_fn=lambda s, **_: self.log(udid, s)):
                if row: row.push_step("Lỗi Pair")
                return

            if row:
                row.push_step("Đang Sao Lưu")
                row.set_pct(0)

            def on_line(s, is_err=False):
                self.log(udid, s, is_err=is_err)
                m = re.findall(r'(\d{1,3})\s*%', s)
                if m and row: row.set_pct(int(m[-1]))

            rc, _ = run_stream(["idevicebackup2", "-u", udid, "backup", "--full", target_root], on_line=on_line)
            created_default_dir = os.path.join(target_root, udid)

            if rc == 0 and os.path.isdir(created_default_dir) and not verify_backup_layout(created_default_dir):
                info = self._build_info(udid)
                dev_name = info.get('name', 'iPhone')
                
                with self.lock:
                    final_name = self._generate_next_backup_foldername(target_root, dev_name)
                    final_dst = os.path.join(target_root, final_name)
                    os.rename(created_default_dir, final_dst)

                if row:
                    row.set_pct(100)
                    row.push_step("Backup xong")
                self.log(udid, f"Backup hoàn tất ➔ Thư mục: {final_name}")

                if self.var_tik.get():
                    uninstall_app_any(udid, BIDS_TIKTOK, "TikTok", row, lambda s, is_err=False: self.log(udid, s, is_err=is_err))

                if self.var_lite.get():
                    uninstall_app_any(udid, BIDS_TIKTOK_LITE, "TikTok Lite", row, lambda s, is_err=False: self.log(udid, s, is_err=is_err))
            else:
                if row: row.push_step("Lỗi Backup")
                if os.path.exists(created_default_dir):
                    shutil.rmtree(created_default_dir, ignore_errors=True)
        finally:
            SEMAPHORE.release()

    # ================== WORKER RESTORE PRO ==================
    def start_restore_all(self):
        if not self.rows:
            messagebox.showwarning("CẢNH BÁO", "Không có thiết bị kết nối!")
            return
        
        # Xác định kho nguồn / kho đích theo lựa chọn radio
        active = self.var_active_store.get()
        if active == "A":
            source_root = self.lbl_path_a.cget("text").strip()
            target_root = self.lbl_path_b.cget("text").strip()
            src_label = "A"
        else:
            source_root = self.lbl_path_b.cget("text").strip()
            target_root = self.lbl_path_a.cget("text").strip()
            src_label = "B"

        if not os.path.isdir(source_root):
            messagebox.showerror("LỖI", f"Kho {src_label} không tồn tại:\n{source_root}")
            return

        self._save_settings_from_ui()

        all_bks = list_valid_backups(source_root)
        if not all_bks:
            messagebox.showerror("LỖI", f"Kho {src_label} không chứa bản backup hợp lệ nào!")
            return

        connected_devices = []
        for udid, row in self.rows.items():
            if not row.info.get("trusted", True):
                continue
            connected_devices.append({
                "udid": udid,
                "name": row.info.get("name", "iPhone"),
                "ios_str": row.info.get("ios", "?"),
                "ios_t": row.info.get("ios_t", (0, 0, 0))
            })

        if not connected_devices:
            messagebox.showwarning("CẢNH BÁO", "Tất cả các máy kết nối đều NOT TRUST!\nVui lòng bấm 'Tin Cậy' trên điện thoại trước khi khôi phục.")
            return

        self.pending_restore_map = []
        confirm_items = []
        used_backup_paths = set()

        for dev in connected_devices:
            chosen = None
            match_type = ""

            matched_udid_bks = [bk for bk in all_bks if bk["udid"] == dev["udid"] and bk["path"] not in used_backup_paths and bk["ios_t"] <= dev["ios_t"]]
            if matched_udid_bks:
                chosen = matched_udid_bks[0]
                match_type = "UDID Khớp (Ưu tiên 1)"

            if not chosen:
                compatible_bks = [bk for bk in all_bks if bk["path"] not in used_backup_paths and bk["ios_t"] <= dev["ios_t"]]
                if compatible_bks:
                    chosen = compatible_bks[0]
                    match_type = "Tương thích iOS (Ưu tiên 2)"

            if chosen:
                used_backup_paths.add(chosen["path"])
                self.pending_restore_map.append((dev["udid"], chosen["path"]))
                confirm_items.append({
                    "folder_name": chosen["folder_name"],
                    "bk_ios": chosen["ios_str"],
                    "dev_name": dev["name"],
                    "dev_ios": dev["ios_str"],
                    "udid": dev["udid"],
                    "match_type": match_type
                })

        if not self.pending_restore_map:
            messagebox.showerror("LỖI", f"Không ghép được bản backup nào tương thích cho các thiết bị đã Trust!")
            return

        self.log("SYSTEM", f"Restore chuyển kho: {src_label} ➜ {'B' if src_label == 'A' else 'A'} | {len(all_bks)} bản backup | {len(self.pending_restore_map)} máy ghép nối")
        self._show_confirm_frame(confirm_items)

    def _restore_worker(self, target_udid, backup_folder_full, target_after_restore, source_store="A"):
        row = self.rows.get(target_udid)
        if not SEMAPHORE.acquire(timeout=1):
            if row: row.push_step("Đang chờ slot...")
            SEMAPHORE.acquire()
        try:
            if not pair_validate(target_udid, log_fn=lambda s, **_: self.log(target_udid, s)):
                if row: row.push_step("Lỗi Pair")
                self.log(target_udid, "Cần xác nhận 'Tin Cậy' trên màn hình iPhone!", is_err=True)
                return

            if verify_backup_layout(backup_folder_full):
                if row: row.push_step("Backup không hợp lệ")
                self.log(target_udid, "Thư mục Backup bị thiếu file cốt lõi (Manifest.db/plist)!", is_err=True)
                return

            # 1. Patch UDID target vào Info.plist của Backup
            patch_info_plist(backup_folder_full, target_udid, log_fn=lambda s, is_err=False: self.log(target_udid, s, is_err=is_err))

            # 2. KIỂM TRA NÚT CHECKBOX "CAN THIỆP TRỰC TIẾP FILE BACKUP" CÓ BẬT KHÔNG
            if self.var_patch_backup_lang.get():
                locale_setting, lang_setting = _parse_lang_preset(self.var_lang_locale.get())
                self.log(target_udid, f"Bắt đầu can thiệp file Backup sang {lang_setting}/{locale_setting}...")
                patch_backup_language(backup_folder_full, lang_code=lang_setting, locale_code=locale_setting, log_fn=lambda s, is_err=False: self.log(target_udid, s, is_err=is_err))

            base_dir = os.path.dirname(backup_folder_full)
            src_name = os.path.basename(backup_folder_full)
            cmd = ["idevicebackup2", "-u", target_udid, "-s", src_name, "restore", os.path.normpath(base_dir), "--settings", "--remove"]

            if row:
                row.push_step("Restore 0%")
                row.set_pct(0)

            def on_line(s, is_err=False):
                self.log(target_udid, s, is_err=is_err)
                m = re.findall(r'(\d{1,3})\s*%', s)
                if m and row:
                    p_val = int(m[-1])
                    row.set_pct(p_val)
                    row.push_step(f"Restore {p_val}%")

            rc, last_lines = run_stream(cmd, on_line=on_line)
            if rc == 0:
                self.log(target_udid, "Khôi phục dữ liệu Restore hoàn tất thành công.")
                
                # KHÓA TRẠNG THÁI REBOOT TRONG 35 GIÂY (Ngăn không cho Polling báo Not Trust)
                RESTORE_LOCK_CACHE[target_udid] = time.time() + 35.0

                try:
                    os.makedirs(target_after_restore, exist_ok=True)
                    dest = os.path.join(target_after_restore, os.path.basename(backup_folder_full))

                    if os.path.exists(dest):
                        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        dest = os.path.join(target_after_restore, f"{os.path.basename(backup_folder_full)}_{stamp}")

                    shutil.move(backup_folder_full, dest)
                    self.log(target_udid, f"Đã chuyển kho thành công: {source_store} ➔ Kho đối diện:\n{os.path.basename(dest)}")
                    
                    # Cộng bộ đếm restore thành công và tự động cập nhật lại số lượng kho
                    self.after(0, self._count_restore_done)
                    self.log(target_udid, f"✓ Đã chuyển iPhone thứ {self.restore_done_count + 1} qua Kho đối diện thành công!")
                    
                    if row:
                        row.set_pct(100)
                        row.push_step("Hoàn tất Restore 100%")
                except Exception as e:
                    self.log(target_udid, f"Lỗi khi chuyển kho sau restore: {e}", is_err=True)

            else:
                if row: row.push_step(f"Restore lỗi (exit {rc})")
                for line in last_lines[-10:]:
                    self.log(target_udid, line, is_err=True)
        finally:
            SEMAPHORE.release()

if __name__ == "__main__":
    app = App()
    app.mainloop()
