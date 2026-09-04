# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-05 01:15:00  
**Phiên bản**: `4.7.1 Web App Link Fix & Portable Launcher Edition`  
**Trạng thái**: Hoàn tất 100% các tính năng: Bố cục trên-dưới nguyên bản, lưới thiết bị co giãn thông minh (3 cột mặc định, 5 cột phóng to), viền đen thẻ thiết bị, loại bỏ khung button đếm máy và hiển thị văn bản thuần "Số thiết bị đang kết nối: X", hệ thống thông báo rút máy cả đợt, sửa lỗi nhập URL Web App tự chọn không bị reset, menu chuột phải Dán tiện lợi, sửa lỗi chạy ngầm TIKTOOL_PRO.pyw qua runpy, và độc lập 100% không cần pip.

---

## 📍 Đang làm & Tiến độ

* **Phiên bản**: `4.7.1 Web App Link Fix & Portable Launcher Edition`
* **Tiến độ**: Toàn bộ hệ thống giao diện và chức năng đã được tối ưu hoàn thiện:
  - Bố cục duy trì cấu trúc Trên - Dưới (Full-width): Khung thiết bị ở trên, Nhật ký hệ thống ở dưới, thanh trạng thái đáy.
  - Lưới thẻ iPhone co giãn mượt mà: Mặc định mở app hiển thị chuẩn **3 thiết bị / 1 hàng** (rộng rãi, thông số ECID/Model to rõ), khi phóng to tối đa Full HD hiển thị **5 thiết bị / 1 hàng**.
  - Viền thẻ iPhone chuyển sang màu đen sắc nét (`#000000`).
  - Tiêu đề "NHẬT KÝ HỆ THỐNG" căn sát lề trái thanh console.
  - Thông tin "Số thiết bị đang kết nối: X" đặt ở lề phải thanh console dưới dạng text thuần font đậm (`Segoe UI 10 bold`, màu `#0A2B17`), bỏ hoàn toàn dạng button/pill frame.
  - Xóa bỏ ô đếm thiết bị thừa ở thanh trên, đưa cụm `Tổng: X (Hôm nay) ↺` sang lề trái tạo sự cân đối, thoáng đãng.
  - Thông báo hoàn tất cả đợt khi tắt Auto Activate (chuông `notify.wav` + nháy Taskbar cam `FlashWindow` + banner vàng cam trong log).
  - **Sửa triệt để lỗi link Web App**: URL nhập vào được giữ nguyên vĩnh viễn, không bị vòng lặp 1s sync loop giật lùi về `https://linkm.site/`.
  - **Menu chuột phải trực quan**: Nhấp chuột phải vào ô link Web App hay ô tên để Cắt, Sao chép, Dán (Paste) cực nhanh.
  - **Khởi động 1 chạm không cửa sổ đen**: `TIKTOOL_PRO.pyw` được refactor bằng `runpy.run_path`, nạp đúng `__file__`, chạy ngay lập tức.
  - **Khả năng cài đặt sang máy tính khác (Zero-Pip)**: Ứng dụng dùng 100% Python Standard Library, không cần `pip install`. Chỉ cần Python 64-bit + iTunes/3uTools là chạy được ngay trên bất kỳ máy Windows nào.

---

## ✅ Những gì đã hoàn thành:

1. **Khắc phục lỗi dán Link Web App bị nhảy về mặc định**:
   - Thêm cờ nạp khởi động `_webclip_link_loaded`: Chỉ nạp URL từ `settings.json` đúng 1 lần khi app vừa khởi động.
   - Vòng lặp `_start_json_sync_loop` mỗi 1 giây không còn ghi đè vào `var_custom_webclip_link`, bảo vệ tuyệt đối chuỗi người dùng đang gõ/dán.
   - Bổ sung `_bind_context_menu()` hỗ trợ menu chuột phải Cut / Copy / Paste / Select All cho các ô nhập liệu `Entry`.

2. **Khắc phục lỗi khởi động của `TIKTOOL_PRO.pyw`**:
   - Chuyển cơ chế nạp từ `exec()` sang `runpy.run_path(target, run_name="__main__")`.
   - Cung cấp biến `__file__` đầy đủ cho `BB_RB.py` (`BASE_DIR = os.path.dirname(...)`), loại bỏ lỗi văng ngầm `NameError: name '__file__' is not defined`.
   - Cập nhật file batch `CHAY_TIKTOOL.bat` tự động phát hiện `pythonw` linh hoạt.

