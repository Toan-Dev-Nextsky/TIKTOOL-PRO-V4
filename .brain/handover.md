# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-10  
**Phiên bản**: `4.9.0 IPA Installer Edition`  
**Trạng thái**: Hoàn thiện Tab CÀI IPA HÀNG LOẠT: quét file .ipa tự động, checkbox chọn lọc từng file, gỡ app cũ trước khi cài, cài song song toàn dàn; 54/54 unit tests PASS.

---

## 🌟 Tái thiết kế Thẻ Hiệu Suất Sinh Động & Tối ưu viền — cập nhật 2026-09-09

Tích hợp bản thiết kế từ `stitch_modern_animated_redesign` và tinh chỉnh chi tiết theo phản hồi thực tế của người dùng:

1. **Giao diện Navy & Cyan hiện đại (`performance_card_theme`)**:
   - Thẻ sử dụng nền Navy sâu `#0F172A`, kết hợp viền ngoài cyan 1px `#0E7490` với hiệu ứng hover glow `#38BDF8`.
   - Viền ngoài giúp thẻ tách biệt rõ ràng, không bị chìm vào nền Soft Charcoal `#1A1D23` của app.

2. **Đèn chỉ báo trực tiếp nhịp thở (Live Pulse Dot Indicator)**:
   - Thêm `self.perf_dot` bằng Canvas vector 5×5 px đặt cạnh tiêu đề "HIỆU SUẤT".
   - Chu kỳ hoạt ảnh nhịp thở 850ms luân phiên đổi màu giữa cyan sáng `#38BDF8` và cyan đậm `#0284C7`.
   - Trực quan hóa tiến trình hệ thống đang chạy thời gian thực, không gây tốn tài nguyên hay giật lag.

3. **Hộp số sản lượng hôm nay & Tối ưu hóa không gian**:
   - Khung giờ linh hoạt (`lbl_stat_hour_window`) nền `#083344` chữ cyan `#38BDF8`, thiết kế không viền sạch sẽ.
   - Hộp số hôm nay (`daily_value_box`): đóng khung viền vàng hổ phách 1px `#FACC15` trên nền tối `#2C2508`, chữ số to đậm `Segoe UI 14 Bold` màu `#FACC15`, kèm hiệu ứng hover glow viền chuyển `#FDE047`.
   - Nút Chi tiết (`lbl_stat_action`) và nút Refresh (`lbl_stat_refresh`) được bỏ viền thừa, có hiệu ứng đổi màu hover rõ nét.

4. **Hệ thống đánh giá sao hiệu suất (`performance_star_glow_profile`)**:
   - 5 sao: sparkle lấp lánh vàng nhạt/vàng sáng (`#FFF7C2` / `#FDE68A`).
   - 4 sao: glow vàng hổ phách (`#FDE68A` / `#FACC15`).
   - Nền badge sao giữ trong suốt (khớp màu surface thẻ `#0F172A`) với `border_width = 0`.

5. **Bảo toàn cấu trúc & Kiểm thử tự động**:
   - Thẻ `DeviceCard` bảo đảm thừa kế trực tiếp từ `tk.Frame` với viền chữ nhật chuẩn.
   - Thêm 5 unit test chuyên sâu; toàn bộ **54/54 tests PASS** (0.297s), `py_compile` sạch 100%.

---

## ⏱ Tối ưu thời gian Batch Activate — cập nhật 2026-09-08

Vấn đề: Batch Activate chậm. Thay vì đoán, thêm log `⏱` đo thời gian từng giai đoạn rồi chạy 6 đợt thật trên dàn 10 máy.

**Thay đổi duy nhất áp dụng**: Giảm timeout `ios lang` **20s → 15s**.
- 20s (bản gốc): lệnh luôn hết timeout do SpringBoard reload → 20s chết/máy.
- 8s: có máy vẫn tiếng Anh (cắt trước khi iPhone nhận lệnh).
- 15s: cân bằng — máy nhận lệnh, tiết kiệm ~5s/máy.

**Thử và loại bỏ**:
- Giảm `ACTIVATE_SEMAPHORE` 32→16: `Chờ slot = 0.0s` ở mọi đợt → semaphore không phải bottleneck; giảm làm tệ hơn (Skip Setup timeout tăng, 2 máy `sent`).
- Bỏ retry Skip Setup khi timeout: gây hồi quy "báo hoàn thành nhưng máy chưa active" → retry là cơ chế chính, giữ nguyên.

