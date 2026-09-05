import os
import sys
import re
import time
import shutil
import json
import plistlib
import threading
import uuid
import tempfile
import base64
import queue
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tiktool_core import (
    OperationRegistry,
    ProcessRunner,
    RebootTracker,
    cleanup_owned_job,
    create_backup_job,
    create_restore_stage,
    load_concurrency,
    normalize_url as core_normalize_url,
    redact_log,
    repair_ipas_path,
    validate_backup,
)

# ================== BẢNG MÀU UI/UX PRO MAX – SOFT MINT DASHBOARD ==================
COLOR_BG_DARK = "#EAF4EE"           # Nền chính Mint-Sage dịu mắt
COLOR_HEADER_BG = "#F0FAF4"         # Header Mint nhạt
COLOR_PANEL_BG = "#F0FAF4"          # Nền Panel Cấu hình

COLOR_WHITE_BORDER = "#A7C4B0"      # Viền phân cách Sage-300
COLOR_BORDER_MD = "#C8DFD0"         # Viền mềm Sage-200

COLOR_DISABLED = "#D5EAD9"          # Nền Tab Không Chọn Sage nhạt
COLOR_TEXT_WHITE = "#0F2318"        # Chữ Xanh Đen Sắc Nét (100% Readability)
COLOR_TEXT_MUTED = "#4A6B54"        # Chữ Xanh Phụ Sage-600

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
APPS_CONFIG_FP = os.path.join(BASE_DIR, "apps_config.json")
LICENSE_FP = os.path.join(BASE_DIR, "license.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
IPAS_DIR = os.path.join(BASE_DIR, "ipas")
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(IPAS_DIR, exist_ok=True)

MAX_CONCURRENCY = load_concurrency(APPS_CONFIG_FP, default=20)
SEMAPHORE = threading.Semaphore(MAX_CONCURRENCY)
ACTIVATE_SEMAPHORE = threading.Semaphore(32)  # Kích hoạt song song toàn bộ thiết bị cùng lúc (tối đa 32 máy)
LANG_SEMAPHORE = threading.Semaphore(32)      # Đổi ngôn ngữ song song toàn bộ thiết bị cùng lúc (tối đa 32 máy)
PAIR_LOCK = threading.Lock()
PROCESS_RUNNER = ProcessRunner()

# CACHE HỆ THỐNG
TRUSTED_CACHE = set()

DEFAULT_SETTINGS = {
    "storeA": os.path.join(BASE_DIR, "backups_A"),
    "storeB": os.path.join(BASE_DIR, "backups_B"),
    "generalBackupDir": os.path.join(BASE_DIR, "backups"),
    "ipasDir": IPAS_DIR,
    "removeTikTok": False,
    "removeTikTokLite": True,
    "deepFlags": True,
    "langLocale": "ja_JP|ja",            # Mặc định là tiếng Nhật
    "setLangAfterActive": True,           # Đặt ngôn ngữ tự động sau khi Batch Activate
    "autoActivateAfterRestore": True,      # Tự động Activate ngay sau khi Restore xong
    "active": "A",                        # Kho nguồn mặc định: "A" (A->B) hoặc "B" (B->A)
    "customWebclipLink": "",                      # Để trống, người dùng tự nhập link
    "dailyRestoreDate": "",
    "dailyRestoreCount": 0
}

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

def run_capture(cmd_list, timeout=120):
    """Chạy lệnh thu thập output ngắn hạn"""
    result = PROCESS_RUNNER.run_capture(cmd_list, timeout=timeout)
    output = result.output
    if result.error:
        output = "\n".join(part for part in (output, result.error) if part)
    return result.returncode, output

# ================== CẤU HÌNH & TIỆN ÍCH WEBCLIP / WEB APP ==================
WEBCLIP_TIKTOK_PNG = os.path.join(BASE_DIR, "tiktok.png")
WEBCLIP_TIKTOK_LITE_PNG = os.path.join(BASE_DIR, "tiktok_lite.png")
WEBCLIP_FUN_PNG = os.path.join(BASE_DIR, "fun.png")
WEBCLIP_2FA_PNG = os.path.join(BASE_DIR, "2FA.png")
WEBCLIP_DEFAULT_PNG = os.path.join(BASE_DIR, "webapp.png")

def _xml_escape(s):
    s = str(s if s else "")
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")

def normalize_url(url):
    return core_normalize_url(url)

def _needs_safari_mode(url):
    u = (url or "").lower()
    return ".fun" in u

def _read_icon_b64(path):
    try:
        if path and os.path.isfile(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        pass
    return ""

def _pick_webclip_icon_path(label, url):
    t = (label or "").lower()
    u = (url or "").lower()
    if "lay2fa.com" in u or "lay2fa" in t or "2fa" in t:
        return WEBCLIP_2FA_PNG
    if "tiktok lite" in t or "id6447160980" in u:
        return WEBCLIP_TIKTOK_LITE_PNG
    if ("tiktok" in t and "lite" not in t) or "id1235601864" in u:
        return WEBCLIP_TIKTOK_PNG
    if "fun" in t or ".fun" in u:
        return WEBCLIP_FUN_PNG
    # Mặc định dùng icon Web App toàn năng siêu đẹp cho mọi link web bất kỳ (ví dụ https://linkm.site/)
    if os.path.isfile(WEBCLIP_DEFAULT_PNG):
        return WEBCLIP_DEFAULT_PNG
    return ""

def _make_webclip_mobileconfig(label, url):
    profile_uuid = str(uuid.uuid4())
    payload_uuid = str(uuid.uuid4())
    safe_label = _xml_escape(label)
    safe_url = _xml_escape(url)
    icon_b64 = _read_icon_b64(_pick_webclip_icon_path(label, url))
    fullscreen = not _needs_safari_mode(url)
    fs_val = "true" if fullscreen else "false"

    icon_block = ""
    if icon_b64:
        icon_block = f"""
            <key>Icon</key>
            <data>{icon_b64}</data>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>FullScreen</key>
            <{fs_val}/>
            <key>IgnoreManifestScope</key>
            <true/>
            <key>IsRemovable</key>
            <true/>
            <key>Label</key>
            <string>{safe_label}</string>
            <key>PayloadDescription</key>
            <string>Web App generated by TikTok Pro</string>
            <key>PayloadDisplayName</key>
            <string>{safe_label}</string>
            <key>PayloadIdentifier</key>
            <string>com.tiktokpro.webclip.{payload_uuid}</string>
            <key>PayloadType</key>
            <string>com.apple.webClip.managed</string>
            <key>PayloadUUID</key>
            <string>{payload_uuid}</string>
            <key>PayloadVersion</key>
            <integer>1</integer>
            <key>Precomposed</key>
            <true/>{icon_block}
            <key>URL</key>
            <string>{safe_url}</string>
        </dict>
    </array>
    <key>PayloadDescription</key>
    <string>Installs a Home Screen Web App</string>
    <key>PayloadDisplayName</key>
    <string>{safe_label}</string>
    <key>PayloadIdentifier</key>
    <string>com.tiktokpro.webclip.profile.{profile_uuid}</string>
    <key>PayloadRemovalDisallowed</key>
    <false/>
    <key>PayloadType</key>
    <string>Configuration</string>
    <key>PayloadUUID</key>
    <string>{profile_uuid}</string>
    <key>PayloadVersion</key>
    <integer>1</integer>
</dict>
</plist>"""
    return xml

# ================== HELPER FUNCTIONS ==================
def check_device_trust(udid):
    """Kiểm tra Trust siêu tốc với timeout tối đa 0.5s"""
    if udid in TRUSTED_CACHE:
        return True

    exe = which_tool("idevicepair")
    if not exe: return False
    try:
        rc, _ = run_capture([exe, "-u", udid, "validate"], timeout=0.5)
        is_ok = rc == 0
        if is_ok:
            TRUSTED_CACHE.add(udid)
        return is_ok
    except Exception:
        return False

def run_stream(cmd_list, on_line=None, timeout=7200):
    result = PROCESS_RUNNER.run_stream(cmd_list, on_line=on_line, timeout=timeout)
    if result.error and on_line:
        on_line(result.error, is_err=True)
    return result.returncode, list(result.lines[-200:])

def get_connected_udids():
    exe = which_tool("idevice_id")
    if not exe: return []
    rc, out = run_capture([exe, "-l"], timeout=2)
    if rc != 0:
        return []
    return [line.strip() for line in out.splitlines() if re.fullmatch(r"[0-9a-fA-F-]{16,}", line.strip())]

def ideviceinfo_k(u, k):
    exe = which_tool("ideviceinfo")
    if not exe: return ""
    for _ in range(2):
        rc, out = run_capture([exe, "-u", u, "--simple", "-k", k], timeout=1.0)
        if rc == 0:
            return out.strip()
        time.sleep(0.1)
    return ""

def pair_validate(udid, log_fn):
    with PAIR_LOCK:
        code, _ = run_stream(["idevicepair", "-u", udid, "validate"], on_line=lambda s, **_: log_fn(s))
        if code != 0:
            code2, _ = run_stream(["idevicepair", "-u", udid, "pair"], on_line=lambda s, **_: log_fn(s))
            return code2 == 0
        return True

# ================== PRO RESTORE CORE HELPERS ==================
def verify_backup_layout(folder):
    ok, errors = validate_backup(folder)
    return [] if ok else errors

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
        subs = [
            d for d in os.listdir(parent_dir)
            if d != ".tiktool_work" and os.path.isdir(os.path.join(parent_dir, d))
        ]
    except Exception: subs = []
    for d in subs:
        full = os.path.join(parent_dir, d)
        if not verify_backup_layout(full):
            b_info = read_backup_info(full)
            if b_info:
                out.append(b_info)
    out.sort(key=lambda bk: (bk["last_dt"] or datetime.min), reverse=False)
    return out

def patch_info_plist(backup_root: str, target_udid: str) -> bool:
    """Cập nhật UDID đích trực tiếp vào Info.plist trong 0.001s, không copy lãng phí thời gian."""
    info_path = os.path.join(backup_root, "Info.plist")
    if not os.path.isfile(info_path):
        return False
    try:
        with open(info_path, "rb") as stream:
            info = plistlib.load(stream)
        if info.get("UniqueDeviceID") != target_udid:
            info["UniqueDeviceID"] = target_udid
            temporary = info_path + ".tmp"
            with open(temporary, "wb") as stream:
                plistlib.dump(info, stream)
            os.replace(temporary, info_path)
        return True
    except Exception:
        return False

def _max_backup_index(root_dir):
    max_n = 0
    try:
        if not os.path.isdir(root_dir):
            return 0
        for name in os.listdir(root_dir):
            full = os.path.join(root_dir, name)
            if os.path.isdir(full):
                m = re.match(r'^(\d+)_', name)
                if m:
                    try:
                        max_n = max(max_n, int(m.group(1)))
                    except Exception:
                        pass
    except Exception:
        pass
    return max_n

def uninstall_app_any(udid, bundle_ids, label_name, card, log_fn):
    if card: card.push_step(f"Gỡ {label_name}...")
    ok = False
    for bid in bundle_ids:
        cmd = ["ideviceinstaller", "-u", udid, "uninstall", bid]
        rc, _ = run_stream(cmd, on_line=lambda s, is_err=False: log_fn(s, is_err=is_err))
        if rc == 0: ok = True; break
    if card: card.push_step(f"Gỡ {label_name} {'thành công' if ok else 'bỏ qua'}")
    return ok

# ================== THANH TIẾN TRÌNH GRADIENT HIỆN ĐẠI ==================
class GradientProgressBar(tk.Canvas):
    def __init__(self, master, height=8, trough_color="#D5E8DD",
                 color_start="#06B6D4", color_end="#2563EB",
                 border_radius=4, **kwargs):
        bg = master.cget("bg") if hasattr(master, "cget") else "#F0FAF4"
        super().__init__(master, height=height, bg=bg, highlightthickness=0, bd=0, **kwargs)
        self.height = height
        self.trough_color = trough_color
        self.color_start = color_start
        self.color_end = color_end
        self.border_radius = border_radius
        self._value = 0.0
        self.bind("<Configure>", lambda e: self._redraw())

    def __setitem__(self, key, value):
        if key == "value":
            self.set_value(value)

    def __getitem__(self, key):
        if key == "value":
            return self._value
        return super().__getitem__(key)

    def set_value(self, val):
        try:
            self._value = max(0.0, min(100.0, float(val)))
        except (ValueError, TypeError):
            self._value = 0.0
        self._redraw()

    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb_to_hex(r, g, b):
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    def _interpolate(self, c1, c2, t):
        r1, g1, b1 = self._hex_to_rgb(c1)
        r2, g2, b2 = self._hex_to_rgb(c2)
        return self._rgb_to_hex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t)

    def _redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.height
        if w <= 1:
            return

        # 1. Rãnh nền (trough)
        self.create_rectangle(0, 0, w, h, fill=self.trough_color, outline=self.trough_color)

        # 2. Dải màu gradient tiến độ mượt mà
        fill_w = int(w * (self._value / 100.0))
        if fill_w > 0:
            step = 2
            for x in range(0, fill_w, step):
                x_end = min(x + step, fill_w)
                t = x / max(1, w - 1)
                color = self._interpolate(self.color_start, self.color_end, t)
                self.create_rectangle(x, 0, x_end, h, fill=color, outline=color)

# ================== CARD THIẾT BỊ LƯỚI 3 COLUMNS ==================
class DeviceCard(tk.Frame):
    def __init__(self, master, udid, info, app_ref=None):
        is_trusted = info.get("trusted", True)
        border_col = "#000000" if is_trusted else "#EF4444"
        
        super().__init__(master, bg=COLOR_PANEL_BG, highlightbackground=border_col, highlightthickness=1, bd=0)
        self.udid = udid
        self.info = info
        self.app_ref = app_ref

        # Dòng 1: Tiêu đề thiết bị (Trái) & Nút thao tác nhanh (Phải)
        top_row = tk.Frame(self, bg=COLOR_PANEL_BG)
        top_row.pack(fill="x", padx=6, pady=(4, 1))

        if not is_trusted:
            title_txt = f"⚠️ {info.get('name', 'iPhone')} • NOT TRUST"
            title_color = "#E11D48"
        else:
            title_txt = f"📱 {info.get('name', 'iPhone')} • iOS {info.get('ios', '?')}"
            title_color = COLOR_TEXT_WHITE

        self.lbl_top = tk.Label(top_row, text=title_txt, font=("Segoe UI", 10, "bold"), fg=title_color, bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_top.pack(side="left")

        # Dòng 2: Model & ECID tinh gọn 1 dòng duy nhất
        ecid_str = info.get('ecid', '—') or '—'
        model_str = info.get('model', 'N/A') or 'N/A'
        lbl_sub = tk.Label(self, text=f"Model: {model_str}  •  ECID: {ecid_str}", font=("Consolas", 9), fg="#0284C7", bg=COLOR_PANEL_BG, anchor="w")
        lbl_sub.pack(fill="x", padx=6, pady=(0, 2))

        # Dòng 3: Trạng thái bước hiện tại (Trái) & % Tiến độ (Phải) - ĐẶT LÊN TRÊN THANH TIẾN TRÌNH
        status_row = tk.Frame(self, bg=COLOR_PANEL_BG)
        status_row.pack(fill="x", padx=6, pady=(1, 3))

        step_txt = "Sẵn sàng" if is_trusted else "⚠️ BẤM TIN CẬY"
        step_fg = "#059669" if is_trusted else "#DC2626"
        step_bg = COLOR_PANEL_BG

        self.lbl_step = tk.Label(status_row, text=step_txt, font=("Segoe UI", 9, "bold"), fg=step_fg, bg=step_bg, anchor="w")
        self.lbl_step.pack(side="left", fill="x", expand=True)

        self.lbl_task = tk.Label(status_row, text="0%", font=("Consolas", 10, "bold"), fg="#0284C7", bg=COLOR_PANEL_BG, anchor="e")
        self.lbl_task.pack(side="right", padx=(4, 0))
        self.lbl_pct = self.lbl_task

        # Dòng 4: Thanh tiến trình Gradient full chiều ngang
        prog_f = tk.Frame(self, bg=COLOR_PANEL_BG)
        prog_f.pack(fill="x", padx=6, pady=(0, 5))

        self.pb = GradientProgressBar(prog_f, height=8, trough_color="#D5E8DD", color_start="#06B6D4", color_end="#2563EB")
        self.pb.pack(fill="x", expand=True)

    def _trigger_single_lang(self):
        if self.app_ref:
            self.app_ref._launch_language(self.udid)

    def _trigger_single_active(self):
        if self.app_ref:
            self.app_ref._launch_activate(self.udid)

    def update_trust_status(self, is_trusted, info):
        self.info = info
        border_col = "#000000" if is_trusted else "#EF4444"
        self.configure(highlightbackground=border_col, highlightthickness=1)

        if not is_trusted:
            title_txt = f"⚠️ {info.get('name', 'iPhone')} • NOT TRUST"
            title_color = "#E11D48"
            step_txt = "⚠️ BẤM TIN CẬY"
            step_fg = "#DC2626"
            step_bg = "#FEF2F2"
        else:
            title_txt = f"📱 {info.get('name', 'iPhone')} • iOS {info.get('ios', '?')}"
            title_color = COLOR_TEXT_WHITE
            step_txt = "Sẵn sàng"
            step_fg = "#059669"
            step_bg = COLOR_PANEL_BG

        self.lbl_top.config(text=title_txt, fg=title_color)
        self.lbl_step.config(text=step_txt, fg=step_fg, bg=step_bg)

    def set_pct(self, p):
        if self.app_ref and not self.app_ref._is_ui_thread():
            self.app_ref._post_ui(self.set_pct, p)
            return
        try:
            if not self.winfo_exists(): return
            val = float(str(p).replace("%", "").strip())
            if hasattr(self, "pb") and self.pb.winfo_exists():
                self.pb["value"] = val
            if hasattr(self, "lbl_task") and self.lbl_task.winfo_exists():
                self.lbl_task.config(text=f"{int(val)}%")
                if val >= 100:
                    self.lbl_task.config(fg="#059669")
                else:
                    self.lbl_task.config(fg="#0284C7")
        except Exception: pass

    def set_task(self, text):
        if self.app_ref and not self.app_ref._is_ui_thread():
            self.app_ref._post_ui(self.set_task, text)
            return
        try:
            if not self.winfo_exists(): return
            m = re.findall(r'(\d{1,3})\s*%', str(text))
            if m:
                self.set_pct(m[-1])
            if hasattr(self, "lbl_step") and self.lbl_step.winfo_exists():
                self.lbl_step.config(text=text)
        except Exception: pass

    def push_step(self, text):
        if self.app_ref and not self.app_ref._is_ui_thread():
            self.app_ref._post_ui(self.push_step, text)
            return
        try:
            if not self.winfo_exists(): return
            if not self.winfo_exists(): return
            m = re.findall(r'(\d{1,3})\s*%', str(text))
            if m:
                self.set_pct(m[-1])
            if hasattr(self, "lbl_step") and self.lbl_step.winfo_exists():
                self.lbl_step.config(text=text)
        except Exception: pass

# ================== MAIN APP (BB MANAGER PRO) ==================
class App(tk.Tk):
    def _bind_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.select_range(0, 'end'))
        def show_menu(e):
            if str(widget.cget("state")) != "disabled":
                widget.focus_set()
                menu.tk_popup(e.x_root, e.y_root)
        widget.bind("<Button-3>", show_menu)

    def __init__(self):
        super().__init__()

        self._ui_thread_id = threading.get_ident()
        self.ui_queue = queue.Queue()
        self.operations = OperationRegistry()
        self.reboot_tracker = RebootTracker()
        self.process_runner = PROCESS_RUNNER
        self.log_file_lock = threading.Lock()
        self.log_file_path = os.path.join(
            LOGS_DIR,
            datetime.now().strftime("tiktool-%Y%m%d-%H%M%S.log"),
        )
        self.configure(bg=COLOR_BG_DARK)

        self.title("TIKTOK PRO - FULL RESTORE & LANGUAGE ENGINE")
        self.geometry("1300x940")
        self.minsize(1180, 820)

        self.rows = {}
        self.lock = threading.Lock()
        self.last_json_mtime = 0
        self.pending_restore_map = []
        self.current_mode = "RESTORE"
        self.licensed = True
        self.restore_done_count = 0  # Bộ đếm restore thành công trong phiên
        self.daily_restore_date = datetime.now().strftime("%Y-%m-%d")
        self.daily_restore_count = 0  # Bộ đếm nick đã restore trong ngày
        self._last_progress_log = {}  # Lưu % log gần nhất cho mỗi UDID để chống nghẽn log
        self._backup_name_counters = {}  # Đếm STT thư mục backup độc lập cho từng kho
        self._poll_lock = threading.Lock()
        self._poll_sync_pending = False
        self._poll_latest = None
        self._grid_cols = 3  # Số cột thẻ thiết bị (tự động co giãn theo kích thước cửa sổ)

        # Variables
        self.var_lang_locale = tk.StringVar(value=DEFAULT_SETTINGS["langLocale"])
        self.var_set_lang_after_active = tk.BooleanVar(value=DEFAULT_SETTINGS["setLangAfterActive"])
        self.var_auto_activate_after_restore = tk.BooleanVar(value=DEFAULT_SETTINGS["autoActivateAfterRestore"])
        self.var_active_store = tk.StringVar(value="A")  # Kho nguồn: A hoặc B
        self.var_custom_webclip_link = tk.StringVar(value=DEFAULT_SETTINGS.get("customWebclipLink", "https://linkm.site/"))

        # Theo dõi các tiến trình đang thực hiện để cảnh báo khi tắt app
        self.active_restores = set()
        self.active_backups = set()
        self.active_activates = set()
        self.protocol("WM_DELETE_WINDOW", self._on_app_close)

        self._setup_style()
        self._setup_ui()
        self._load_initial_settings()  # Load settings.json NGAY LẬP TỨC trước khi timer nào chạy
        self.log("SYSTEM", "Bản quyền TikTok Pro đã được kích hoạt thành công.")
        self.after(50, self._drain_ui_queue)
        self._start_json_sync_loop()
        self._start_polling()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("WinXP.Horizontal.TProgressbar", troughcolor="#E2E8F0", background="#0284C7", borderwidth=0, relief="flat", thickness=6)

    def _setup_ui(self):
        # 1. TOP BRANDING & CONTROLS PANEL (Sleek Compact Surface)
        top_card = tk.Frame(self, bg=COLOR_PANEL_BG, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        top_card.pack(fill="x", side="top", padx=10, pady=(3, 2))

        # --- HÀNG 1: LOGO + NGÔN NGỮ + KÍCH HOẠT THIẾT BỊ ---
        row1 = tk.Frame(top_card, bg=COLOR_PANEL_BG)
        row1.pack(fill="x", padx=8, pady=(3, 2))

        # Logo TikTok Pro
        box_logo = tk.Frame(row1, bg="#EAF4FF", highlightbackground="#3B82F6", highlightthickness=1)
        box_logo.pack(side="left", padx=(0, 8))
        lbl_logo = tk.Label(box_logo, text="TikTok Pro", font=("Segoe UI", 10, "bold"), fg="#1D4ED8", bg="#EAF4FF")
        lbl_logo.pack(padx=7, pady=1)

        # Cấu hình ngôn ngữ
        box_lang = tk.Frame(row1, bg=COLOR_PANEL_BG)
        box_lang.pack(side="left", padx=(0, 8))

        lbl_lang_title = tk.Label(box_lang, text="🌐 Ngôn ngữ:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_WHITE, bg=COLOR_PANEL_BG)
        lbl_lang_title.pack(side="left", padx=(0, 4))

        self.lbl_current_lang = tk.Label(box_lang, text=f"[{self.var_lang_locale.get()}]", font=("Consolas", 8, "bold"), fg="#0284C7", bg=COLOR_BG_DARK, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        self.lbl_current_lang.pack(side="left", padx=(0, 4), ipady=1, ipadx=4)

        btn_change_lang = tk.Button(box_lang, text="⚙️ Popup", font=("Segoe UI", 8, "bold"), bg="#0D9488", activebackground="#14B8A6", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.open_lang_popup)
        btn_change_lang.pack(side="left", padx=(0, 3), ipady=2, ipadx=5)

        btn_only_set_lang = tk.Button(box_lang, text="🌐 Đổi lệnh", font=("Segoe UI", 8, "bold"), bg="#2563EB", activebackground="#3B82F6", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.set_language_locale_all)
        btn_only_set_lang.pack(side="left", ipady=2, ipadx=5)

        # Cụm Kích hoạt thiết bị
        box_act = tk.Frame(row1, bg=COLOR_PANEL_BG)
        box_act.pack(side="left", padx=(8, 0))

        btn_batch_activate = tk.Button(box_act, text="⚡ BATCH ACTIVATE (ALL)", font=("Segoe UI", 9, "bold"), bg="#059669", activebackground="#10B981", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.batch_activate_all)
        btn_batch_activate.pack(side="left", padx=(0, 6), ipady=2, ipadx=7)

        chk_lang_after_active = tk.Checkbutton(
            box_act,
            text="🔑 Đặt ngôn ngữ sau Active",
            font=("Segoe UI", 8, "bold"),
            fg=COLOR_TEXT_WHITE,
            bg=COLOR_PANEL_BG,
            selectcolor=COLOR_BG_DARK,
            activebackground="#FFFFFF",
            activeforeground="#0F172A",
            variable=self.var_set_lang_after_active,
            command=self._save_settings_from_ui
        )
        chk_lang_after_active.pack(side="left")

        # Badge luồng bên phải
        flow_badge = tk.Frame(row1, bg=COLOR_HEADER_BG, highlightbackground=COLOR_BORDER_MD, highlightthickness=1)
        flow_badge.pack(side="right")

        lbl_f1 = tk.Label(flow_badge, text="Activate", font=("Consolas", 8, "bold"), fg="#059669", bg=COLOR_HEADER_BG)
        lbl_f1.pack(side="left", padx=(5, 1), pady=1)
        lbl_farr1 = tk.Label(flow_badge, text="->", font=("Consolas", 8), fg="#94A3B8", bg=COLOR_HEADER_BG)
        lbl_farr1.pack(side="left", pady=1)
        lbl_f2 = tk.Label(flow_badge, text="Skip Setup", font=("Consolas", 8, "bold"), fg="#4F46E5", bg=COLOR_HEADER_BG)
        lbl_f2.pack(side="left", padx=1, pady=1)
        lbl_farr2 = tk.Label(flow_badge, text="->", font=("Consolas", 8), fg="#94A3B8", bg=COLOR_HEADER_BG)
        lbl_farr2.pack(side="left", pady=1)
        lbl_f3 = tk.Label(flow_badge, text="Set Lang", font=("Consolas", 8, "bold"), fg="#0284C7", bg=COLOR_HEADER_BG)
        lbl_f3.pack(side="left", padx=(1, 5), pady=1)

        # --- HÀNG 2: TẠO WEB APP (COMPACT) ---
        row2 = tk.Frame(top_card, bg=COLOR_PANEL_BG)
        row2.pack(fill="x", padx=8, pady=(1, 3))

        lbl_web_title = tk.Label(row2, text="🌐 WEB APP:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_WHITE, bg=COLOR_PANEL_BG)
        lbl_web_title.pack(side="left", padx=(0, 4))

        lbl_input_tag = tk.Label(row2, text="Link:", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        lbl_input_tag.pack(side="left", padx=(0, 3))

        box_link = tk.Frame(row2, bg="#FFFFFF", highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        box_link.pack(side="left", padx=(0, 6))

        self.ent_custom_link = tk.Entry(
            box_link,
            textvariable=self.var_custom_webclip_link,
            font=("Consolas", 9),
            fg="#0F2318",
            bg="#FFFFFF",
            relief="flat",
            bd=0,
            width=28
        )
        self.ent_custom_link.pack(side="left", padx=4, pady=1)

        self._bind_context_menu(self.ent_custom_link)

        btn_create_webapp = tk.Button(
            row2,
            text="🚀 Tạo Web App",
            font=("Segoe UI", 8, "bold"),
            bg="#0284C7",
            activebackground="#0369A1",
            fg="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.create_custom_webclip_all
        )
        btn_create_webapp.pack(side="left", padx=(0, 8), ipady=2, ipadx=7)

        btn_tt_appstore = tk.Button(
            row2,
            text="📱 TikTok",
            font=("Segoe UI", 8, "bold"),
            bg="#1E293B",
            activebackground="#334155",
            fg="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.install_tiktok_webclip_all
        )
        btn_tt_appstore.pack(side="left", padx=(0, 5), ipady=2, ipadx=6)

        btn_ttlite_appstore = tk.Button(
            row2,
            text="⚡ TikTok Lite",
            font=("Segoe UI", 8, "bold"),
            bg="#0D9488",
            activebackground="#14B8A6",
            fg="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.install_tiktok_lite_webclip_all
        )
        btn_ttlite_appstore.pack(side="left", ipady=2, ipadx=6)

        lbl_hint = tk.Label(row2, text="💡 Gửi WebClip profile ra màn hình chính iPhone", font=("Segoe UI", 8, "italic"), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        lbl_hint.pack(side="right", padx=(0, 4))

        # 2. KHUNG CHUYỂN TAB & CẤU HÌNH (RESTORE & BACKUP)
        self.frame_tab_section = tk.Frame(self, bg=COLOR_PANEL_BG, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        self.frame_tab_section.pack(fill="x", padx=10, pady=(1, 2))

        # Thanh nút bấm Tab
        self.frame_tab_control = tk.Frame(self.frame_tab_section, bg=COLOR_BG_DARK)
        self.frame_tab_control.pack(fill="x", padx=3, pady=(2, 1))

        self.btn_tab_restore = tk.Button(self.frame_tab_control, text="[↺] KHÔI PHỤC (RESTORE PRO)", font=("Segoe UI", 9, "bold"), bg="#0284C7", fg="#FFFFFF", relief="flat", bd=0, command=self._switch_to_restore, cursor="hand2")
        self.btn_tab_restore.pack(side="left", padx=(0, 3), ipady=3, expand=True, fill="x")

        self.btn_tab_backup = tk.Button(self.frame_tab_control, text="[💾] SAO LƯU (BACKUP)", font=("Segoe UI", 9, "bold"), bg=COLOR_DISABLED, fg="#475569", relief="flat", bd=0, command=self._switch_to_backup, cursor="hand2")
        self.btn_tab_backup.pack(side="left", ipady=3, expand=True, fill="x")

        # Nội dung panel bên trong
        self.panel_content = tk.Frame(self.frame_tab_section, bg=COLOR_PANEL_BG)
        self.panel_content.pack(fill="x", padx=4, pady=(1, 3))

        self.frame_restore_panel = tk.Frame(self.panel_content, bg=COLOR_PANEL_BG)
        self.frame_backup_panel = tk.Frame(self.panel_content, bg=COLOR_PANEL_BG)

        self._setup_restore_panel()
        self._setup_backup_panel()
        self._switch_to_restore()

        # 3. CONTAINER GIỮA (LƯỚI THIẾT BỊ KẾT NỐI / BẢNG PHÂN BỔ)
        self.middle_container = tk.Frame(self, bg=COLOR_BG_DARK)
        self.middle_container.pack(fill="both", expand=True, padx=10, pady=(1, 2))

        # 3A. KHUNG THIẾT BỊ KẾT NỐI
        self.frame_dev_zone = tk.Frame(self.middle_container, bg=COLOR_BG_DARK)
        self.frame_dev_zone.pack(fill="both", expand=True)

        dev_title_bar = tk.Frame(self.frame_dev_zone, bg=COLOR_PANEL_BG, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        dev_title_bar.pack(fill="x", padx=2, pady=(0, 3))

        # Cụm BỘ ĐẾM KHO ƯU TIÊN NỔI BẬT (TỔNG KHO, ĐÃ CHUYỂN, CÒN LẠI)
        right_stat_bar = tk.Frame(dev_title_bar, bg=COLOR_PANEL_BG)
        right_stat_bar.pack(side="right", padx=4, pady=1)

        # 1. Thẻ TỔNG KHO
        card_tk = tk.Frame(right_stat_bar, bg=COLOR_HEADER_BG, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        card_tk.pack(side="left", padx=3, pady=1)
        lbl_c1_t = tk.Label(card_tk, text="Tổng kho:", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_HEADER_BG)
        lbl_c1_t.pack(side="left", padx=(6, 3), pady=2)
        self.lbl_stat_tong_kho = tk.Label(card_tk, text="0", font=("Segoe UI", 12, "bold"), fg=COLOR_TEXT_WHITE, bg=COLOR_HEADER_BG)
        self.lbl_stat_tong_kho.pack(side="left", padx=(0, 6), pady=2)

        # 2. Thẻ ĐÃ CHUYỂN
        card_dc = tk.Frame(right_stat_bar, bg="#ECFDF5", highlightbackground="#10B981", highlightthickness=1)
        card_dc.pack(side="left", padx=3, pady=1)
        lbl_c2_t = tk.Label(card_dc, text="Đã chuyển:", font=("Segoe UI", 8, "bold"), fg="#059669", bg="#ECFDF5")
        lbl_c2_t.pack(side="left", padx=(6, 3), pady=2)
        self.lbl_stat_da_chuyen = tk.Label(card_dc, text="0", font=("Segoe UI", 12, "bold"), fg="#059669", bg="#ECFDF5")
        self.lbl_stat_da_chuyen.pack(side="left", padx=(0, 6), pady=2)

        # 3. Thẻ CÒN LẠI
        card_cl = tk.Frame(right_stat_bar, bg="#F0F9FF", highlightbackground="#BAE6FD", highlightthickness=1)
        card_cl.pack(side="left", padx=3, pady=1)
        lbl_c3_t = tk.Label(card_cl, text="Còn lại:", font=("Segoe UI", 8, "bold"), fg="#0284C7", bg="#F0F9FF")
        lbl_c3_t.pack(side="left", padx=(6, 3), pady=2)
        self.lbl_stat_con_lai = tk.Label(card_cl, text="0", font=("Segoe UI", 12, "bold"), fg="#0284C7", bg="#F0F9FF")
        self.lbl_stat_con_lai.pack(side="left", padx=(0, 6), pady=2)

        # Nút Reset nhanh cho bộ đếm chuyển
        btn_reset_cnt = tk.Button(right_stat_bar, text="↺", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_MUTED, bg=COLOR_BG_DARK, activebackground="#E2E8F0", activeforeground="#0F172A", relief="flat", bd=0, cursor="hand2", command=self._reset_restore_counter)
        btn_reset_cnt.pack(side="left", padx=(3, 2), ipady=1, ipadx=4)

        # Cụm BỘ ĐẾM NICK ĐÃ RESTORE TRONG NGÀY (Hình minh họa: Tổng: X) - đặt bên lề trái
        daily_stat_bar = tk.Frame(dev_title_bar, bg=COLOR_PANEL_BG)
        daily_stat_bar.pack(side="left", padx=8, pady=1)

        card_daily = tk.Frame(daily_stat_bar, bg="#EEF2FF", highlightbackground="#818CF8", highlightthickness=1)
        card_daily.pack(padx=2, pady=1)

        lbl_daily_t = tk.Label(card_daily, text="Tổng:", font=("Segoe UI", 8, "bold"), fg="#4338CA", bg="#EEF2FF")
        lbl_daily_t.pack(side="left", padx=(8, 3), pady=2)

        self.lbl_stat_daily_restore = tk.Label(card_daily, text=str(self.daily_restore_count), font=("Segoe UI", 12, "bold"), fg="#4F46E5", bg="#EEF2FF")
        self.lbl_stat_daily_restore.pack(side="left", padx=(0, 4), pady=2)

        lbl_daily_sub = tk.Label(card_daily, text="(Hôm nay)", font=("Segoe UI", 8), fg="#6366F1", bg="#EEF2FF")
        lbl_daily_sub.pack(side="left", padx=(0, 6), pady=2)

        btn_reset_daily = tk.Button(
            card_daily,
            text="↺",
            font=("Segoe UI", 8, "bold"),
            fg="#4338CA",
            bg="#E0E7FF",
            activebackground="#C7D2FE",
            activeforeground="#312E81",
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._reset_daily_restore_counter
        )
        btn_reset_daily.pack(side="left", padx=(0, 3), pady=2, ipadx=3)

        self.dev_canvas = tk.Canvas(self.frame_dev_zone, bg=COLOR_BG_DARK, highlightthickness=0)
        self.dev_scrollbar = ttk.Scrollbar(self.frame_dev_zone, orient="vertical", command=self.dev_canvas.yview)
        self.grid_container = tk.Frame(self.dev_canvas, bg=COLOR_BG_DARK)

        self.dev_canvas.bind('<Configure>', self._on_canvas_configure)
        self.grid_container.bind("<Configure>", lambda e: self.dev_canvas.configure(scrollregion=self.dev_canvas.bbox("all")))
        self.dev_canvas_window = self.dev_canvas.create_window((0, 0), window=self.grid_container, anchor="nw")
        self.dev_canvas.configure(yscrollcommand=self.dev_scrollbar.set)

        self.dev_canvas.pack(side="left", fill="both", expand=True, padx=2, pady=(0, 4))
        self.dev_scrollbar.pack(side="right", fill="y", pady=(0, 4))

        # 3B. KHUNG PHÂN BỔ BẢNG BACKUP DẠNG LIST (2-LAYER MATCHING ENGINE)
        self.frame_confirm_zone = tk.Frame(self.middle_container, bg=COLOR_PANEL_BG, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)

        confirm_title_bar = tk.Frame(self.frame_confirm_zone, bg=COLOR_HEADER_BG)
        confirm_title_bar.pack(fill="x", padx=10, pady=6)

        lbl_conf_title = tk.Label(confirm_title_bar, text="📋 PHÂN BỔ THÔNG MINH (2-LAYER MATCHING ENGINE)", font=("Segoe UI", 11, "bold"), fg="#0284C7", bg=COLOR_HEADER_BG)
        lbl_conf_title.pack(side="left")

        self.conf_canvas = tk.Canvas(self.frame_confirm_zone, bg=COLOR_PANEL_BG, highlightthickness=0)
        self.conf_scrollbar = ttk.Scrollbar(self.frame_confirm_zone, orient="vertical", command=self.conf_canvas.yview)
        self.conf_list_container = tk.Frame(self.conf_canvas, bg=COLOR_PANEL_BG)

        self.conf_list_container.bind("<Configure>", lambda e: self.conf_canvas.configure(scrollregion=self.conf_canvas.bbox("all")))
        self.conf_canvas.create_window((0, 0), window=self.conf_list_container, anchor="nw")
        self.conf_canvas.configure(yscrollcommand=self.conf_scrollbar.set)

        self.conf_canvas.pack(side="top", fill="both", expand=True, padx=10, pady=4)
        self.conf_scrollbar.pack(side="right", fill="y", pady=4)

        self.conf_btn_bar = tk.Frame(self.frame_confirm_zone, bg=COLOR_PANEL_BG)
        self.conf_btn_bar.pack(side="bottom", fill="x", padx=10, pady=8)

        self.btn_run_conf = tk.Button(self.conf_btn_bar, text="XÁC NHẬN RESTORE CHUYỂN KHO", font=("Segoe UI", 12, "bold"), bg="#059669", activebackground="#10B981", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self._execute_confirmed_restore)
        self.btn_run_conf.pack(fill="x", pady=(0, 4), ipady=7)

        self.btn_cancel_conf = tk.Button(self.conf_btn_bar, text="HỦY BỎ", font=("Segoe UI", 11, "bold"), bg="#EF4444", activebackground="#DC2626", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self._hide_confirm_frame)
        self.btn_cancel_conf.pack(fill="x", pady=(0, 2), ipady=5)

        # 4. KHU VỰC THỐNG KÊ STATUS DƯỚI CÙNG (DẠNG TEXT GỌN GÀNG)
        frame_trust_status = tk.Frame(self, bg=COLOR_PANEL_BG, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        frame_trust_status.pack(fill="x", side="bottom", padx=10, pady=(0, 2))

        self.lbl_trust_count = tk.Label(frame_trust_status, text="Trust: 0", font=("Segoe UI", 8, "bold"), fg="#059669", bg=COLOR_PANEL_BG)
        self.lbl_trust_count.pack(side="left", padx=(8, 4), pady=2)

        tk.Label(frame_trust_status, text="•", font=("Segoe UI", 8), fg="#94A3B8", bg=COLOR_PANEL_BG).pack(side="left", padx=2)

        self.lbl_dev_count = tk.Label(frame_trust_status, text="Tổng: 0", font=("Segoe UI", 8, "bold"), fg="#475569", bg=COLOR_PANEL_BG)
        self.lbl_dev_count.pack(side="left", padx=4, pady=2)

        tk.Label(frame_trust_status, text="•", font=("Segoe UI", 8), fg="#94A3B8", bg=COLOR_PANEL_BG).pack(side="left", padx=2)

        self.lbl_untrust_count = tk.Label(frame_trust_status, text="Not Trust: 0", font=("Segoe UI", 8, "bold"), fg="#DC2626", bg=COLOR_PANEL_BG)
        self.lbl_untrust_count.pack(side="left", padx=4, pady=2)

        tk.Label(frame_trust_status, text="•", font=("Segoe UI", 8), fg="#94A3B8", bg=COLOR_PANEL_BG).pack(side="left", padx=2)

        self.lbl_restore_done_status = tk.Label(frame_trust_status, text="Restored: 0", font=("Segoe UI", 8, "bold"), fg="#0284C7", bg=COLOR_PANEL_BG)
        self.lbl_restore_done_status.pack(side="left", padx=4, pady=2)

        # 5. NHẬT KÝ HỆ THỐNG (TERMINAL OLED DARK BOX)
        frame_log = tk.Frame(self, bg=COLOR_PANEL_BG, height=140, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        frame_log.pack(fill="x", side="bottom", padx=10, pady=(0, 3))
        frame_log.pack_propagate(False)

        frame_log_head = tk.Frame(frame_log, bg=COLOR_BG_DARK)
        frame_log_head.pack(fill="x", padx=2, pady=(2, 0))

        # Tiêu đề "NHẬT KÝ HỆ THỐNG" căn lề TRÁI (theo mũi tên đỏ ngang)
        lbl_log_head = tk.Label(frame_log_head, text="NHẬT KÝ HỆ THỐNG", font=("Segoe UI", 9, "bold"), fg="#334155", bg=COLOR_BG_DARK, anchor="w")
        lbl_log_head.pack(side="left", padx=8, pady=2)

        # Thông tin thiết bị kết nối dạng text thuần, font đậm, không dùng khung button
        self.lbl_log_dev_info = tk.Label(
            frame_log_head,
            text="Số thiết bị đang kết nối: 0",
            font=("Segoe UI", 10, "bold"),
            fg="#0A2B17",
            bg=COLOR_BG_DARK
        )
        self.lbl_log_dev_info.pack(side="right", padx=10, pady=2)

        self.txt_log = tk.Text(frame_log, font=("Consolas", 10), bg="#0F172A", fg="#F8FAFC", bd=0, highlightthickness=0)
        self.txt_log.pack(fill="both", expand=True, padx=6, pady=4)
        self.txt_log.tag_config("err", foreground="#EF4444")
        self.txt_log.tag_config("alert", foreground="#F59E0B", font=("Consolas", 10, "bold"))  # Vàng cam – cảnh báo rút máy
        self.txt_log.tag_config("ok", foreground="#22C55E", font=("Consolas", 10, "bold"))    # Xanh lá – thành công

    # ================== POPUP ĐỔI NGÔN NGỮ ==================
    def open_lang_popup(self):
        """Hiện Popup chọn ngôn ngữ"""
        pop = tk.Toplevel(self)
        pop.title("Cấu Hình Ngôn Ngữ / Locale")
        pop.geometry("480x420")
        pop.configure(bg=COLOR_PANEL_BG)
        pop.resizable(False, False)
        pop.transient(self)
        pop.grab_set()

        lbl_t = tk.Label(pop, text="CHỌN NGÔN NGỮ VÀ LOCALE", font=("Segoe UI", 12, "bold"), fg=COLOR_TEXT_WHITE, bg=COLOR_PANEL_BG)
        lbl_t.pack(pady=(14, 4))

        lbl_sub = tk.Label(pop, text="Chọn ngôn ngữ có sẵn bên dưới hoặc tự nhập định dạng locale|lang:", font=("Segoe UI", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG, wraplength=440)
        lbl_sub.pack(pady=(0, 10))

        frame_lb = tk.Frame(pop, bg=COLOR_PANEL_BG)
        frame_lb.pack(fill="both", expand=True, padx=20)

        lb = tk.Listbox(frame_lb, bg=COLOR_HEADER_BG, fg=COLOR_TEXT_WHITE, selectbackground="#2563EB", selectforeground="#FFFFFF", font=("Segoe UI", 10), bd=0, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        lb.pack(fill="both", expand=True)

        for name, code in LANG_PRESETS:
            lb.insert("end", f"  {name}  ➜  ({code})")

        frame_custom = tk.Frame(pop, bg=COLOR_PANEL_BG)
        frame_custom.pack(fill="x", padx=20, pady=12)

        lbl_c = tk.Label(frame_custom, text="Tùy chỉnh (locale|lang):", font=("Segoe UI", 10, "bold"), fg=COLOR_TEXT_WHITE, bg=COLOR_PANEL_BG)
        lbl_c.pack(side="left")

        ent_custom = tk.Entry(frame_custom, font=("Consolas", 10), bg=COLOR_HEADER_BG, fg="#0284C7", insertbackground="#0F172A", bd=0, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        ent_custom.pack(side="right", fill="x", expand=True, padx=(8, 0), ipady=3)
        ent_custom.insert(0, self.var_lang_locale.get())
        self._bind_context_menu(ent_custom)

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

        btn_save = tk.Button(pop, text="ÁP DỤNG & LƯU", font=("Segoe UI", 11, "bold"), bg="#10B981", activebackground="#059669", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=apply_lang)
        btn_save.pack(fill="x", padx=20, pady=(0, 16), ipady=7)

    # ================== LOGIC SET LANGUAGE / LOCALE WORKER (LỆNH TRỰC TIẾP CHỦ ĐỘNG) ==================
    def _begin_operation(self, udid, kind):
        if self.operations.begin(udid, kind):
            return True
        current = self.operations.snapshot().get(udid, "tác vụ khác")
        self.log(udid, f"Bỏ qua {kind}: thiết bị đang chạy {current}.", is_err=True)
        return False

    def _require_license(self):
        return True

    def _launch_language(self, udid):
        if not self._require_license():
            return False
        if not self._begin_operation(udid, "language"):
            return False
        preset = self.var_lang_locale.get()
        threading.Thread(
            target=self._set_language_locale_worker,
            args=(udid, preset, True),
            daemon=True,
        ).start()
        return True

    def _launch_activate(self, udid):
        if not self._require_license():
            return False
        if not self._begin_operation(udid, "activate"):
            return False
        set_language = bool(self.var_set_lang_after_active.get())
        preset = self.var_lang_locale.get()
        threading.Thread(
            target=self._batch_activate_worker,
            args=(udid, set_language, preset, True, "activate"),
            daemon=True,
        ).start()
        return True

    def _set_language_locale_worker(self, udid, language_preset=None, operation_reserved=False):
        """Hàm đặt ngôn ngữ chủ động bằng lệnh ios.exe qua USB"""
        task = "Set Language"
        row = self.rows.get(udid)
        if not LANG_SEMAPHORE.acquire(timeout=1):
            if row:
                row.set_task("Đang chờ slot…")
            LANG_SEMAPHORE.acquire()
        try:
            locale, lang = _parse_lang_preset(language_preset or DEFAULT_SETTINGS["langLocale"])
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
            return rc == 0
        finally:
            LANG_SEMAPHORE.release()
            if operation_reserved:
                self.operations.end(udid, "language")

    def set_language_locale_all(self):
        """Kích hoạt đổi ngôn ngữ cho tất cả thiết bị bằng lệnh ios.exe"""
        if not self._require_license():
            return
        ok, msg = _ios_usable()
        if not ok:
            messagebox.showerror("Set Language/Locale", f"Không tìm thấy ios.exe hợp lệ.\n\n{msg}")
            return
        if not self.rows:
            messagebox.showinfo("Set Language/Locale", "Không có thiết bị kết nối.")
            return
                
        preset = self.var_lang_locale.get()
        loc, lng = _parse_lang_preset(preset)
        self.log("SYSTEM", f"Bắt đầu cài đặt ngôn ngữ {lng}/{loc} bằng lệnh cho toàn bộ máy...")
        for udid in list(self.rows.keys()):
            self._launch_language(udid)

    # ================== BATCH ACTIVATE ENGINE ==================
    def batch_activate_all(self):
        """Kích hoạt hàng loạt tất cả thiết bị: Activate → Skip Setup → Set Lang"""
        if not self._require_license():
            return
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
            self._launch_activate(udid)

    def _batch_activate_worker(self, udid, set_language=None, language_preset=None, operation_reserved=False, operation_kind="activate"):
        """Worker xử lý kích hoạt từng thiết bị: 3 giai đoạn Activate → Skip Setup → Set Lang"""
        with self.lock:
            self.active_activates.add(udid)
        task = "Batch Activate"
        row = self.rows.get(udid)

        # Quản lý semaphore kích hoạt song song toàn bộ máy
        if not ACTIVATE_SEMAPHORE.acquire(timeout=1):
            if row:
                row.set_task("Đang chờ slot…")
            ACTIVATE_SEMAPHORE.acquire()

        try:
            # === GIAI ĐOẠN 1: ideviceactivation activate (5% → 40%) ===
            self._update_card_progress(udid, pct=5, task=f"{task} 5%", step="Đang kích hoạt...")

            idevact = which_tool("ideviceactivation")
            cmd = [idevact, "activate", "-u", udid, "-b"]
            self.log(udid, "RUN: " + " ".join(cmd))

            activate_ok = False
            for attempt in range(1, 4):
                rc, out = run_capture(cmd)
                self.log(udid, out or f"exit {rc}", is_err=(rc != 0))

                low = (out or "").lower()
                activate_ok = (rc == 0) or ("already activated" in low) or ("device is already activated" in low)
                if activate_ok:
                    break

                if attempt < 3 and ("lockdownd" in low or "could not connect" in low or "failed to connect" in low):
                    self.log(udid, f"⚠️ Lockdownd đang bận, thử lại sau 5s (lần {attempt}/3)...")
                    self._update_card_progress(udid, step=f"Đợi lockdownd ({attempt}/3)...")
                    time.sleep(5)
                else:
                    break

            if not activate_ok:
                self._update_card_progress(udid, task=f"{task} lỗi", step="Activate thất bại")
                self.log(udid, "Kích hoạt thất bại!", is_err=True)
                return False

            # === GIAI ĐOẠN 2: ios.exe prepare --skip-all (45% → 75%) ===
            self._update_card_progress(udid, pct=45, task=f"{task} 45%", step="Skip Setup Assistant...")

            ios_exe = _fixed_ios_exe()
            cmd2 = [ios_exe, "prepare", "--skip-all", f"--udid={udid}", "--nojson"]
            self.log(udid, "RUN: " + " ".join(cmd2))

            skip_ok = False
            for skip_attempt in range(1, 4):
                _res2 = PROCESS_RUNNER.run_capture(cmd2, timeout=40)
                rc2 = _res2.returncode
                out2 = _res2.output

                # Lọc bỏ warning go-ios tunnel (không ảnh hưởng chức năng qua USB/lockdownd)
                _skip_display_lines = [
                    ln for ln in (out2 or "").splitlines()
                    if "go-ios agent is not running" not in ln
                    and "failed to get tunnel info" not in ln
                    and ln.strip()
                ]
                _skip_display_out = "\n".join(_skip_display_lines)

                if _res2.timed_out:
                    # Timeout thường do go-ios tunnel hoặc lockdownd phản hồi chậm
                    # Lệnh prepare thực tế vẫn có thể đã được iPhone tiếp nhận
                    self.log(udid, f"⚡ Lệnh Skip Setup đã gửi (timeout 40s, lần {skip_attempt}/3 — iPhone có thể đã nhận lệnh).")
                    skip_ok = True  # Coi như thành công, tiếp tục luồng
                    break
                else:
                    if _skip_display_out:
                        low2 = _skip_display_out.lower()
                    else:
                        low2 = ""

                    skip_ok = (rc2 == 0) or ('"ok"' in low2) or (low2.strip() == "ok")

                    if skip_ok:
                        if _skip_display_out:
                            self.log(udid, _skip_display_out)
                        break

                    # Nếu lỗi lockdownd/connection → retry
                    if skip_attempt < 3 and ("lockdownd" in low2 or "could not connect" in low2 or "failed to connect" in low2 or "connection" in low2):
                        self.log(udid, f"⚠️ Skip Setup: lockdownd đang bận, thử lại sau 5s (lần {skip_attempt}/3)...")
                        self._update_card_progress(udid, step=f"Retry Skip Setup ({skip_attempt}/3)...")
                        time.sleep(5)
                    else:
                        # Lỗi khác nhưng không chặn — log cảnh báo và tiếp tục
                        if _skip_display_out:
                            self.log(udid, _skip_display_out, is_err=True)
                        self.log(udid, f"⚠️ Skip Setup trả về rc={rc2}, tiếp tục luồng Batch Activate...")
                        skip_ok = True  # Không chặn cứng; iPhone thường đã nhận lệnh
                        break

            if not skip_ok:
                self._update_card_progress(udid, task=f"{task} cảnh báo", step="Skip Setup lỗi (tiếp tục)")
                self.log(udid, "⚠️ Skip Setup Assistant không phản hồi rõ ràng, tiếp tục Batch Activate...", is_err=False)

            self._update_card_progress(udid, pct=80, task=f"{task} 80%", step="Skip Setup OK")

            # === GIAI ĐOẠN 3: Set Language & Locale (80% → 100%) ===
            if bool(set_language):
                self._update_card_progress(udid, pct=85, task=f"{task} 85%", step="Đang đổi ngôn ngữ...")
                locale, lang = _parse_lang_preset(language_preset or DEFAULT_SETTINGS["langLocale"])

                cmd3 = [ios_exe, "lang", f"--setlocale={locale}", f"--setlang={lang}", f"--udid={udid}", "--nojson"]
                self.log(udid, "RUN: " + " ".join(cmd3))

                # Đổi ngôn ngữ thường mất 3-10s; giới hạn timeout 20s tránh treo luồng
                # Dùng PROCESS_RUNNER trực tiếp để phân biệt timeout vs lỗi thực
                _res3 = PROCESS_RUNNER.run_capture(cmd3, timeout=20)
                rc3 = _res3.returncode
                out3 = _res3.output

                # Lọc bỏ warning go-ios tunnel (không ảnh hưởng chức năng qua USB/lockdownd)
                _display_lines = [
                    ln for ln in (out3 or "").splitlines()
                    if "go-ios agent is not running" not in ln
                    and "failed to get tunnel info" not in ln
                    and ln.strip()
                ]
                _display_out = "\n".join(_display_lines)

                if _res3.timed_out:
                    # SpringBoard reload ngắt kết nối USB tạm thời → timeout là bình thường
                    # iPhone đã nhận lệnh và đổi ngôn ngữ xong trong thực tế
                    self.log(udid, f"⚡ Lệnh đổi ngôn ngữ đã gửi (SpringBoard đang cập nhật, timeout 20s là bình thường).")
                else:
                    if _display_out:
                        self.log(udid, _display_out, is_err=(rc3 != 0))

                    low3 = (_display_out or "").lower()
                    lang_ok = (rc3 == 0) or ('"language"' in low3) or ('"locale"' in low3) or ('"ok"' in low3) or ('supportedlanguages' in low3)
                    if not lang_ok:
                        # Khi iPhone đổi ngôn ngữ, SpringBoard reload làm ngắt kết nối socket tạm thời
                        # khiến lệnh phản hồi trễ; nhưng thực tế iPhone đã nhận lệnh và đổi xong
                        self.log(udid, f"⚡ Lệnh đổi ngôn ngữ đã gửi (SpringBoard đang cập nhật: {_display_out or rc3}).")

            # === HOÀN TẤT ===
            self._update_card_progress(udid, pct=100, task=f"{task} thành công", step="Đã kích hoạt ✓")
            self.log(udid, "Batch Activate hoàn tất thành công.")
            return True

        finally:
            with self.lock:
                self.active_activates.discard(udid)
            ACTIVATE_SEMAPHORE.release()
            if operation_reserved:
                self.operations.end(udid, operation_kind)

    # ================== TIỆN ÍCH WEB APP (WEBCLIP PROFILE TO IPHONE) ==================
    def _push_webclip_to_device(self, udid, profile_path, label, url, max_retries=2):
        row = self.rows.get(udid)
        ios_exe = _fixed_ios_exe()
        if not ios_exe:
            self.log(udid, "Không tìm thấy ios.exe cạnh tool.", is_err=True)
            if row: row.set_task("Thiếu ios.exe")
            return False

        attempts = max(1, int(max_retries) + 1)
        for attempt in range(1, attempts + 1):
            cmd = [ios_exe, "profile", "add", profile_path, f"--udid={udid}", "--nojson"]
            self.log(udid, f"Đẩy Web App '{label}' -> {url} (lần {attempt}/{attempts})")
            self.log(udid, "RUN: " + " ".join(cmd))
            if row:
                row.set_task(f"Web App {attempt}/{attempts}")
                row.push_step(f"Đẩy Web App {attempt}/{attempts}")
            rc, out = run_capture(cmd)
            out = (out or "").strip()
            low = out.lower()
            ok = (rc == 0) or ("profile added" in low) or ("install profile" in low) or ("success" in low) or ('"ok"' in low) or (low == "ok")
            if out:
                self.log(udid, out, is_err=(not ok))
            if ok:
                self.log(udid, f"Gửi WebClip thành công. Hãy bấm Install trên iPhone để thêm '{label}' ra màn hình.")
                if row:
                    row.set_task("Web App đã gửi")
                    row.set_pct(100)
                    row.push_step("Chờ bấm Install trên iPhone")
                return True
            self.log(udid, f"Gửi WebClip thất bại (exit {rc}).", is_err=True)
            if attempt < attempts:
                self.log(udid, "Thử gửi lại WebClip sau 1 giây...")
                time.sleep(1)
        if row:
            row.set_task("Web App lỗi")
            row.set_pct(0)
        return False

    def _push_webclip_all(self, label, url):
        ok, msg = _ios_usable()
        if not ok:
            self._post_ui(messagebox.showerror, "Web App", f"Không tìm thấy ios.exe hợp lệ.\n\n{msg}")
            return False
        if not self.rows:
            self._post_ui(messagebox.showinfo, "Web App", "Không có thiết bị kết nối.")
            return False

        url = normalize_url(url)
        if not url:
            self._post_ui(messagebox.showwarning, "Thiếu link", "Vui lòng nhập link web app.")
            return False

        label = (label or "Web App").strip() or "Web App"
        profile_xml = _make_webclip_mobileconfig(label, url)
        profile_path = os.path.join(tempfile.gettempdir(), f"webclip_{uuid.uuid4()}.mobileconfig")

        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                f.write(profile_xml)

            total = 0
            success = 0
            for udid in list(self.rows.keys()):
                if hasattr(self, "operations") and not self._begin_operation(udid, "webclip"):
                    continue
                total += 1
                try:
                    if self._push_webclip_to_device(udid, profile_path, label, url, max_retries=2):
                        success += 1
                finally:
                    if hasattr(self, "operations"):
                        self.operations.end(udid, "webclip")

            self.log(None, f"Web App '{label}': thành công {success}/{total} thiết bị.", is_err=(success != total))
            if total == 0:
                self._post_ui(messagebox.showinfo, "Web App", "Không có thiết bị rảnh để nhận Web App.")
            elif success == total:
                self._post_ui(
                    messagebox.showinfo,
                    "Web App",
                    f"Đã gửi '{label}' tới {success}/{total} thiết bị.\n\nBấm Install trên từng iPhone để hiện icon ngoài màn hình.",
                )
            else:
                self._post_ui(
                    messagebox.showwarning,
                    "Web App",
                    f"Đã gửi thành công {success}/{total} thiết bị.\nKiểm tra log để xem máy nào lỗi.",
                )
            return total > 0 and success == total
        finally:
            try:
                if os.path.exists(profile_path):
                    os.remove(profile_path)
            except Exception:
                pass

    def create_custom_webclip_all(self):
        if not self._require_license():
            return
        raw_url = self.var_custom_webclip_link.get()
        url = normalize_url(raw_url)
        if not url:
            messagebox.showwarning("Thiếu link", "Vui lòng nhập link web app.")
            return

        self._save_settings_from_ui()
        self.log(None, f"Custom Web App URL: nhập='{raw_url}' -> chuẩn hoá='{url}'")

        # Tự sinh label từ tên miền: e.g. "linkm.site" -> "LINKM.SITE"
        host = url.split("://", 1)[-1].split("/", 1)[0].strip()
        label = host.upper() if host else "Custom Web App"

        threading.Thread(target=self._push_webclip_all, args=(label, url), daemon=True).start()

    def install_tiktok_webclip_all(self):
        if not self._require_license():
            return
        threading.Thread(
            target=self._push_webclip_all,
            args=("TikTok - AppStore", "https://apps.apple.com/jp/app/tiktok-%E3%83%86%E3%82%A3%E3%83%83%E3%82%AF%E3%83%88%E3%83%83%E3%82%AF/id1235601864"),
            daemon=True
        ).start()

    def install_tiktok_lite_webclip_all(self):
        if not self._require_license():
            return
        threading.Thread(
            target=self._push_webclip_all,
            args=("TikTok Lite - AppStore", "https://apps.apple.com/jp/app/tiktok-lite/id6447160980"),
            daemon=True
        ).start()

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
                # KHO A ➜ KHO B: XANH LÁ / EMERALD (#059669)
                self.lbl_title_a.config(text=f"MỤC NHẬP (KHO A: {count_a} iPhone)", fg="#059669")
                self.lbl_title_b.config(text=f"MỤC XUẤT (KHO B: {count_b} iPhone)", fg="#0284C7")
                self.btn_label_a.config(bg="#10B981")
                self.btn_label_b.config(bg="#0284C7")
                self.box_a.config(highlightbackground="#10B981", highlightthickness=2)
                self.box_b.config(highlightbackground="#BAE6FD", highlightthickness=1)
                self.lbl_flow_direction.config(text="A ➜ B", fg="#059669")
                self.btn_start_restore.config(
                    text=f"⚡ BẮT ĐẦU RESTORE PRO (A ➜ B • {count_a} iPhone)", 
                    bg="#059669",
                    activebackground="#10B981"
                )
                self.lbl_store_info.config(text=f"📱 Nguồn Kho A ({count_a} iPhone) ➜ Đích Kho B ({count_b} iPhone)", fg="#059669")
                if hasattr(self, "chk_auto_act"):
                    self.chk_auto_act.config(fg="#059669", activeforeground="#059669")
                if hasattr(self, "box_restore_pill") and hasattr(self, "lbl_restore_done"):
                    self.box_restore_pill.config(bg="#ECFDF5", highlightbackground="#10B981")
                    self.lbl_restore_done.config(fg="#059669", bg="#ECFDF5")
            else:
                # KHO B ➜ KHO A: XANH DƯƠNG / OCEAN BLUE (#0284C7)
                self.lbl_title_a.config(text=f"MỤC XUẤT (KHO A: {count_a} iPhone)", fg="#059669")
                self.lbl_title_b.config(text=f"MỤC NHẬP (KHO B: {count_b} iPhone)", fg="#0284C7")
                self.btn_label_a.config(bg="#10B981")
                self.btn_label_b.config(bg="#0284C7")
                self.box_a.config(highlightbackground="#A7F3D0", highlightthickness=1)
                self.box_b.config(highlightbackground="#0284C7", highlightthickness=2)
                self.lbl_flow_direction.config(text="B ➜ A", fg="#0284C7")
                self.btn_start_restore.config(
                    text=f"⚡ BẮT ĐẦU RESTORE PRO (B ➜ A • {count_b} iPhone)",
                    bg="#0284C7",
                    activebackground="#0369A1"
                )
                self.lbl_store_info.config(text=f"📱 Nguồn Kho B ({count_b} iPhone) ➜ Đích Kho A ({count_a} iPhone)", fg="#0284C7")
                if hasattr(self, "chk_auto_act"):
                    self.chk_auto_act.config(fg="#0284C7", activeforeground="#0284C7")
                if hasattr(self, "box_restore_pill") and hasattr(self, "lbl_restore_done"):
                    self.box_restore_pill.config(bg="#EAF4FF", highlightbackground="#0284C7")
                    self.lbl_restore_done.config(fg="#0284C7", bg="#EAF4FF")

        self._save_settings_from_ui()

    def _count_backups_in_dir(self, dir_path):
        """Đếm số thư mục backup hợp lệ trong một thư mục"""
        if not os.path.isdir(dir_path):
            return 0
        backups = list_valid_backups(dir_path)
        return len(backups)

    def _count_restore_done(self):
        self.restore_done_count += 1

        # Cập nhật số nick restore trong ngày
        today = datetime.now().strftime("%Y-%m-%d")
        if self.daily_restore_date != today:
            self.daily_restore_date = today
            self.daily_restore_count = 0
        self.daily_restore_count += 1
        self._save_daily_restore_stats()

        self._update_restore_counter()
        self._on_store_switch()

    def _reset_restore_counter(self):
        self.restore_done_count = 0
        self._update_restore_counter()
        self._on_store_switch()

    def _reset_daily_restore_counter(self):
        self.daily_restore_count = 0
        self.daily_restore_date = datetime.now().strftime("%Y-%m-%d")
        self._save_daily_restore_stats()
        if hasattr(self, "lbl_stat_daily_restore"):
            self.lbl_stat_daily_restore.config(text="0")
        self.log("SYSTEM", "Đã đặt lại bộ đếm Restore trong ngày về 0.")

    def _save_daily_restore_stats(self):
        try:
            data = {}
            if os.path.exists(SETTINGS_FP):
                with open(SETTINGS_FP, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["dailyRestoreDate"] = self.daily_restore_date
            data["dailyRestoreCount"] = self.daily_restore_count
            with open(SETTINGS_FP, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.last_json_mtime = os.path.getmtime(SETTINGS_FP)
        except Exception as e:
            pass

    def _update_restore_counter(self):
        if hasattr(self, "lbl_restore_done"):
            self.lbl_restore_done.config(text=f"Đã Restore: {self.restore_done_count}")
        if hasattr(self, "lbl_restore_done_status"):
            self.lbl_restore_done_status.config(text=f"Restored: {self.restore_done_count}")
        if hasattr(self, "lbl_stat_da_chuyen"):
            self.lbl_stat_da_chuyen.config(text=str(self.restore_done_count))
        if hasattr(self, "lbl_stat_daily_restore"):
            self.lbl_stat_daily_restore.config(text=str(self.daily_restore_count))

    def _on_canvas_configure(self, event):
        self.dev_canvas.itemconfig(self.dev_canvas_window, width=event.width)
        new_cols = self._calculate_columns(event.width)
        if new_cols != getattr(self, "_grid_cols", 3):
            self._relayout_cards(cols=new_cols)

    # ---------------- BẢNG CẤU HÌNH RESTORE ----------------
    def _setup_restore_panel(self):
        f = self.frame_restore_panel
        f.columnconfigure((0, 1), weight=1)

        # === HÀNG 0: CHỌN KHO NGUỒN (RADIO A / B) + THÔNG TIN SỐ LƯỢNG ===
        store_select_bar = tk.Frame(f, bg=COLOR_BG_DARK, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1)
        store_select_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=2, pady=(1, 2))

        lbl_store_title = tk.Label(store_select_bar, text="📦 CHỌN KHO NGUỒN:", font=("Segoe UI", 9, "bold"), fg=COLOR_TEXT_WHITE, bg=COLOR_BG_DARK)
        lbl_store_title.pack(side="left", padx=(6, 3), pady=2)

        rb_a = tk.Radiobutton(store_select_bar, text="Kho A ➜ B", font=("Segoe UI", 8, "bold"), fg="#059669", bg=COLOR_BG_DARK, selectcolor="#FFFFFF", activebackground="#F1F5F9", activeforeground="#059669", variable=self.var_active_store, value="A", command=self._on_store_switch)
        rb_a.pack(side="left", padx=4, pady=2)

        rb_b = tk.Radiobutton(store_select_bar, text="Kho B ➜ A", font=("Segoe UI", 8, "bold"), fg="#0284C7", bg=COLOR_BG_DARK, selectcolor="#FFFFFF", activebackground="#F1F5F9", activeforeground="#0284C7", variable=self.var_active_store, value="B", command=self._on_store_switch)
        rb_b.pack(side="left", padx=4, pady=2)

        # Thông tin số lượng backup trong kho nguồn
        self.lbl_store_info = tk.Label(store_select_bar, text="📱 Kho nguồn: đang quét...", font=("Segoe UI", 8, "bold"), fg="#0284C7", bg=COLOR_BG_DARK)
        self.lbl_store_info.pack(side="left", padx=8, pady=2)

        # Hiện tại chiều chuyển
        self.lbl_flow_direction = tk.Label(store_select_bar, text="A ➜ B", font=("Segoe UI", 9, "bold"), fg="#059669", bg=COLOR_BG_DARK)
        self.lbl_flow_direction.pack(side="right", padx=8, pady=2)

        # === HÀNG 1: KHO A & KHO B (MỤC NHẬP / MỤC XUẤT) ===
        # Ô Kho A
        col_a = tk.Frame(f, bg=COLOR_PANEL_BG)
        col_a.grid(row=1, column=0, sticky="ew", padx=2, pady=1)
        col_a.columnconfigure(0, weight=1)

        self.lbl_title_a = tk.Label(col_a, text="MỤC NHẬP (KHO A)", font=("Segoe UI", 8, "bold"), fg="#059669", bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_title_a.pack(fill="x", pady=(0, 1))

        self.box_a = tk.Frame(col_a, bg=COLOR_HEADER_BG, highlightbackground="#10B981", highlightthickness=1, bd=0)
        self.box_a.pack(fill="x")
        self.box_a.columnconfigure(1, weight=1)

        self.btn_label_a = tk.Button(self.box_a, text="📂 Chọn", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg="#10B981", activebackground="#059669", activeforeground="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=lambda: self._browse("STORE_A"))
        self.btn_label_a.grid(row=0, column=0, padx=4, pady=2)

        self.lbl_path_a = tk.Label(self.box_a, text=DEFAULT_SETTINGS["storeA"], font=("Consolas", 8), fg=COLOR_TEXT_WHITE, bg=COLOR_HEADER_BG, anchor="w", cursor="hand2")
        self.lbl_path_a.grid(row=0, column=1, sticky="ew", padx=3, pady=2)
        self.lbl_path_a.bind("<Button-1>", lambda e: self._browse("STORE_A"))

        # Ô Kho B
        col_b = tk.Frame(f, bg=COLOR_PANEL_BG)
        col_b.grid(row=1, column=1, sticky="ew", padx=2, pady=1)
        col_b.columnconfigure(0, weight=1)

        self.lbl_title_b = tk.Label(col_b, text="MỤC XUẤT (KHO B)", font=("Segoe UI", 8, "bold"), fg="#0284C7", bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_title_b.pack(fill="x", pady=(0, 1))

        self.box_b = tk.Frame(col_b, bg=COLOR_HEADER_BG, highlightbackground="#BAE6FD", highlightthickness=1, bd=0)
        self.box_b.pack(fill="x")
        self.box_b.columnconfigure(1, weight=1)

        self.btn_label_b = tk.Button(self.box_b, text="📂 Chọn", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg="#0284C7", activebackground="#0369A1", activeforeground="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=lambda: self._browse("STORE_B"))
        self.btn_label_b.grid(row=0, column=0, padx=4, pady=2)

        self.lbl_path_b = tk.Label(self.box_b, text=DEFAULT_SETTINGS["storeB"], font=("Consolas", 8), fg=COLOR_TEXT_WHITE, bg=COLOR_HEADER_BG, anchor="w", cursor="hand2")
        self.lbl_path_b.grid(row=0, column=1, sticky="ew", padx=3, pady=2)
        self.lbl_path_b.bind("<Button-1>", lambda e: self._browse("STORE_B"))

        # CHECKBOX AUTO ACTIVATE
        box_opt = tk.Frame(f, bg=COLOR_PANEL_BG)
        box_opt.grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=(1, 2))

        self.chk_auto_act = tk.Checkbutton(
            box_opt,
            text="⚡ Tự Activate sau Restore",
            font=("Segoe UI", 8, "bold"),
            fg="#059669",
            bg=COLOR_PANEL_BG,
            selectcolor=COLOR_BG_DARK,
            activebackground="#FFFFFF",
            activeforeground="#059669",
            variable=self.var_auto_activate_after_restore,
            command=self._save_settings_from_ui
        )
        self.chk_auto_act.pack(side="left", padx=(2, 0))

        # BỘ ĐẾM RESTORE THÀNH CÔNG
        self.box_restore_pill = tk.Frame(box_opt, bg="#ECFDF5", highlightbackground="#10B981", highlightthickness=1)
        self.box_restore_pill.pack(side="right", padx=2)

        self.lbl_restore_done = tk.Label(self.box_restore_pill, text="Đã Restore: 0", font=("Segoe UI", 8, "bold"), fg="#059669", bg="#ECFDF5")
        self.lbl_restore_done.pack(padx=6, pady=1)

        self.btn_start_restore = tk.Button(f, text="⚡ BẮT ĐẦU RESTORE PRO", font=("Segoe UI", 10, "bold"), bg="#059669", activebackground="#10B981", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.start_restore_all)
        self.btn_start_restore.grid(row=3, column=0, columnspan=2, sticky="ew", padx=2, pady=(1, 2), ipady=4)

        # Quét số lượng backup ban đầu
        self.after(500, self._on_store_switch)

    # ---------------- BẢNG CẤU HÌNH BACKUP ----------------
    def _setup_backup_panel(self):
        f = self.frame_backup_panel
        f.columnconfigure(0, weight=1)

        box_top = tk.Frame(f, bg=COLOR_PANEL_BG)
        box_top.pack(fill="x", padx=2, pady=1)
        box_top.columnconfigure(0, weight=1)

        col_bk = tk.Frame(box_top, bg=COLOR_PANEL_BG)
        col_bk.grid(row=0, column=0, sticky="ew")

        lbl_title_bk = tk.Label(col_bk, text="KHO BACKUP", font=("Segoe UI", 8, "bold"), fg="#0284C7", bg=COLOR_PANEL_BG, anchor="w")
        lbl_title_bk.pack(fill="x", pady=(0, 1))

        box_bk = tk.Frame(col_bk, bg=COLOR_HEADER_BG, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1, bd=0)
        box_bk.pack(fill="x")
        box_bk.columnconfigure(1, weight=1)

        btn_label_gen = tk.Button(box_bk, text="📂 Chọn", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg="#2563EB", activebackground="#1D4ED8", activeforeground="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=lambda: self._browse("GEN_DIR"))
        btn_label_gen.grid(row=0, column=0, padx=4, pady=2)

        self.lbl_path_gen = tk.Label(box_bk, text=DEFAULT_SETTINGS["generalBackupDir"], font=("Consolas", 8), fg=COLOR_TEXT_WHITE, bg=COLOR_HEADER_BG, anchor="w", cursor="hand2")
        self.lbl_path_gen.grid(row=0, column=1, sticky="ew", padx=3, pady=2)
        self.lbl_path_gen.bind("<Button-1>", lambda e: self._browse("GEN_DIR"))

        box_chk = tk.Frame(box_top, bg=COLOR_PANEL_BG)
        box_chk.grid(row=0, column=1, sticky="e", padx=(8, 0), pady=(4, 0))

        self.var_tik = tk.BooleanVar(value=False)
        tk.Checkbutton(box_chk, text="Gỡ TikTok", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_WHITE, bg=COLOR_PANEL_BG, selectcolor=COLOR_BG_DARK, activebackground="#FFFFFF", activeforeground="#0F172A", variable=self.var_tik, command=self._save_settings_from_ui).pack(side="left", padx=4)

        self.var_lite = tk.BooleanVar(value=True)
        tk.Checkbutton(box_chk, text="Gỡ TikTok Lite", font=("Segoe UI", 8, "bold"), fg=COLOR_TEXT_WHITE, bg=COLOR_PANEL_BG, selectcolor=COLOR_BG_DARK, activebackground="#FFFFFF", activeforeground="#0F172A", variable=self.var_lite, command=self._save_settings_from_ui).pack(side="left", padx=4)

        self.btn_start_backup = tk.Button(f, text="💾 BẮT ĐẦU SAO LƯU (BACKUP ALL)", font=("Segoe UI", 10, "bold"), bg="#2563EB", activebackground="#1D4ED8", fg="#FFFFFF", relief="flat", bd=0, cursor="hand2", command=self.start_backup_all)
        self.btn_start_backup.pack(fill="x", padx=2, pady=(1, 2), ipady=4)

    # ---------------- TAB SWITCH ----------------
    def _switch_to_restore(self):
        self.current_mode = "RESTORE"
        self.btn_tab_restore.config(bg="#0284C7", fg="#FFFFFF")
        self.btn_tab_backup.config(bg=COLOR_DISABLED, fg="#475569")

        self.frame_backup_panel.pack_forget()
        self.frame_restore_panel.pack(fill="x")

    def _switch_to_backup(self):
        self.current_mode = "BACKUP"
        self.btn_tab_backup.config(bg="#0284C7", fg="#FFFFFF")
        self.btn_tab_restore.config(bg=COLOR_DISABLED, fg="#475569")

        self.frame_restore_panel.pack_forget()
        self.frame_backup_panel.pack(fill="x")

    # ---------------- LOAD SETTINGS KHỞI ĐỘNG ----------------
    def _load_initial_settings(self):
        """Load settings.json ĐỒNG BỘ ngay khi khởi động để label paths hiển thị đúng
        trước khi bất kỳ timer nào (500ms) chạy và ghi đè settings."""
        try:
            if os.path.exists(SETTINGS_FP):
                with open(SETTINGS_FP, "r", encoding="utf-8") as f:
                    data = json.load(f)
                repaired = repair_ipas_path(data, BASE_DIR)
                unsafe_key = "patchBackupLang" + "BeforeRestore"
                removed_unsafe_setting = data.pop(unsafe_key, None) is not None
                if repaired or removed_unsafe_setting:
                    with open(SETTINGS_FP, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                self.last_json_mtime = os.path.getmtime(SETTINGS_FP)
                self._apply_settings_to_ui(data)
                self.log("SYSTEM", f"Đã load cấu hình từ settings.json thành công.")
        except Exception as e:
            self.log("SYSTEM", f"Không thể load settings.json: {e}", is_err=True)

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
        if "setLangAfterActive" in data: self.var_set_lang_after_active.set(bool(data["setLangAfterActive"]))
        if "autoActivateAfterRestore" in data: self.var_auto_activate_after_restore.set(bool(data["autoActivateAfterRestore"]))
        if "active" in data and data["active"] in ("A", "B"): self.var_active_store.set(data["active"])
        if "customWebclipLink" in data and data["customWebclipLink"]:
            # Only set on initial load, not during periodic sync (to avoid overwriting user edits)
            if not getattr(self, '_webclip_link_loaded', False):
                self.var_custom_webclip_link.set(data["customWebclipLink"])
                self._webclip_link_loaded = True
        if "langLocale" in data and data["langLocale"]:
            self.var_lang_locale.set(data["langLocale"])
            loc, lng = _parse_lang_preset(data["langLocale"])
            self.lbl_current_lang.config(text=f"[{data['langLocale']}]")

        today = datetime.now().strftime("%Y-%m-%d")
        saved_date = data.get("dailyRestoreDate", "")
        if saved_date == today:
            saved_count = int(data.get("dailyRestoreCount", 0))
            self.daily_restore_count = max(saved_count, self.restore_done_count)
            self.daily_restore_date = today
        else:
            if self.restore_done_count > 0:
                self.daily_restore_count = self.restore_done_count
                self.daily_restore_date = today
            elif not saved_date:
                self.daily_restore_date = today
        if hasattr(self, "lbl_stat_daily_restore"):
            self.lbl_stat_daily_restore.config(text=str(self.daily_restore_count))

        self._on_store_switch()

    def _save_settings_from_ui(self):
        try:
            data = DEFAULT_SETTINGS.copy()
            if os.path.exists(SETTINGS_FP):
                with open(SETTINGS_FP, "r", encoding="utf-8") as f: data.update(json.load(f))
            data.pop("patchBackupLang" + "BeforeRestore", None)
            repair_ipas_path(data, BASE_DIR)

            data["storeA"] = self.lbl_path_a.cget("text").strip()
            data["storeB"] = self.lbl_path_b.cget("text").strip()
            data["generalBackupDir"] = self.lbl_path_gen.cget("text").strip()
            data["removeTikTok"] = self.var_tik.get()
            data["removeTikTokLite"] = self.var_lite.get()
            data["langLocale"] = self.var_lang_locale.get()
            data["setLangAfterActive"] = self.var_set_lang_after_active.get()
            data["autoActivateAfterRestore"] = self.var_auto_activate_after_restore.get()
            data["active"] = self.var_active_store.get()
            data["customWebclipLink"] = self.var_custom_webclip_link.get().strip()
            data["dailyRestoreDate"] = self.daily_restore_date
            data["dailyRestoreCount"] = self.daily_restore_count

            with open(SETTINGS_FP, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.last_json_mtime = os.path.getmtime(SETTINGS_FP)
        except Exception as e:
            self.log("SYSTEM", f"Lỗi _save_settings_from_ui: {e}", is_err=True)

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

    def _is_ui_thread(self):
        return threading.get_ident() == self._ui_thread_id

    def _post_ui(self, callback, *args, **kwargs):
        self.ui_queue.put((callback, args, kwargs))

    def _drain_ui_queue(self):
        try:
            for _ in range(200):
                try:
                    callback, args, kwargs = self.ui_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    self._append_log_file(f"[{_ts()}] SYSTEM: Lỗi UI queue: {e}\n")
        finally:
            try:
                self.after(50, self._drain_ui_queue)
            except Exception:
                pass

    def _queue_poll_sync(self, udids, trust_results, info_results):
        with self._poll_lock:
            self._poll_latest = (udids, trust_results, info_results)
            if self._poll_sync_pending:
                return
            self._poll_sync_pending = True
        self._post_ui(self._apply_latest_poll)

    def _apply_latest_poll(self):
        with self._poll_lock:
            payload = self._poll_latest
            self._poll_latest = None
            self._poll_sync_pending = False
        if payload is not None:
            self._sync_cards(*payload)

    def _append_log_file(self, message):
        try:
            with self.log_file_lock:
                with open(self.log_file_path, "a", encoding="utf-8", newline="") as stream:
                    stream.write(redact_log(message))
        except Exception:
            pass

    def log(self, udid, line, is_err=False, is_warn=False, is_ok=False):
        prefix = (udid[:6] + "...") if udid else "SYSTEM"
        msg = f"[{_ts()}] {prefix}: {line}\n"
        self._append_log_file(msg)
        App._post_ui(self, self._write_log, msg, is_err, is_warn, is_ok)

    def _write_log(self, msg, is_err, is_warn=False, is_ok=False):
        try:
            if is_err: self.txt_log.insert("end", msg, "err")
            elif is_warn: self.txt_log.insert("end", msg, "alert")
            elif is_ok: self.txt_log.insert("end", msg, "ok")
            else: self.txt_log.insert("end", msg)
            self.txt_log.see("end")
        except Exception: pass

    def _parse_any_percent(self, s):
        try:
            m = re.findall(r'(\d{1,3})\s*%', str(s or ''))
            if m:
                val = int(m[-1])
                if 0 <= val <= 100:
                    return val
        except Exception:
            pass
        return None

    def _should_log_stream_line(self, udid, line):
        s = str(line or '').strip()
        if not s:
            return False
        low = s.lower()
        important_words = (
            'error', 'fail', 'failed', 'thất bại', 'lỗi',
            'complete', 'completed', 'success', 'successful',
            'restore successful', 'mberrordomain', 'run:',
            'warning', 'disconnect', 'timeout'
        )
        if any(w in low for w in important_words):
            return True
        pct = self._parse_any_percent(s)
        if pct is None:
            return False
        key = udid or 'GENERAL'
        last = self._last_progress_log.get(key)
        if pct in (0, 1, 3, 50, 90, 95, 99, 100):
            self._last_progress_log[key] = pct
            return True
        if last is None or abs(pct - last) >= 5:
            self._last_progress_log[key] = pct
            return True
        return False

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
            info_cache = {}
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY) as executor:
                while True:
                    udids = get_connected_udids()
                    current_set = set(udids)
                    
                    for cached_u in list(TRUSTED_CACHE):
                        if cached_u not in current_set and not self.reboot_tracker.is_waiting(cached_u):
                            TRUSTED_CACHE.remove(cached_u)
                            info_cache.pop(cached_u, None)

                    if udids:
                        untrusted_targets = [u for u in udids if u not in TRUSTED_CACHE]
                        futures = {u: executor.submit(check_device_trust, u) for u in untrusted_targets}
                        new_results = {u: f.result() for u, f in futures.items()}
                        
                        trust_results = {u: (True if u in TRUSTED_CACHE else new_results.get(u, False)) for u in udids}
                    else:
                        trust_results = {}

                    info_futures = {}
                    for u in udids:
                        trusted = trust_results.get(u, False)
                        cached = info_cache.get(u)
                        if cached is None or cached.get("trusted") != trusted:
                            info_futures[u] = executor.submit(self._build_info, u, trusted)
                    for u, future in info_futures.items():
                        info_cache[u] = future.result()
                    info_results = {u: info_cache[u] for u in udids if u in info_cache}

                    try:
                        self._queue_poll_sync(udids, trust_results, info_results)
                    except Exception:
                        break

                    time.sleep(0.3)

        threading.Thread(target=_poll, daemon=True).start()

    def _calculate_columns(self, width=None):
        """Tính toán số cột thẻ thiết bị tối ưu:
        - Mặc định mở app (width 1300px, canvas ~1276px): hiển thị đúng 3 thiết bị trên 1 hàng
        - Khi phóng to Full HD (width ~1920px, canvas ~1896px): hiển thị 5 thiết bị trên 1 hàng
        - Màn hình siêu rộng 2K/4K (width >= 2100px): 6 cột
        """
        if width is None:
            try:
                width = self.dev_canvas.winfo_width()
            except Exception:
                width = 0
        if width <= 0:
            return getattr(self, "_grid_cols", 3)
        if width < 800:
            return 2
        elif width < 1550:
            return 3
        elif width < 2100:
            return 5
        else:
            return 6

    def _relayout_cards(self, cols=None):
        """Co giãn và chia lại lưới thẻ thiết bị linh hoạt (Responsive Grid)"""
        if cols is None:
            cols = self._calculate_columns()
        self._grid_cols = cols

        # Cấu hình lại trọng số các cột linh hoạt (dùng uniform='' để xóa nhóm cột cũ triệt để)
        for col in range(12):
            if col < cols:
                self.grid_container.columnconfigure(col, weight=1, uniform="dev_col")
            else:
                self.grid_container.columnconfigure(col, weight=0, uniform="")

        udid_list = list(self.rows.keys())
        for idx, udid in enumerate(udid_list):
            r = idx // cols
            c = idx % cols
            card = self.rows[udid]
            card.grid_forget()
            card.grid(row=r, column=c, padx=4, pady=3, sticky="ew")

    def _sync_cards(self, current_udids, trust_results, info_results=None):
        info_results = info_results or {}
        with self.lock:
            need_relayout = False
            trusted_cnt = 0
            untrusted_cnt = 0
            now_ts = time.time()

            for udid in list(self.rows.keys()):
                if udid not in current_udids:
                    if self.reboot_tracker.is_waiting(udid):
                        self.rows[udid].push_step("Hoàn tất • Đang khởi động lại...")
                        continue
                    self.rows[udid].destroy()
                    del self.rows[udid]
                    need_relayout = True
                    self.log(udid, "Đã ngắt kết nối.")

            for udid in current_udids:
                is_locked_reboot = self.reboot_tracker.is_waiting(udid, now=now_ts)
                
                if is_locked_reboot:
                    is_trusted = True
                else:
                    is_trusted = trust_results.get(udid, False)

                if is_trusted: trusted_cnt += 1
                else: untrusted_cnt += 1

                if udid not in self.rows:
                    info = info_results.get(udid) or self._build_info(udid, is_trusted=False)
                    card = DeviceCard(self.grid_container, udid, info, app_ref=self)
                    self.rows[udid] = card
                    need_relayout = True
                    self.log(udid, f"Kết nối: {info['name']} • iOS {info['ios']}")
                else:
                    card = self.rows[udid]
                    if is_locked_reboot:
                        card.push_step("Hoàn tất • Đang khởi động lại...")
                        if trust_results.get(udid, False):
                            self.reboot_tracker.clear(udid)
                    else:
                        if card.info.get("trusted") != is_trusted:
                            info = info_results.get(udid) or self._build_info(udid, is_trusted=False)
                            card.update_trust_status(is_trusted, info)
                            if is_trusted:
                                self.log(udid, f"Đã xác nhận Trust: {info['name']} • iOS {info['ios']}")

            if need_relayout:
                self._relayout_cards()

            dev_cnt = len(self.rows)
            self.lbl_dev_count.config(text=f"Tổng: {dev_cnt}")
            self.lbl_trust_count.config(text=f"Trust: {trusted_cnt}")
            self.lbl_untrust_count.config(text=f"Not Trust: {untrusted_cnt}")
            if hasattr(self, "lbl_stat_total_dev"):
                self.lbl_stat_total_dev.config(text=str(dev_cnt))
            if hasattr(self, "lbl_log_dev_info"):
                self.lbl_log_dev_info.config(text=f"Số thiết bị đang kết nối: {dev_cnt}")

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

            cell_f = tk.Frame(self.conf_list_container, bg=COLOR_HEADER_BG, highlightbackground=COLOR_WHITE_BORDER, highlightthickness=1, bd=0)
            cell_f.grid(row=r, column=c, padx=5, pady=4, sticky="ew")

            m_color = "#059669" if "UDID" in item['match_type'] else "#0284C7"

            lbl_line1_stt = tk.Label(cell_f, text=f"{idx + 1}. 📂 {item['folder_name']} (iOS {item['bk_ios']})", font=("Segoe UI", 10, "bold"), fg="#0284C7", bg=COLOR_HEADER_BG, anchor="w")
            lbl_line1_stt.pack(side="top", anchor="w", padx=8, pady=(6, 0))

            lbl_line1_dev = tk.Label(cell_f, text=f"   ➔ 📱 {item['dev_name']} (iOS {item['dev_ios']}) [{item['match_type']}]", font=("Segoe UI", 10, "bold"), fg=m_color, bg=COLOR_HEADER_BG, anchor="w")
            lbl_line1_dev.pack(side="top", anchor="w", padx=8, pady=(2, 0))

            lbl_line2_udid = tk.Label(cell_f, text=f"   UDID TARGET: {item['udid']}", font=("Consolas", 9), fg=COLOR_TEXT_MUTED, bg=COLOR_HEADER_BG, anchor="w")
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

        auto_activate = bool(self.var_auto_activate_after_restore.get())
        set_language = bool(self.var_set_lang_after_active.get())
        language_preset = self.var_lang_locale.get()
        for target_udid, bk_path in self.pending_restore_map:
            if not self._begin_operation(target_udid, "restore"):
                continue
            threading.Thread(
                target=self._restore_worker,
                args=(target_udid, bk_path, target_root, src_label, auto_activate, set_language, language_preset, True),
                daemon=True,
            ).start()
        
        self.after(1200, self._hide_confirm_frame)

    # ================== WORKER BACKUP (CƠ CHẾ ĐẶT TÊN 1_iPhone, 2_iPhone...) ==================
    def start_backup_all(self):
        if not self._require_license():
            return
        if not self.rows:
            messagebox.showwarning("CẢNH BÁO", "Không có thiết bị kết nối!")
            return
        target_root = self.lbl_path_gen.cget("text").strip()
        os.makedirs(target_root, exist_ok=True)
        self._save_settings_from_ui()

        udids = list(self.rows.keys())
        names_by_udid = self._reserve_backup_names(target_root, udids)
        remove_tiktok = bool(self.var_tik.get())
        remove_tiktok_lite = bool(self.var_lite.get())

        for udid in udids:
            if not self._begin_operation(udid, "backup"):
                continue
            reserved_name = names_by_udid.get(udid)
            threading.Thread(
                target=self._backup_worker,
                args=(udid, target_root, reserved_name, remove_tiktok, remove_tiktok_lite, True),
                daemon=True,
            ).start()

    def _reserve_backup_names(self, target_root, udids):
        names_by_udid = {}
        used_names = set()
        with self.lock:
            root_key = os.path.abspath(target_root).lower()
            current_max = _max_backup_index(target_root)
            next_index = max(current_max, self._backup_name_counters.get(root_key, 0))
            existing_names = set()
            try:
                existing_names = {name for name in os.listdir(target_root) if os.path.isdir(os.path.join(target_root, name))}
            except Exception:
                pass
            for udid in udids:
                card = self.rows.get(udid)
                dev_name = card.info.get('name') if card else 'iPhone'
                dev_name = re.sub(r'[^\w\-\s]', '', dev_name).strip() or 'iPhone'
                while True:
                    next_index += 1
                    reserved = f"{next_index}_{dev_name}"
                    if reserved not in existing_names and reserved not in used_names:
                        break
                used_names.add(reserved)
                names_by_udid[udid] = reserved
            self._backup_name_counters[root_key] = next_index
        return names_by_udid

    def _generate_next_backup_foldername(self, target_root, base_device_name="iPhone"):
        clean_name = re.sub(r'[^\w\-\s]', '', base_device_name).strip() or "iPhone"
        next_idx = _max_backup_index(target_root) + 1
        candidate = f"{next_idx}_{clean_name}"
        if os.path.exists(os.path.join(target_root, candidate)):
            dup_idx = 1
            while True:
                dup_candidate = f"{candidate}_{dup_idx}"
                if not os.path.exists(os.path.join(target_root, dup_candidate)):
                    candidate = dup_candidate
                    break
                dup_idx += 1
        return candidate

    def _backup_worker(self, udid, target_root, reserved_name=None, remove_tiktok=False, remove_tiktok_lite=False, operation_reserved=False):
        with self.lock:
            self.active_backups.add(udid)
        row = self.rows.get(udid)
        if not SEMAPHORE.acquire(timeout=1):
            if row: row.push_step("Đang chờ slot...")
            SEMAPHORE.acquire()
        backup_job = None
        try:
            if not pair_validate(udid, log_fn=lambda s, **_: self.log(udid, s)):
                if row: row.push_step("Lỗi Pair")
                return

            if row:
                row.push_step("Đang Sao Lưu")
                row.set_pct(0)

            def on_line(s, is_err=False):
                if is_err or self._should_log_stream_line(udid, s):
                    self.log(udid, s, is_err=is_err)
                pct = self._parse_any_percent(s)
                if pct is not None and row:
                    row.set_pct(pct)
                    row.push_step(f"Sao lưu {pct}%")

            backup_job = create_backup_job(target_root, udid)
            rc, _ = run_stream(
                ["idevicebackup2", "-u", udid, "backup", "--full", backup_job.job_root],
                on_line=on_line,
            )
            created_default_dir = backup_job.output_path

            if rc == 0 and os.path.isdir(created_default_dir) and not verify_backup_layout(created_default_dir):
                info = self._build_info(udid)
                dev_name = info.get('name', 'iPhone')
                
                with self.lock:
                    if not reserved_name:
                        final_name = self._generate_next_backup_foldername(target_root, dev_name)
                    else:
                        final_name = reserved_name
                    final_dst = os.path.join(target_root, final_name)
                    if os.path.exists(final_dst):
                        final_name = f"{final_name}_{int(time.time())}"
                        final_dst = os.path.join(target_root, final_name)
                    os.rename(created_default_dir, final_dst)

                if row:
                    row.set_pct(100)
                    row.push_step("Backup xong")
                self.log(udid, f"Backup hoàn tất ➔ Thư mục: {final_name}")

                if remove_tiktok:
                    uninstall_app_any(udid, BIDS_TIKTOK, "TikTok", row, lambda s, is_err=False: self.log(udid, s, is_err=is_err))

                if remove_tiktok_lite:
                    uninstall_app_any(udid, BIDS_TIKTOK_LITE, "TikTok Lite", row, lambda s, is_err=False: self.log(udid, s, is_err=is_err))
            else:
                if row: row.push_step("Lỗi Backup")
        finally:
            if backup_job is not None:
                try:
                    cleanup_owned_job(backup_job.job_root, missing_ok=True)
                except Exception as e:
                    self.log(udid, f"Lỗi dọn staging backup: {e}", is_err=True)
            with self.lock:
                self.active_backups.discard(udid)
            SEMAPHORE.release()
            if operation_reserved:
                self.operations.end(udid, "backup")

    # ================== WORKER RESTORE PRO ==================
    def start_restore_all(self):
        if not self._require_license():
            return
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

    def _restore_worker(self, target_udid, backup_folder_full, target_after_restore, source_store="A", auto_activate=False, set_language=False, language_preset=None, operation_reserved=False):
        with self.lock:
            self.active_restores.add(target_udid)
        row = self.rows.get(target_udid)
        stage = None
        if not SEMAPHORE.acquire(timeout=1):
            if row: row.push_step("Đang chờ slot...")
            SEMAPHORE.acquire()
        try:
            if not pair_validate(target_udid, log_fn=lambda s, **_: self.log(target_udid, s)):
                if row: row.push_step("Lỗi Pair")
                self.log(target_udid, "Cần xác nhận 'Tin Cậy' trên màn hình iPhone!", is_err=True)
                return

            try:
                stage = create_restore_stage(backup_folder_full, target_udid)
            except Exception as e:
                self.log(target_udid, f"Lỗi tạo bản sao Staging: {e}", is_err=True)
                return

            base_dir = os.path.dirname(stage.backup_path)
            src_name = os.path.basename(stage.backup_path)
            cmd = ["idevicebackup2", "-u", target_udid, "-s", src_name, "restore", os.path.normpath(base_dir), "--settings", "--remove"]

            if row:
                row.push_step("Restore 0%")
                row.set_pct(0)

            def on_line(s, is_err=False):
                if is_err or self._should_log_stream_line(target_udid, s):
                    self.log(target_udid, s, is_err=is_err)
                pct = self._parse_any_percent(s)
                if pct is not None and row:
                    row.set_pct(pct)
                    row.push_step(f"Restore {pct}%")

            rc, last_lines = run_stream(cmd, on_line=on_line)
            if rc == 0:
                self.log(target_udid, "Khôi phục dữ liệu Restore hoàn tất thành công.")
                
                # KHÓA TRẠNG THÁI REBOOT TRONG 35 GIÂY (Ngăn không cho Polling báo Not Trust)
                self.reboot_tracker.mark(target_udid, timeout=135.0)

                try:
                    os.makedirs(target_after_restore, exist_ok=True)
                    dest = os.path.join(target_after_restore, os.path.basename(backup_folder_full))
                    if os.path.exists(dest):
                        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        dest = os.path.join(target_after_restore, f"{os.path.basename(backup_folder_full)}_{stamp}")

                    try:
                        shutil.move(backup_folder_full, dest)
                    except Exception:
                        shutil.copytree(backup_folder_full, dest)
                        shutil.rmtree(backup_folder_full)

                    self.log(target_udid, f"Đã chuyển kho thành công: {source_store} ➔ Kho đối diện:\n{os.path.basename(dest)}")
                    
                    # Cộng bộ đếm restore thành công và tự động cập nhật lại số lượng kho
                    self._post_ui(self._count_restore_done)
                    self.log(target_udid, f"✓ Đã chuyển iPhone thứ {self.restore_done_count + 1} qua Kho đối diện thành công!")
                    
                    if row:
                        row.set_pct(100)
                        row.push_step("Hoàn tất Restore 100%")

                    # === TỰ ĐỘNG ACTIVATE SAU RESTORE (nếu bật) ===
                    if auto_activate:
                        self.log(target_udid, "⚡ Auto Activate sau Restore: đang chờ thiết bị reboot...")
                        transitioned = operation_reserved and self.operations.transition(
                            target_udid, "restore", "auto_activate"
                        )
                        threading.Thread(
                            target=self._post_restore_activate_worker,
                            args=(target_udid, set_language, language_preset, transitioned),
                            daemon=True
                        ).start()
                    # (Thông báo rút máy sẽ hiện sau khi TẤT CẢ máy trong đợt hoàn tất — xem finally bên dưới)

                except Exception as e:
                    self.log(target_udid, f"Lỗi khi chuyển kho sau restore: {e}", is_err=True)

            else:
                if row: row.push_step(f"Restore lỗi (exit {rc})")
                for line in last_lines[-10:]:
                    self.log(target_udid, line, is_err=True)
        finally:
            if stage:
                try:
                    cleanup_owned_job(stage.job_root, missing_ok=True)
                except Exception as e:
                    self.log(target_udid, f"Lỗi dọn dẹp staging: {e}", is_warn=True)
            with self.lock:
                self.active_restores.discard(target_udid)
                _all_done = len(self.active_restores) == 0  # Kiểm tra trong lock
            SEMAPHORE.release()
            if operation_reserved:
                self.operations.end(target_udid, "restore")
            # === THÔNG BÁO RÚT MÁY KHI TẤT CẢ ĐỢT XONG (chỉ khi Auto Activate TẮT) ===
            if _all_done and not auto_activate:
                done_count = self.restore_done_count
                banner = "=" * 58
                self.log("SYSTEM", banner, is_warn=True)
                self.log("SYSTEM", f"🔔 ĐÃ RESTORE XONG {done_count} MÁY – RÚT TẤT CẢ RA & CẮM ĐỢT MỚI!", is_warn=True)
                self.log("SYSTEM", "   Tất cả iPhone đang reboot, KHÔNG cần chờ thêm.", is_warn=True)
                self.log("SYSTEM", banner, is_warn=True)
                def _beep_all_done():
                    # 1. Nhấp nháy icon TikTool trên thanh taskbar (màu cam) để dù tắt tiếng vẫn biết
                    try:
                        import ctypes
                        hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
                        ctypes.windll.user32.FlashWindow(hwnd, True)
                    except Exception:
                        pass
                    # 2. Phát file âm thanh tích hợp sẵn trong app (notify.wav)
                    try:
                        import winsound, os
                        app_dir = os.path.dirname(os.path.abspath(__file__))
                        sound_file = os.path.join(app_dir, "notify.wav")
                        if not os.path.exists(sound_file):
                            sound_file = r"C:\Windows\Media\Windows Notify.wav"
                        if os.path.exists(sound_file):
                            winsound.PlaySound(sound_file, winsound.SND_FILENAME)
                            import time; time.sleep(0.5)
                            winsound.PlaySound(sound_file, winsound.SND_FILENAME)
                        else:
                            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
                    except Exception:
                        pass
                threading.Thread(target=_beep_all_done, daemon=True).start()

    def _update_card_progress(self, udid, pct=None, step=None, task=None):
        """Cập nhật tiến độ và trạng thái card thiết bị an toàn, tự tìm card mới nhất nếu thiết bị vừa cắm lại"""
        try:
            row = self.rows.get(udid)
            if row:
                if pct is not None:
                    row.set_pct(pct)
                if step is not None:
                    row.push_step(step)
                if task is not None:
                    row.set_task(task)
        except Exception:
            pass

    def _update_card_step(self, udid, text):
        """Cập nhật trạng thái card thiết bị an toàn, tự động tìm card mới nhất nếu thiết bị vừa cắm lại"""
        try:
            row = self.rows.get(udid)
            if row:
                row.push_step(text)
        except Exception:
            pass

    def _post_restore_activate_worker(self, udid, set_language=False, language_preset=None, operation_reserved=False):
        """Sau khi Restore xong, chờ đúng 100 giây cho iPhone khởi động hoàn tất rồi tự động Batch Activate."""
        with self.lock:
            self.active_activates.add(udid)
        try:
            TOTAL_WAIT = 100  # Đợi đúng 100 giây
            self.log(udid, f"⏳ Restore hoàn tất. Bắt đầu đếm ngược ({TOTAL_WAIT}s) cho iPhone khởi động hoàn toàn...")

            start_time = time.time()
            last_log_time = start_time

            while True:
                elapsed = int(time.time() - start_time)
                remaining = TOTAL_WAIT - elapsed
                if remaining <= 0:
                    break

                self._update_card_step(udid, f"Chờ khởi động ({remaining}s)...")

                # Cứ mỗi 20 giây log tiến độ một lần
                if time.time() - last_log_time >= 20:
                    self.log(udid, f"⏳ Đang chờ iPhone khởi động lại: còn {remaining}s...")
                    last_log_time = time.time()

                time.sleep(2)

            # Hết thời gian chờ, kiểm tra kết nối thiết bị
            self.log(udid, "⌛ Đã hết 100 giây chờ! Đang kiểm tra kết nối thiết bị...")
            self._update_card_step(udid, "Kiểm tra kết nối...")

            # Chờ tối đa 45 giây nếu thiết bị chưa kịp hiện trong danh sách USB
            check_deadline = time.time() + 45
            connected = False
            while time.time() < check_deadline:
                if udid in get_connected_udids():
                    connected = True
                    break
                time.sleep(2)

            if not connected:
                self.log(udid, "⚠️ Không tìm thấy thiết bị kết nối USB sau thời gian chờ. Bỏ qua Auto Activate.", is_err=True)
                self._update_card_step(udid, "Không thấy thiết bị – Bỏ qua")
                return

            # Nghỉ thêm 3 giây để ổn định cổng kết nối
            time.sleep(3)
            self.log(udid, "✅ iPhone đã khởi động xong & kết nối ổn định ➔ Bắt đầu Batch Activate...")
            self._update_card_step(udid, "Bắt đầu Auto Activate")

            # Chạy toàn bộ pipeline Batch Activate 3 giai đoạn
            self._batch_activate_worker(
                udid,
                set_language=set_language,
                language_preset=language_preset,
                operation_reserved=operation_reserved,
                operation_kind="auto_activate",
            )
        finally:
            with self.lock:
                self.active_activates.discard(udid)
            if operation_reserved:
                self.operations.end(udid, "auto_activate")

    def _on_app_close(self):
        """Xử lý sự kiện khi người dùng bấm dấu X tắt app.
        Cảnh báo nguy hiểm nếu đang Restore / Backup / Activate dở dang.
        """
        operations = self.operations.snapshot()
        n_rest = sum(kind == "restore" for kind in operations.values())
        n_bk = sum(kind == "backup" for kind in operations.values())
        n_act = sum(kind in ("activate", "auto_activate", "language", "webclip") for kind in operations.values())

        if n_rest > 0 or n_bk > 0 or n_act > 0:
            details = []
            if n_rest > 0:
                details.append(f"• {n_rest} máy iPhone đang RESTORE dữ liệu")
            if n_bk > 0:
                details.append(f"• {n_bk} máy iPhone đang SAO LƯU (BACKUP)")
            if n_act > 0:
                details.append(f"• {n_act} máy iPhone đang KÍCH HOẠT / AUTO ACTIVATE")

            detail_str = "\n".join(details)
            msg = (
                f"⚠️ CẢNH BÁO: HỆ THỐNG ĐANG CÓ TIẾN TRÌNH HOẠT ĐỘNG!\n\n"
                f"{detail_str}\n\n"
                f"❌ NẾU BẠN TẮT APP NGAY LÚC NÀY:\n"
                f"• Thiết bị đang Restore sẽ bị nạp dở dữ liệu ➔ RẤT DỄ BỊ LỖI TREO TÁO / HỎNG HĐH (bắt buộc phải cắm máy tính restore lại)!\n"
                f"• Bản Backup đang tạo sẽ bị gián đoạn, hỏng file (thiếu Manifest.db)!\n"
                f"• Thiết bị đang kích hoạt sẽ chưa xong các bước bỏ qua thiết lập.\n\n"
                f"👉 BẠN CÓ THỰC SỰ MUỐN DỪNG VÀ ÉP TẮT APP NGAY BÂY GIỜ KHÔNG?"
            )
            ans = messagebox.askyesno(
                "CẢNH BÁO TIẾN TRÌNH ĐANG CHẠY",
                msg,
                icon="warning",
                default="no"
            )
            if not ans:
                return  # Người dùng chọn Không: Hủy đóng app, tiếp tục làm việc bình thường

            # Nếu người dùng chấp nhận ép tắt, dừng toàn bộ subprocess đã đăng ký.
            self.process_runner.terminate_all()

        try:
            self._save_settings_from_ui()
        except Exception:
            pass

        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)

if __name__ == "__main__":
    app = App()
    app.mainloop()