3. **Hướng dẫn di chuyển ứng dụng sang máy tính khác**:
   - Làm rõ điều kiện cần: Python 3.10/3.11 64-bit (chọn Add to PATH) + iTunes x64 hoặc 3uTools (lấy Apple Driver).
   - Xác nhận code không có bất kỳ pip dependencies nào và hàm bản quyền `_require_license` luôn trả về `True` (không khóa cứng phần cứng).

4. **Lưới thẻ thiết bị Responsive Grid & Giao diện chuẩn**:
   - Cửa sổ chuẩn (< 1550px) chia đúng 3 cột; phóng to (1550px - 2100px) chia 5 cột; màn hình siêu rộng (>= 2100px) chia 6 cột.
   - Xóa ràng buộc uniform cũ bằng `uniform=""` trong Tkinter, loại bỏ hiện tượng méo/dẹp thẻ.
   - Viền thẻ `DeviceCard` màu đen sắc nét (`#000000`).
   - Tiêu đề `NHẬT KÝ HỆ THỐNG` căn lề trái; `Số thiết bị đang kết nối: X` căn lề phải dạng text thuần.

5. **Hệ thống cảnh báo rút máy cả đợt**:
   - Chỉ kích hoạt khi toàn bộ máy trong đợt hoàn tất (`len(self.active_restores) == 0`).
   - File âm thanh `notify.wav` tích hợp trực tiếp, miễn nhiễm với chế độ `No Sounds` của Windows.
   - Nhấp nháy Taskbar `FlashWindow` màu vàng cam nhận biết ngay khi tắt loa máy tính.

---

## 🔧 Quyết định kỹ thuật quan trọng:
- **One-time UI Setting Load Flag (`_webclip_link_loaded`)**: Ngăn vòng lặp nền ghi đè các trường input mà người dùng đang thao tác nhập liệu.
- **Tkinter Context Menu (`_bind_context_menu`)**: Tạo popup menu chuột phải riêng cho `tk.Entry` để hỗ trợ thao tác Clipboard quen thuộc trên Windows.
- **`runpy.run_path` for Python Wrappers**: Cách chuẩn nhất trong Python Standard Library để chạy script target với đầy đủ môi trường runtime (`__file__`, `__name__`, globals) mà không cần tạo process cmd.exe.
- **Top-Down Layout Preservation**: Giữ nguyên bố cục Trên - Dưới toàn màn hình theo đúng mong muốn của người dùng.
- **Responsive Threshold (< 1550px = 3 cols, >= 1550px = 5 cols)**: Đảm bảo cửa sổ chuẩn 1300px luôn luôn hiển thị 3 thẻ trên 1 hàng, khi Full HD 1920px hiển thị 5 thẻ.

---

## 📁 File quan trọng:
- [BB_RB.py](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py): Mã nguồn chính của ứng dụng.
- [TIKTOOL_PRO.pyw](file:///c:/TIKTOOL%20PRO%20V4/TIKTOOL_PRO.pyw): Khởi động app dạng silent background window bằng runpy.
- [CHAY_TIKTOOL.bat](file:///c:/TIKTOOL%20PRO%20V4/CHAY_TIKTOOL.bat): File khởi động app tự dò pythonw.
- [notify.wav](file:///c:/TIKTOOL%20PRO%20V4/notify.wav): File âm thanh thông báo êm ái tích hợp trong app.
- [tiktool_core.py](file:///c:/TIKTOOL%20PRO%20V4/tiktool_core.py): Lõi quản lý backup, staging, fingerprint và dọn dẹp thư mục tạm.
- [settings.json](file:///c:/TIKTOOL%20PRO%20V4/settings.json): Cấu hình người dùng và thống kê ngày.
- [CHANGELOG.md](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md): Nhật ký thay đổi phiên bản.
- [docs/architecture/system_overview.md](file:///c:/TIKTOOL%20PRO%20V4/docs/architecture/system_overview.md): Tài liệu kiến trúc hệ thống.
- [.brain/brain.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json): Bộ nhớ tĩnh dự án.
- [.brain/session.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json): Trạng thái phiên làm việc hiện tại.