**Giữ nguyên**: timeout 40s Skip Setup, retry ×3, xác minh state 2 lần, semaphore 32, `AUTO_ACTIVATE_SETTLE_SECONDS = 100`.

**Nhật ký `⏱`** (giữ lại): 8 mốc đo thời gian — chờ slot, GĐ1 Activate, xác minh state, GĐ2 Skip Setup (kèm kết quả), GĐ3 Set Language, xác minh state lần cuối, tổng mỗi máy, USB ổn định Auto Activate.

---

## Astro Bot Companion — cập nhật 2026-09-06

- `AstroBotCompanion(tk.Frame)` được đặt giữa thống kê ngày và thống kê kho, không chiếm lưới thiết bị.
- Canvas vector 76×52 px mô phỏng Astro Bot với thân trắng, visor đen, mắt LED, ear pods và antenna phát sáng; hoạt hình `after(80)` khoảng 12 FPS.
- Tám trạng thái: chờ cắm máy, sẵn sàng, Restore, reboot, Activate (mắt sao sáng halo tím + lõi trắng, kèm tia lửa điện `spark`), Backup, cảnh báo và ăn mừng hoàn tất.
- Bong bóng thoại hiển thị số máy và tiến độ Restore trung bình; click bot để nhảy nhẹ và luân phiên lời động viên.
- `_resolve_mascot_state()` chọn trạng thái theo operation registry; `_set_mascot_state()` bảo đảm worker nền cập nhật qua UI queue.

---

## ⚡ Nâng cấp Instant Restore & Sửa lỗi Auto Activate — cập nhật 2026-09-05

1. **Khắc phục lỗi chờ 10-15s "Check" trước khi Restore**:
   - Cơ chế `prepare_restore_in_place()`: chỉ đọc `Status.plist` xác nhận snapshot và ghi UDID đích vào `Info.plist` của bản backup ngay tại kho; nạp trực tiếp từ thư mục kho. Tốc độ chuẩn bị giảm xuống **0.004 giây/máy** (~700 lần nhanh hơn), nạp ngay tức thì.
   - Thêm cơ chế an toàn `rollback_restore_info()`: Lưu bản byte gốc của `Info.plist` trong RAM; nếu restore thất bại thì hoàn tác lại y nguyên UDID gốc, không để lại UDID của máy nạp lỗi.

2. **Sửa lỗi Auto Activate "báo thành công nhưng iPhone không active được"**:
   - Worker tự tiền kiểm: thiếu `ideviceactivation.exe` hoặc `ios.exe` sẽ dừng và báo đỏ ngay.
   - Xác minh trạng thái thực tế bằng `ideviceactivation state`: nếu thiết bị trả về `Unactivated` / `FactoryActivated` thì báo lỗi, không tin exit code.
   - Báo cáo trung thực (tri-state): `ok` mới báo hoàn tất thành công; `sent` (timeout, đã retry 3 lần) báo vàng cảnh báo; `failed` báo đỏ dừng luồng.
   - Chuẩn bị thiết bị trong luồng Auto (`_auto_activate_launch`): chờ lockdownd phản hồi (tối đa 30s) và xác thực lại pairing `idevicepair validate` trước khi chạy pipeline.
   - Quét USB với `timeout=8` tránh reset bộ đếm khi cắm nhiều máy.

---

## 📍 Đang làm & Tiến độ

