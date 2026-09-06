# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-06 10:00:00  
**Phiên bản**: `4.8.6 Astro Bot Companion Edition`  
**Trạng thái**: Hoàn thiện Astro Bot Companion — linh vật vector hoạt hình thuần Tkinter với tám sắc thái theo workflow, bong bóng thoại động, hiệu ứng lơ lửng/chớp mắt/LED và tương tác poke. Giữ nguyên Instant Restore 0.004s/máy, Honest Auto Activate Verification, Zero-Pip dependency; toàn bộ 37/37 tests và kiểm tra render tám trạng thái đạt.

---

## Astro Bot Companion — cập nhật 2026-09-06

- `AstroBotCompanion(tk.Frame)` được đặt giữa thống kê ngày và thống kê kho, không chiếm lưới thiết bị.
- Canvas vector 76×52 px mô phỏng Astro Bot với thân trắng, visor đen, mắt LED, ear pods và antenna phát sáng; hoạt hình `after(80)` khoảng 12 FPS.
- Tám trạng thái: chờ cắm máy, sẵn sàng, Restore, reboot, Activate (mắt sao sáng halo tím + lõi trắng, kèm tia lửa điện `spark`), Backup, cảnh báo và ăn mừng hoàn tất.
- Bong bóng thoại hiển thị số máy và tiến độ Restore trung bình; click bot để nhảy nhẹ và luân phiên lời động viên.
- `_resolve_mascot_state()` chọn trạng thái theo operation registry; `_set_mascot_state()` bảo đảm worker nền cập nhật qua UI queue.

---

## ⚡ Nâng cấp Instant Restore & Sửa lỗi Auto Activate — cập nhật 2026-09-05 (Tối)

1. **Khắc phục lỗi chờ 10-15s "Check" trước khi Restore**:
   - Trước đây: `create_restore_stage()` băm SHA-256 3 lần + `copytree` cả thư mục backup (2.8s/máy). 14 máy chạy đồng thời làm nghẽn I/O ổ đĩa nặng nề (~3.2GB dữ liệu đọc/ghi) trước khi phát lệnh restore.
   - Hiện tại: Sử dụng `prepare_restore_in_place()` (giống như `IphoneToolPro_V26.04.26`): chỉ đọc `Status.plist` xác nhận snapshot và ghi UDID đích vào `Info.plist` của bản backup ngay tại kho; nạp trực tiếp từ thư mục kho. Tốc độ chuẩn bị giảm xuống **0.004 giây/máy** (~700 lần nhanh hơn), nạp ngay tức thì.
   - Thêm cơ chế an toàn `rollback_restore_info()`: Lưu bản byte gốc của `Info.plist` trong RAM; nếu restore thất bại thì hoàn tác lại y nguyên UDID gốc, không để lại UDID của máy nạp lỗi.

2. **Sửa lỗi Auto Activate "báo thành công nhưng iPhone không active được"**:
   - Trước đây: Giai đoạn 2 `ios.exe prepare --skip-all` nuốt mọi lỗi (timeout 40s, lỗi `[WinError 2]` thiếu công cụ, lỗi pairing), gán `skip_ok = True` dẫn đến luôn báo thành công ảo. Luồng Auto thiếu tiền kiểm công cụ và mất bước re-pair / chờ lockdownd.
   - Hiện tại:
     - Worker tự tiền kiểm: thiếu `ideviceactivation.exe` hoặc `ios.exe` sẽ dừng và báo đỏ ngay.
     - Xác minh trạng thái thực tế bằng `ideviceactivation state`: nếu thiết bị trả về `Unactivated` / `FactoryActivated` thì báo lỗi, không tin exit code.
     - Báo cáo trung thực (tri-state): `ok` mới báo hoàn tất thành công; `sent` (timeout, đã retry 3 lần) báo vàng cảnh báo; `failed` báo đỏ dừng luồng.
     - Chuẩn bị thiết bị trong luồng Auto (`_auto_activate_launch`): chờ lockdownd phản hồi (tối đa 30s) và xác thực lại pairing `idevicepair validate` trước khi chạy pipeline.
     - Quét USB với `timeout=8` tránh reset bộ đếm khi cắm nhiều máy.

