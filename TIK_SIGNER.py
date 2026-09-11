# -*- coding: utf-8 -*-
"""
TIK SIGNER PRO — Chuyên Ký IPA Hàng Loạt Theo Chứng Chỉ / UDID
Dành riêng cho dàn máy làm phôi TikTok Lite Nhật · TIKTOOL PRO V4
Giao diện: Python ttkbootstrap (Darkly Theme)
"""
import os
import sys
import re
import time
import queue
import plistlib
import zipfile
import threading
import subprocess
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# ─────────────────── Đường dẫn chuẩn ───────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
CERTS_DIR    = os.path.join(BASE_DIR, "certs")
IPAS_DIR     = os.path.join(BASE_DIR, "ipas")
ZSIGN_EXE    = os.path.join(BASE_DIR, "zsign.exe")
IDEV_ID      = os.path.join(BASE_DIR, "idevice_id.exe")
os.makedirs(CERTS_DIR, exist_ok=True)
os.makedirs(IPAS_DIR,  exist_ok=True)

APP_TITLE = "TIK SIGNER PRO  ·  CHUYÊN KÝ IPA HÀNG LOẠT"
VERSION   = "1.1.0"

# ═══════════════════════════════════════════════════════════
#  Helpers — Backend Ký Số & UDID
# ═══════════════════════════════════════════════════════════

def run_cmd(cmd, on_line=None, timeout=None):
    """Chạy lệnh subprocess, stream output theo dòng."""
    lines = []
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        for line in proc.stdout:
            line = line.rstrip()
            lines.append(line)
            if on_line:
                on_line(line)
        proc.wait(timeout=timeout)
        return proc.returncode, lines
    except Exception as e:
        msg = f"[LỖI] {e}"
        if on_line:
            on_line(msg)
        return -1, [msg]


