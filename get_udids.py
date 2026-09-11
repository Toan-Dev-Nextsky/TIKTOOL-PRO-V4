import subprocess
import os
import sys

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

file_path = "danh_sach_100_UDID.txt"
existing = set()

if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        existing = {line.strip() for line in f if line.strip()}

cmd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "idevice_id.exe")
try:
    res = subprocess.run([cmd, "-l"], capture_output=True, text=True, check=True)
    current = [u.strip() for u in res.stdout.splitlines() if u.strip()]
except Exception as e:
    current = []
    print(f"Loi khi chay idevice_id: {e}")

new_count = 0
for u in current:
    if u not in existing:
        existing.add(u)
        new_count += 1

with open(file_path, "w", encoding="utf-8") as f:
    for u in sorted(existing):
        f.write(u + "\n")

print("========================================================")
print("       TIKTOOL PRO - THU THAP DANH SACH UDID")
print("========================================================")
print(f"-> So may dang cam hien tai    : {len(current)} may")
print(f"-> Da them moi trong lan nay   : {new_count} may")
print(f"-> TONG SO UDID TRONG DANH SACH: {len(existing)} / 100 may")
print("========================================================")
print(f"File luu tai: {os.path.abspath(file_path)}")
print("========================================================")