3. **Kiểm thử**: Toàn bộ unit tests đạt **35/35 tests PASS** (0.24s). `py_compile` sạch 100%.

---

## 📍 Đang làm & Tiến độ

* **Phiên bản**: `4.8.3 High-Contrast Store Selection Boxes Edition`
* **Tiến độ**: Toàn bộ hệ thống giao diện và động cơ xử lý USB đa luồng đã hoàn tất:
  - **High-Contrast Store Selection Boxes (Border & Badge Color Refinement)**:
    - **Kho A (Mục Nhập/Xuất)**: Badge cố định màu Xanh lục `#10B981` đặc trưng (`MỤC NHẬP (KHO A)` khi chọn A ➜ B, `MỤC XUẤT (KHO A)` khi chọn B ➜ A). Khi Kho A được chọn làm nguồn thì có **border đậm Xanh lục `#10B981` (2px)**; khi không được chọn thì có **border tối `#3A414F` (1px)** như bản cũ.
    - **Kho B (Mục Xuất/Nhập)**: Badge cố định màu Cam `#F97316` đặc trưng (`MỤC XUẤT (KHO B)` khi chọn A ➜ B, `MỤC NHẬP (KHO B)` khi chọn B ➜ A). Khi Kho B được chọn làm nguồn thì có **border đậm Cam `#F97316` (2px)**; khi không được chọn thì có **border tối `#3A414F` (1px)** như bản cũ.
    - **KHO BACKUP**: Hộp nền trắng `#FFFFFF`, viền ngoài tím `#7C3AED` (2px), badge tím `KHO BACKUP` chữ trắng, đường dẫn chữ đen to đậm `Segoe UI 10 Bold`.
    - **Nhận diện trực quan**: Không còn hiện tượng màu sắc badge bị hoán đổi nhảy loạn; kho nào được chọn sẽ nổi bật với viền sáng đậm màu tương ứng, kho còn lại chìm với viền tối.
    - **Tương tác nhanh**: Nhấp chuột vào bất kỳ vị trí nào trên hộp (badge, khoảng trắng, đường dẫn) đều mở hộp thoại duyệt file (`cursor="hand2"`).
  - **Rounded Gradient Buttons System (`GradientButton`)**: Kế thừa `tk.Canvas` với thuật toán hình học giải tích vẽ các lát cắt dọc 1px bo góc tròn `radius=6px`, gradient đa điểm dừng mượt mà (Emerald, Electric Blue, Sky, Purple), viền sáng tinh tế, hiệu ứng hover sáng và tactile feedback lún 1px khi bấm.
  - **Soft Charcoal Slate Dark Theme System**: Nền Canvas Warm Soft Slate-Charcoal `#1A1D23`, Thẻ/Panel `#22262E`, Sub-panels & Tracks `#262A33`, Terminal Log Console `#1E2229`, Buttons Elevated `#2C313C`, Clean Subtle Borders `#3A414F`, Chữ Slate (`#F8FAFC`, `#E2E8F0`, `#94A3B8`, `#64748B`), Điểm nhấn Electric Blue `#2563EB`, Emerald `#34D399`, Tech Cyan `#38BDF8`.
  - **Windows Segoe MDL2 Assets Icon Font**: Biểu tượng vector hệ thống tích hợp sẵn trên Windows (mã PUA chuẩn: Phone `\uE8EA`, Warning `\uE7BA`, Globe `\uE774`, Gear `\uE713`, Lightning `\uE945`, Folder `\uED25`, Save `\uE74E`, Refresh `\uE72C`, Rocket `\uEB9D`, Clipboard `\uE8C8`, Lightbulb `\uEA80`, Package `\uE7B8`, Check `\uE73E`, Cancel `\uE711`, Key `\uE8D7`, Arrow `\uE72A`).
  - **Giữ vững 100% logic lõi & độ ổn định USB**: Động cơ USB đa luồng, đếm ngược 100s sau Restore, lọc cảnh báo go-ios tunnel, chuông báo hoàn tất đợt đa giác quan.
  - **Zero-pip dependency & Portability**: Ứng dụng chạy hoàn toàn dựa trên thư viện chuẩn Python 3.11 và các công cụ Windows/Apple có sẵn.

