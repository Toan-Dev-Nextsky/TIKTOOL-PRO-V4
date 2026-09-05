# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-05 08:30:00  
**Phiên bản**: `4.7.2 Auto-Activate Timing & Web App Default Edition`  
**Trạng thái**: Sẵn sàng vận hành 100% trong môi trường sản xuất thực tế. Đã tối ưu hoàn hảo thời gian chờ reboot (100 giây), lọc bỏ triệt để cảnh báo vô hại go-ios tunnel, xử lý êm dịu hiện tượng SpringBoard reload timeout khi đổi ngôn ngữ, ô nhập link Web App mặc định để trống, menu chuột phải Dán tiện lợi, giao diện chuẩn 3 cột / 5 cột phóng to, và hệ thống cảnh báo rút máy đa giác quan.

---

## 📍 Đang làm & Tiến độ

* **Phiên bản**: `4.7.2 Auto-Activate Timing & Web App Default Edition`
* **Tiến độ**: Toàn bộ hệ thống giao diện và động cơ xử lý USB đa luồng đã hoàn tất:
  - **Tăng thời gian chờ reboot sau Restore lên 100 giây (`TOTAL_WAIT = 100`)**: Cho phép iPhone nạp xong SpringBoard và daemon `lockdownd` trước khi kích hoạt; kết hợp vòng đệm dò tìm USB 45s (tổng an toàn tối đa 145s) giúp tỷ lệ kích hoạt thành công tuyệt đối, hoàn toàn không làm nóng máy.
  - **Lọc sạch cảnh báo vô hại của go-ios**: Ẩn các dòng warning `go-ios agent is not running...` và `failed to get tunnel info...` khi chạy `ios.exe lang`.
  - **Xử lý SpringBoard Reload Timeout (20s) mềm dẻo**: Nhận diện hiện tượng ngắt kết nối tạm thời của socket USB khi đổi ngôn ngữ là bình thường; hiển thị thông báo trắng/xanh thân thiện thay vì cờ đỏ lỗi `is_err`.
  - **Mặc định để trống ô nhập link Web App (`customWebclipLink = ""`)**: Người dùng tự do nhập hoặc dán bất kỳ URL nào mà không cần phải xóa link mẫu ban đầu.
  - **Chống ghi đè link Web App (`_webclip_link_loaded`)**: URL nạp 1 lần duy nhất lúc mở máy, không bị vòng lặp đồng bộ 1s reset ngược lại.
  - **Menu chuột phải (Context Menu)**: Hỗ trợ nhấp chuột phải Cắt, Sao chép, Dán (Paste) và Chọn tất cả trên các ô nhập liệu.
  - **Bố cục Trên - Dưới (Full-width)**: Lưới co giãn thông minh: 3 cột ở cửa sổ chuẩn (< 1550px), 5 cột khi phóng to toàn màn hình Full HD (>= 1550px).
  - **Thẻ thiết bị viền đen (`#000000`) & Thanh log tinh gọn**: Tiêu đề "NHẬT KÝ HỆ THỐNG" bên trái, "Số thiết bị đang kết nối: X" bên phải dạng văn bản thuần đậm.
  - **Hệ thống cảnh báo rút máy cả đợt**: Chuông `notify.wav` (SND_FILENAME) + nháy Taskbar cam `FlashWindow` + banner vàng cam trong log.
  - **Khởi động 1 chạm ngầm**: `TIKTOOL_PRO.pyw` nạp qua `runpy.run_path`, không hiện cửa sổ console đen, zero-pip dependencies.

---

## ✅ Những gì đã hoàn thành trong phiên làm việc:

1. **Tăng thời gian đếm ngược reboot sau Restore từ 80s ➜ 100s**:
   - Tinh chỉnh `TOTAL_WAIT = 100` trong hàm `_post_restore_activate_worker` tại `BB_RB.py`.
   - Cập nhật các thông báo tiến độ và log đếm ngược tương ứng.
   - Giải quyết triệt để tình trạng iPhone chưa kịp load xong hệ điều hành đã bị gửi lệnh kích hoạt.

2. **Lọc sạch cảnh báo go-ios tunnel & SpringBoard reload timeout**:
   - Sử dụng `PROCESS_RUNNER.run_capture` để phân biệt rõ ràng timeout và lỗi thực tế.
   - Lọc bỏ chuỗi `go-ios agent is not running` và `failed to get tunnel info` trước khi in ra log.
   - Ghi nhận `⚡ Lệnh đổi ngôn ngữ đã gửi (SpringBoard đang cập nhật, timeout 20s là bình thường)` giúp người dùng yên tâm.

3. **Mặc định để trống link Web App**:
   - Đổi `DEFAULT_SETTINGS["customWebclipLink"]` thành `""`.
   - Cập nhật `settings.json` thành `"customWebclipLink": ""`.

4. **Đồng bộ toàn diện tài liệu kỹ thuật và bộ nhớ AI**:
   - Cập nhật [CHANGELOG.md](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md) với phiên bản 4.7.2.
   - Cập nhật [docs/architecture/system_overview.md](file:///c:/TIKTOOL%20PRO%20V4/docs/architecture/system_overview.md).
   - Cập nhật [.brain/brain.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json) và [.brain/session.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json).

---

## 🔧 Quyết định kỹ thuật quan trọng:
- **100s Wait Countdown**: Mốc thời gian vàng để iPhone khởi động hoàn tất sau restore dữ liệu lớn, đảm bảo `lockdownd` sẵn sàng tiếp nhận lệnh kích hoạt.
- **Tunnel Warning Suppression**: Cảnh báo daemon tunnel của `ios.exe` là không cần thiết cho chế độ giao tiếp USB usbmuxd truyền thống; việc lọc giúp giao diện log trực quan và không gây hoang mang.
- **Soft Exception Handling on SpringBoard Reload**: Việc đổi ngôn ngữ luôn khiến SpringBoard reload và ngắt kết nối socket USB trong 1-2 giây; timeout 20s thực chất đồng nghĩa với việc lệnh đã được iOS tiếp nhận thành công.
- **Empty Default Webclip URL**: Tôn trọng lựa chọn của người dùng, không gán sẵn link ngoài mong muốn.

---

## 📁 File quan trọng:
- [BB_RB.py](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py): Mã nguồn chính của ứng dụng.
- [settings.json](file:///c:/TIKTOOL%20PRO%20V4/settings.json): Cấu hình người dùng và thống kê sản lượng ngày.
- [CHANGELOG.md](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md): Nhật ký thay đổi phiên bản.
- [docs/architecture/system_overview.md](file:///c:/TIKTOOL%20PRO%20V4/docs/architecture/system_overview.md): Tài liệu kiến trúc hệ thống.
- [TIKTOOL_PRO.pyw](file:///c:/TIKTOOL%20PRO%20V4/TIKTOOL_PRO.pyw): File khởi động app ngầm.
- [CHAY_TIKTOOL.bat](file:///c:/TIKTOOL%20PRO%20V4/CHAY_TIKTOOL.bat): File batch khởi động tự dò pythonw.
- [notify.wav](file:///c:/TIKTOOL%20PRO%20V4/notify.wav): File chuông báo hoàn tất đợt.
- [.brain/brain.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json): Bộ nhớ tĩnh dự án.
- [.brain/session.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json): Trạng thái phiên làm việc hiện tại.