def list_devices():
    """Lấy danh sách UDID các máy đang cắm."""
    try:
        result = subprocess.run(
            [IDEV_ID, "-l"],
            capture_output=True, text=True, timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return [u.strip() for u in result.stdout.splitlines() if u.strip()]
    except Exception:
        return []


def get_device_name(udid):
    """Lấy tên thiết bị iPhone."""
    idev_info = os.path.join(BASE_DIR, "ideviceinfo.exe")
    if not os.path.exists(idev_info):
        return udid[:10] + "..."
    try:
        r = subprocess.run(
            [idev_info, "-u", udid, "-k", "DeviceName"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        name = r.stdout.strip()
        return name if name else udid[:10] + "..."
    except Exception:
        return udid[:10] + "..."


def extract_udids_from_prov(prov_path):
    """Đọc danh sách UDID được cấp phép trong file .mobileprovision."""
    try:
        with open(prov_path, "rb") as f:
            raw = f.read()
        start = raw.find(b"<?xml")
        end   = raw.rfind(b"</plist>")
        if start == -1 or end == -1:
            return []
        pl = plistlib.loads(raw[start: end + 8])
        return pl.get("ProvisionedDevices", [])
    except Exception:
        return []


def scan_cert_folders():
    """Quét thư mục certs/ và các thư mục theo UDID ở gốc."""
    found = []
    search_roots = [CERTS_DIR, BASE_DIR]
    seen = set()

    for root in search_roots:
        try:
            for entry in os.scandir(root):
                if not entry.is_dir():
                    continue
                folder = entry.path
                if folder in seen or entry.name in (".git", "ipas", "backups", "backups_A", "backups_B", "__pycache__"):
                    continue
                seen.add(folder)

                p12   = None
                prov  = None
                pw    = "1"

                for f in os.scandir(folder):
                    fn_lower = f.name.lower()
                    if fn_lower.endswith(".p12"):
                        p12 = f.path
                    elif fn_lower.endswith(".mobileprovision"):
                        prov = f.path
                    elif fn_lower in ("pass.txt", "password.txt"):
                        try:
                            pw = Path(f.path).read_text(encoding="utf-8").strip() or "1"
                        except Exception:
                            pw = "1"

                if p12 and prov:
                    udids_in_prov = extract_udids_from_prov(prov)
                    found.append({
                        "folder":    folder,
                        "label":     entry.name,
                        "p12":       p12,
                        "prov":      prov,
                        "pw":        pw,
                        "udids":     udids_in_prov,
                    })
        except Exception:
            continue

    return found


def match_cert_for_udid(cert_list, udid):
    """Tìm cert phù hợp nhất cho 1 UDID."""
    for c in cert_list:
        if udid in c["udids"] or udid.lower() == c["label"].lower():
            return c
    for c in cert_list:
        if not c["udids"]:
            return c
    return None


# ═══════════════════════════════════════════════════════════
#  GIAO DIỆN CHÍNH (GUI)
# ═══════════════════════════════════════════════════════════

class TikSignerApp(ttk.Window):

    def __init__(self):
        super().__init__(
            title=APP_TITLE,
            themename="darkly",
            size=(1140, 750),
            minsize=(900, 600),
        )

        # Trạng thái
        self._devices   = []
        self._dev_names = {}
        self._certs     = []
        self._ipa_orig  = tk.StringVar()
        self._log_q     = queue.Queue()
        self._row_vars  = {}
        self._busy      = False

        # Tự động chọn file IPA gốc mặc định nếu có sẵn
        self._auto_detect_orig_ipa()

        self._build_ui()
        self._refresh_all()
        self._poll_log()

    def _auto_detect_orig_ipa(self):
        """Tự động tìm file TikTok IPA chưa ký trong thư mục ipas/."""
        if os.path.isdir(IPAS_DIR):
            for f in os.listdir(IPAS_DIR):
                if f.lower().endswith(".ipa") and "und3fined" in f.lower():
                    self._ipa_orig.set(os.path.join(IPAS_DIR, f))
                    return
            for f in os.listdir(IPAS_DIR):
                if f.lower().endswith(".ipa") and "signed" not in f.lower():
                    self._ipa_orig.set(os.path.join(IPAS_DIR, f))
                    return

    # ─────────────── XÂY DỰNG GIAO DIỆN ───────────────

    def _build_ui(self):
        # ── Header ──
        hdr = ttk.Frame(self, bootstyle="dark", padding=(20, 12))
        hdr.pack(fill=X, side=TOP)

        ttk.Label(hdr, text="⚡", font=("Segoe UI Emoji", 24)).pack(side=LEFT, padx=(0, 10))
        ttk.Label(hdr,
                  text="TIK SIGNER PRO",
                  font=("Segoe UI", 18, "bold"),
                  bootstyle="info").pack(side=LEFT)
        ttk.Label(hdr,
                  text=f"  v{VERSION}  ·  Ký IPA Hàng Loạt Theo Chứng Chỉ / UDID",
                  font=("Segoe UI", 10),
                  bootstyle="secondary").pack(side=LEFT, padx=6, pady=5)

        ttk.Button(hdr, text="📁 Mở Thư Mục IPAS", bootstyle="outline-light",
                   command=lambda: os.startfile(IPAS_DIR), width=18).pack(side=RIGHT, padx=4)
        ttk.Button(hdr, text="🔄 Làm Mới Máy", bootstyle="outline-info",
                   command=self._refresh_all, width=14).pack(side=RIGHT, padx=4)

        ttk.Separator(self, orient=HORIZONTAL).pack(fill=X)

        # ── Thân chính (Chia 2 cột Trái / Phải) ──
        body = ttk.Panedwindow(self, orient=HORIZONTAL)
        body.pack(fill=BOTH, expand=True, padx=12, pady=10)

        left  = ttk.Frame(body, padding=4)
        right = ttk.Frame(body, padding=4)
        body.add(left,  weight=3)
        body.add(right, weight=2)

        self._build_left(left)
        self._build_right(right)

        # ── Status Bar dưới cùng ──
        self._status_var = tk.StringVar(value="Sẵn sàng.")
        sb = ttk.Label(self, textvariable=self._status_var,
                       bootstyle="secondary", anchor=W, padding=(14, 4))
        sb.pack(fill=X, side=BOTTOM)

    def _build_left(self, parent):
        # ── Bảng Danh Sách Thiết Bị Cần Ký ──
        dev_frame = ttk.LabelFrame(parent, text=" 📱  Thiết Bị Cần Ký (Theo UDID) ", padding=10)
        dev_frame.pack(fill=BOTH, expand=True)

        tb = ttk.Frame(dev_frame)
        tb.pack(fill=X, pady=(0, 8))

        self._dev_count_lbl = ttk.Label(tb, text="0 máy đang cắm", bootstyle="info",
                                        font=("Segoe UI", 10, "bold"))
        self._dev_count_lbl.pack(side=LEFT)

        ttk.Button(tb, text="📋 Sao Chép 10 UDID",
                   bootstyle="outline-info", width=18,
                   command=self._copy_udids).pack(side=RIGHT, padx=2)
        ttk.Button(tb, text="💾 Xuất File UDID (.txt)",
                   bootstyle="outline-success", width=19,
                   command=self._export_udids).pack(side=RIGHT, padx=2)

        # Bảng Treeview
        cols = ("device", "udid", "cert", "ipa_signed", "progress")
        self._tree = ttk.Treeview(
            dev_frame, columns=cols, show="headings",
            bootstyle="dark", height=15,
        )
        col_cfg = [
            ("device",     "Tên Máy",        130, W),
            ("udid",       "Mã UDID",        220, W),
            ("cert",       "Chứng Chỉ (.p12)", 150, CENTER),
            ("ipa_signed", "Trạng Thái Ký",  180, CENTER),
            ("progress",   "Tiến Độ",         90, CENTER),
        ]
        for cid, heading, width, anchor in col_cfg:
            self._tree.heading(cid, text=heading)
            self._tree.column(cid, width=width, anchor=anchor)

        vsb = ttk.Scrollbar(dev_frame, orient=VERTICAL,   command=self._tree.yview, bootstyle="round-dark")
        hsb = ttk.Scrollbar(dev_frame, orient=HORIZONTAL, command=self._tree.xview, bootstyle="round-dark")
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side=RIGHT, fill=Y)
        hsb.pack(side=BOTTOM, fill=X)
        self._tree.pack(fill=BOTH, expand=True)

        # ── Nút KÝ HÀNG LOẠT ──
        act_frame = ttk.Frame(parent, padding=(0, 10, 0, 0))
        act_frame.pack(fill=X)

        self._btn_sign = ttk.Button(
            act_frame,
            text="⚡  KÝ IPA HÀNG LOẠT CHO TẤT CẢ MÁY",
            bootstyle="warning",
            command=self._start_sign_all,
            padding=(0, 10),
        )
        self._btn_sign.pack(fill=X)

    def _build_right(self, parent):
        # ── 1. File IPA Gốc ──
        ipa_frame = ttk.LabelFrame(parent, text=" 📦  File IPA Gốc Cần Ký ", padding=10)
        ipa_frame.pack(fill=X)

        ipa_row = ttk.Frame(ipa_frame)
        ipa_row.pack(fill=X)
        ttk.Entry(ipa_row, textvariable=self._ipa_orig, state="readonly",
                  bootstyle="dark").pack(side=LEFT, fill=X, expand=True, padx=(0, 6))
        ttk.Button(ipa_row, text="📂 Chọn IPA...",
                   bootstyle="outline-light",
                   command=self._browse_ipa, width=12).pack(side=RIGHT)

        # ── 2. Thư mục Chứng Chỉ (certs/) ──
        cert_frame = ttk.LabelFrame(parent, text=" 🔑  Kho Chứng Chỉ (certs/) ", padding=10)
        cert_frame.pack(fill=BOTH, expand=True, pady=(10, 0))

        cert_tb = ttk.Frame(cert_frame)
        cert_tb.pack(fill=X, pady=(0, 6))
        ttk.Label(cert_tb, text="Thả bộ cert tải về vào thư mục: ", bootstyle="secondary",
                  font=("Segoe UI", 9)).pack(side=LEFT)
        ttk.Button(cert_tb, text="📁 Mở Thư Mục certs/", bootstyle="outline-info", width=18,
                   command=lambda: os.startfile(CERTS_DIR)).pack(side=RIGHT)
        ttk.Button(cert_tb, text="🔄 Quét Lại Cert", bootstyle="outline-secondary", width=14,
                   command=self._refresh_certs).pack(side=RIGHT, padx=4)

        cert_cols = ("label", "devices", "p12")
        self._cert_tree = ttk.Treeview(
            cert_frame, columns=cert_cols, show="headings",
            bootstyle="dark", height=6,
        )
        self._cert_tree.heading("label",   text="Thư Mục Cert")
        self._cert_tree.heading("devices", text="Số UDID")
        self._cert_tree.heading("p12",     text="File .p12")
        self._cert_tree.column("label",   width=150, anchor=W)
        self._cert_tree.column("devices", width=80,  anchor=CENTER)
        self._cert_tree.column("p12",     width=130, anchor=W)

        cert_vsb = ttk.Scrollbar(cert_frame, orient=VERTICAL, command=self._cert_tree.yview, bootstyle="round-dark")
        self._cert_tree.configure(yscrollcommand=cert_vsb.set)
        cert_vsb.pack(side=RIGHT, fill=Y)
        self._cert_tree.pack(fill=BOTH, expand=True)

        # ── 3. Nhật Ký Tiến Trình Ký (Log) ──
        log_frame = ttk.LabelFrame(parent, text=" 🖥️  Nhật Ký Ký Số (Log) ", padding=8)
        log_frame.pack(fill=BOTH, expand=True, pady=(10, 0))

        log_ctrl = ttk.Frame(log_frame)
        log_ctrl.pack(fill=X, pady=(0, 4))
        ttk.Button(log_ctrl, text="🗑 Xóa log", bootstyle="outline-danger", width=10,
                   command=self._clear_log).pack(side=RIGHT)

        self._log_txt = tk.Text(
            log_frame,
            height=10,
            state="disabled",
            bg="#0d1117", fg="#e6edf3",
            insertbackground="white",
            selectbackground="#1f4068",
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
        )
        log_vsb = ttk.Scrollbar(log_frame, orient=VERTICAL, command=self._log_txt.yview, bootstyle="round-dark")
        self._log_txt.configure(yscrollcommand=log_vsb.set)
        log_vsb.pack(side=RIGHT, fill=Y)
        self._log_txt.pack(fill=BOTH, expand=True)

        self._log_txt.tag_config("ok",   foreground="#3fb950")
        self._log_txt.tag_config("err",  foreground="#f85149")
        self._log_txt.tag_config("warn", foreground="#d29922")
        self._log_txt.tag_config("info", foreground="#58a6ff")
        self._log_txt.tag_config("dim",  foreground="#8b949e")

    # ─────────────── QUÉT DỮ LIỆU ───────────────

    def _refresh_all(self):
        self._refresh_devices()
        self._refresh_certs()

    def _refresh_devices(self):
        udids = list_devices()
        self._devices = udids
        self._dev_names = {}
        for u in udids:
            self._dev_names[u] = get_device_name(u)

        self._tree.delete(*self._tree.get_children())
        self._row_vars.clear()

        for udid in udids:
            name = self._dev_names.get(udid, "iPhone")
            cert = match_cert_for_udid(self._certs, udid)
            cert_lbl = f"✅ {cert['label']}" if cert else "❌ Chưa có cert"

            ipa_signed = self._find_signed_ipa(udid)
            ipa_lbl    = f"✅ {os.path.basename(ipa_signed)}" if ipa_signed else "⏳ Chưa ký"

            iid = self._tree.insert("", END, values=(
                name,
                udid,
                cert_lbl,
                ipa_lbl,
                "100%" if ipa_signed else "0%",
            ))
            self._row_vars[udid] = {"iid": iid, "ipa_signed": ipa_signed}

        count = len(udids)
        self._dev_count_lbl.config(
            text=f"{count} máy đang cắm",
            bootstyle="success" if count > 0 else "danger",
        )
        self._status(f"Đã quét: {count} thiết bị kết nối.")

    def _refresh_certs(self):
        self._certs = scan_cert_folders()
        self._cert_tree.delete(*self._cert_tree.get_children())
        for c in self._certs:
            n = len(c["udids"])
            dev_txt = f"{n} UDID" if n > 0 else "All (Enterprise)"
            self._cert_tree.insert("", END, values=(
                c["label"],
                dev_txt,
                os.path.basename(c["p12"]),
            ))
        self._log(f"Đã nhận diện {len(self._certs)} bộ chứng chỉ trong hệ thống.", tag="info")

        for udid, rv in self._row_vars.items():
            cert = match_cert_for_udid(self._certs, udid)
            cert_lbl = f"✅ {cert['label']}" if cert else "❌ Chưa có cert"
            cur = list(self._tree.item(rv["iid"], "values"))
            cur[2] = cert_lbl
            self._tree.item(rv["iid"], values=cur)

    # ─────────────── LOG & HELPERS ───────────────

    def _status(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self._status_var.set(f"[{ts}]  {msg}")

    def _log(self, msg, tag="dim"):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_q.put((f"[{ts}]  {msg}\n", tag))

    def _poll_log(self):
        try:
            while True:
                line, tag = self._log_q.get_nowait()
                self._log_txt.configure(state="normal")
                self._log_txt.insert(END, line, tag)
                self._log_txt.configure(state="disabled")
                self._log_txt.see(END)
        except queue.Empty:
            pass
        self.after(80, self._poll_log)

    def _clear_log(self):
        self._log_txt.configure(state="normal")
        self._log_txt.delete("1.0", END)
        self._log_txt.configure(state="disabled")

    def _browse_ipa(self):
        path = filedialog.askopenfilename(
            title="Chọn file IPA gốc (chưa ký)",
            initialdir=IPAS_DIR,
            filetypes=[("IPA files", "*.ipa"), ("All files", "*.*")],
        )
        if path:
            self._ipa_orig.set(path)
            self._log(f"Đã chọn file IPA gốc: {os.path.basename(path)}", tag="info")

    def _copy_udids(self):
        if not self._devices:
            messagebox.showwarning("Thông báo", "Không có thiết bị nào đang cắm!")
            return
        text = "\n".join(self._devices)
        self.clipboard_clear()
        self.clipboard_append(text)
        self._log(f"Đã sao chép {len(self._devices)} UDID vào bộ nhớ tạm (Clipboard).", tag="ok")
        messagebox.showinfo("Đã sao chép", f"Đã copy {len(self._devices)} UDID vào clipboard!\nAnh có thể dán (Ctrl+V) để gửi cho bên bán cert.")

    def _export_udids(self):
        if not self._devices:
            messagebox.showwarning("Thông báo", "Không có thiết bị nào đang cắm!")
            return
        path = filedialog.asksaveasfilename(
            title="Lưu file danh sách UDID",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"danh_sach_{len(self._devices)}_UDID.txt",
            initialdir=BASE_DIR,
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                for u in self._devices:
                    name = self._dev_names.get(u, "")
                    f.write(f"{u}\n")
            self._log(f"Đã xuất danh sách UDID ra file: {os.path.basename(path)}", tag="ok")
            messagebox.showinfo("Thành công", f"Đã xuất danh sách UDID thành công:\n{path}")

    def _find_signed_ipa(self, udid):
        if not os.path.isdir(IPAS_DIR):
            return None
        for f in os.listdir(IPAS_DIR):
            if f.lower().endswith(".ipa") and udid[:8].lower() in f.lower():
                return os.path.join(IPAS_DIR, f)
        for f in os.listdir(IPAS_DIR):
            fl = f.lower()
            if fl.endswith(".ipa") and "signed" in fl and "unsigned" not in fl:
                return os.path.join(IPAS_DIR, f)
        return None

    def _update_row(self, udid, col_idx, value):
        def _do():
            rv = self._row_vars.get(udid)
            if not rv:
                return
            vals = list(self._tree.item(rv["iid"], "values"))
            vals[col_idx] = value
            self._tree.item(rv["iid"], values=vals)
        self.after(0, _do)

    def _set_busy(self, busy: bool):
        self._busy = busy
        self._btn_sign.config(state="disabled" if busy else "normal")

    # ─────────────── TIẾN TRÌNH KÝ HÀNG LOẠT ───────────────

    def _start_sign_all(self):
        if self._busy:
            return
        ipa_path = self._ipa_orig.get().strip()
        if not ipa_path or not os.path.isfile(ipa_path):
            messagebox.showerror("Lỗi", "Vui lòng chọn file IPA gốc cần ký trước!")
            return
        if not self._devices:
            messagebox.showwarning("Thông báo", "Không có thiết bị nào đang cắm để ký!")
            return

        self._set_busy(True)
        threading.Thread(target=self._sign_worker, args=(ipa_path,), daemon=True).start()

    def _sign_worker(self, ipa_path):
        self._log("══════════ BẮT ĐẦU TIẾN TRÌNH KÝ HÀNG LOẠT ══════════", tag="warn")
        total = len(self._devices)
        success = 0
        failed  = 0

        for idx, udid in enumerate(self._devices, 1):
            name = self._dev_names.get(udid, udid[:12])
            cert = match_cert_for_udid(self._certs, udid)

            if not cert:
                self._log(f"[{idx}/{total}] {name}: ❌ Chưa có chứng chỉ trong certs/", tag="err")
                self._update_row(udid, 2, "❌ Thiếu cert")
                self._update_row(udid, 3, "Bỏ qua")
                failed += 1
                continue

            # Đặt tên file IPA chứa đầy đủ UDID để TIKTOOL PRO tự nhận diện đúng máy
            out_name = f"TikTok_Lite_{udid}_Signed.ipa"
            out_path = os.path.join(IPAS_DIR, out_name)

            self._log(f"[{idx}/{total}] Đang ký cho: {name} (UDID: {udid[:8]}...)", tag="info")
            self._update_row(udid, 3, "⏳ Đang ký số...")
            self._update_row(udid, 4, "10%")

            t0 = time.time()
            cmd = [
                ZSIGN_EXE,
                "-k", cert["p12"],
                "-p", cert["pw"],
                "-m", cert["prov"],
                "-o", out_path,
                "-z", "9",
                "-E", "-W",
                ipa_path,
            ]

            def on_sign_line(line, udid=udid):
                self._log(f"  {line}", tag="dim")
                m = re.search(r'(\d+)%', line)
                if m:
                    self._update_row(udid, 4, f"{m.group(1)}%")

            rc, _ = run_cmd(cmd, on_line=on_sign_line)
            elapsed = round(time.time() - t0, 1)

            if rc == 0 and os.path.isfile(out_path):
                self._log(f"[{idx}/{total}] {name}: ✅ Ký thành công ({elapsed}s) ➔ {out_name}", tag="ok")
                self._update_row(udid, 3, f"✅ {out_name}")
                self._update_row(udid, 4, "100%")
                self._row_vars[udid]["ipa_signed"] = out_path
                success += 1
            else:
                self._log(f"[{idx}/{total}] {name}: ❌ Ký thất bại! (rc={rc})", tag="err")
                self._update_row(udid, 3, "❌ Lỗi ký")
                self._update_row(udid, 4, "0%")
                failed += 1

        self._log(f"══════════ HOÀN TẤT KÝ: {success}/{total} máy thành công ══════════", tag="warn")
        self._status(f"Ký xong: ✅ {success} thành công / ❌ {failed} thất bại.")
        self.after(0, lambda: self._set_busy(False))

        if success > 0:
            messagebox.showinfo(
                "Ký Xong Hàng Loạt",
                f"Đã ký xong {success} file IPA thành công!\nCác file IPA đã được lưu tại:\n{IPAS_DIR}\n\nAnh có thể dùng TIKTOOL PRO để cài đặt hàng loạt ngay!",
            )


# ═══════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    app = TikSignerApp()
    app.mainloop()