---

## ✅ Những gì đã hoàn thành trong phiên làm việc:

1. **Phát triển và tích hợp thành công Rounded Gradient Buttons (`GradientButton`)**:
   - Xây dựng lớp `GradientButton(tk.Canvas)` với thuật toán phân tích hình học giải tích ($dy = r - \sqrt{\max(0, r^2 - dx^2)}$) để render các lát cắt dọc dải màu đa điểm dừng, vẽ đường biên cong và thẳng sắc nét.
   - Hỗ trợ đầy đủ các phương thức `.config()`, `.configure()`, `.cget("text")`, sự kiện `<Enter>`, `<Leave>`, `<ButtonPress-1>`, `<ButtonRelease-1>`.
   - Nâng cấp hai nút bấm trọng tâm: `BATCH ACTIVATE (ALL)` và `BẮT ĐẦU RESTORE PRO` (đổi màu động theo chiều kho A ➜ B / B ➜ A).

2. **Cập nhật hệ màu Soft Charcoal Slate Dark Theme**:
   - Khởi tạo toàn bộ bảng màu chuẩn Soft Charcoal (`COLOR_BG_DARK = "#1A1D23"`, `COLOR_HEADER_BG = "#22262E"`, `COLOR_PANEL_BG = "#22262E"`, `COLOR_SUB_BG = "#262A33"`, `COLOR_CONSOLE_BG = "#1E2229"`, `COLOR_BORDER_LIGHT = "#3A414F"`).
   - Cập nhật đồng bộ các thành phần: Cột thống kê TopBar, Hàng Web App, Bảng Kho hai chiều, Thẻ thiết bị DeviceCard, Thanh tiến trình Gradient Canvas, Cửa sổ nhật ký hệ thống và Thanh trạng thái chân trang.

3. **Duy trì Icon Font chuẩn Windows Segoe MDL2 Assets**:
   - Lớp `Icons` quản lý tập trung toàn bộ mã Private Use Area (PUA).
   - Biểu tượng vector sắc nét ở mọi độ phân giải màn hình.

4. **Kiểm thử toàn diện & Cập nhật bộ nhớ tri thức AI**:
   - `python -m py_compile BB_RB.py` vượt qua không một cảnh báo cú pháp.
   - Toàn bộ bộ kiểm thử tự động `python -m unittest discover -s tests` đạt 24/24 bài test (0.464s - OK).
   - Đồng bộ hóa toàn diện: [CHANGELOG.md](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md), [docs/architecture/system_overview.md](file:///c:/TIKTOOL%20PRO%20V4/docs/architecture/system_overview.md), [.brain/brain.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json), [.brain/session.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json), và [.brain/handover.md](file:///c:/TIKTOOL%20PRO%20V4/.brain/handover.md).

---

## 📁 File quan trọng:
- [BB_RB.py](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py): Mã nguồn chính của ứng dụng (Soft Charcoal Dark Theme + Segoe MDL2 Assets).
- [settings.json](file:///c:/TIKTOOL%20PRO%20V4/settings.json): Cấu hình người dùng và thống kê sản lượng ngày.
- [CHANGELOG.md](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md): Nhật ký thay đổi phiên bản v4.8.1.
- [docs/architecture/system_overview.md](file:///c:/TIKTOOL%20PRO%20V4/docs/architecture/system_overview.md): Tài liệu kiến trúc hệ thống và bảng ánh xạ Design Tokens.
- [TIKTOOL_PRO.pyw](file:///c:/TIKTOOL%20PRO%20V4/TIKTOOL_PRO.pyw): Khởi động app ngầm không hiện console đen.
- [CHAY_TIKTOOL.bat](file:///c:/TIKTOOL%20PRO%20V4/CHAY_TIKTOOL.bat): File batch khởi động tự dò pythonw.
- [notify.wav](file:///c:/TIKTOOL%20PRO%20V4/notify.wav): File chuông báo hoàn tất đợt.
- [.brain/brain.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json): Bộ nhớ tĩnh dự án v4.8.1.
- [.brain/session.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json): Trạng thái phiên làm việc hiện tại.