* **Phiên bản**: `4.8.8 Modern Animated Performance Widget Edition`
* **Tiến độ**: Toàn bộ hệ thống giao diện và động cơ xử lý USB đa luồng đã hoàn tất:
  - **Modern Animated Performance Card**: Thẻ Navy `#0F172A` viền `#0E7490` (hover `#38BDF8`), Canvas breathing dot 5×5 nhịp thở 850ms, hộp số sản lượng hôm nay vàng hổ phách `#FACC15` 14pt bold (hover `#FDE047`), đánh giá sao sparkle/glow.
  - **Astro Bot Companion**: Linh vật Canvas vector hoạt hình theo sát 8 trạng thái tác vụ.
  - **High-Contrast Store Selection Boxes**: Kho A badge xanh lục `#10B981`, Kho B badge cam `#F97316`, Kho Backup badge tím `#7C3AED`; kho được chọn viền 2px tương ứng, kho không chọn viền tối `#3A414F`.
  - **Rounded Gradient Buttons System (`GradientButton`)**: Kế thừa `tk.Canvas` với giải thuật lát cắt 1px bo tròn radius 6px, gradient đa điểm dừng, viền sáng tinh tế, hover sáng và tactile feedback lún 1px.
  - **Soft Charcoal Slate Dark Theme**: Nền Canvas Warm Soft Slate-Charcoal `#1A1D23`, Panels `#22262E`, Sub-panels & Tracks `#262A33`, Terminal Console `#1E2229`.
  - **Windows Segoe MDL2 Assets Icon Font**: Biểu tượng vector hệ thống tích hợp sẵn trên Windows (mã PUA chuẩn).
  - **Zero-pip dependency & Portability**: 100% Python Standard Library, không cài thêm bất kỳ gói ngoài nào.

---

## ✅ Những gì đã hoàn thành trong phiên làm việc:

1. **Tích hợp giao diện Modern Animated Performance Widget**:
   - Chuyển `card_daily` sang bảng màu Navy & Cyan: nền `#0F172A`, viền ngoài cyan 1px `#0E7490` với hover glow `#38BDF8`.
   - Tạo đèn chỉ báo trực tiếp dạng nhịp thở `self.perf_dot` (5×5 px) nhấp nháy chuyển màu giữa cyan sáng `#38BDF8` và cyan đậm `#0284C7` mỗi 850ms.
   - Thêm hộp số sản lượng hôm nay `daily_value_box` viền vàng hổ phách 1px `#FACC15`, chữ to đậm `Segoe UI 14 Bold` màu `#FACC15`, kèm hover glow `#FDE047`.
   - Cập nhật hệ thống đánh giá sao sparkle/glow với nền badge trong suốt.
   - Bỏ các viền thừa bên trong ở khung giờ và nút bấm để tối ưu hóa không gian.

2. **Kiểm thử tự động & Tính toàn vẹn**:
   - Bổ sung 5 unit tests mới trong `tests/test_app_workflows.py`.
   - Chạy kiểm thử tự động đạt **54/54 tests PASS** (0.297s).
   - `python -m py_compile BB_RB.py` hoàn toàn sạch cú pháp.

3. **Cập nhật bộ nhớ tri thức AI**:
   - Đồng bộ hóa toàn diện: [CHANGELOG.md](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md), [docs/architecture/system_overview.md](file:///c:/TIKTOOL%20PRO%20V4/docs/architecture/system_overview.md), [.brain/brain.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json), [.brain/session.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json), và [.brain/handover.md](file:///c:/TIKTOOL%20PRO%20V4/.brain/handover.md).

---

## 📁 File quan trọng:
- [BB_RB.py](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py): Mã nguồn chính của ứng dụng (Soft Charcoal Dark Theme + Segoe MDL2 Assets + Thẻ Hiệu Suất Sinh Động).
- [settings.json](file:///c:/TIKTOOL%20PRO%20V4/settings.json): Cấu hình người dùng và thống kê sản lượng ngày.
- [CHANGELOG.md](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md): Nhật ký thay đổi phiên bản v4.8.8.
- [docs/architecture/system_overview.md](file:///c:/TIKTOOL%20PRO%20V4/docs/architecture/system_overview.md): Tài liệu kiến trúc hệ thống và bảng ánh xạ Design Tokens.
- [TIKTOOL_PRO.pyw](file:///c:/TIKTOOL%20PRO%20V4/TIKTOOL_PRO.pyw): Khởi động app ngầm không hiện console đen.
- [CHAY_TIKTOOL.bat](file:///c:/TIKTOOL%20PRO%20V4/CHAY_TIKTOOL.bat): File batch khởi động tự dò pythonw.
- [notify.wav](file:///c:/TIKTOOL%20PRO%20V4/notify.wav): File chuông báo hoàn tất đợt.
- [.brain/brain.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json): Bộ nhớ tĩnh dự án v4.8.8.
- [.brain/session.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json): Trạng thái phiên làm việc hiện tại.
- [.brain/handover.md](file:///c:/TIKTOOL%20PRO%20V4/.brain/handover.md): Tài liệu bàn giao tiến độ.
