# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-04 17:47:00  
**Phiên bản**: `4.3.0 Web App & Soft Mint Edition`  
**Trạng thái**: Hoàn tất 100% tính năng Tạo Web App, tích hợp icon toàn năng siêu đẹp webapp.png, xóa checkbox can thiệp backup nguy hiểm.

---

## 📍 Đang làm & Tiến độ

* **Phiên bản**: `4.3.0 Web App & Soft Mint Edition`
* **Tiến độ**: Đã tích hợp đầy đủ tính năng tạo shortcut Web App ra màn hình iPhone từ `C:\iphone_tool_v2`, trang bị icon 3D Glassmorphic toàn năng cho mọi link web, xóa bỏ ô can thiệp backup nguy hiểm, hoàn thiện bảng màu Soft Mint dịu mắt.

---

## ✅ Những gì đã hoàn thành:

1. **Tạo Web App / WebClip Profile Shortcut ra màn hình iPhone**:
   - Nghiên cứu cơ chế cấu hình của Apple từ `C:\iphone_tool_v2`: định dạng XML `.mobileconfig` với payload `com.apple.webClip.managed`.
   - Nạp tự động vào thiết bị qua lệnh `ios.exe profile add <path> --udid=<udid> --nojson`.
   - **Tích hợp Icon Toàn Năng Siêu Đẹp (`webapp.png`)**: Thiết kế 3D Glassmorphic Holographic Globe & Link chuẩn HD 512×512, dùng làm icon mặc định cho bất kỳ website nào được nhập vào (như `https://linkm.site/`), không còn bị icon xám mặc định của Safari.
   - Hỗ trợ các icon chuyên biệt tự động: TikTok (`tiktok.png`), TikTok Lite (`tiktok_lite.png`), 2FA (`2FA.png`), Fun (`fun.png`).
   - Tự động chuẩn hóa link web, trích xuất hostname làm nhãn app.
   - Thêm Hàng 3 trong `top_card`:
     - Ô **Nhập link web** (mặc định sẵn `https://linkm.site/`), lưu tự động vào `settings.json`.
     - Nút **[🚀 Tạo Web App]**: Gửi shortcut tới toàn bộ iPhone đang kết nối.
     - 2 Nút phím tắt nhanh: **[📱 TikTok - AppStore]** và **[⚡ TikTok Lite - AppStore]**.
   - Chạy trên tiểu trình nền (`threading.Thread`), không gây đơ giật giao diện; cập nhật tiến trình trên từng thẻ thiết bị và hiển thị thông báo kết quả.

2. **Xóa Bỏ Checkbox Can Thiệp Backup Nguy Hiểm**:
   - Loại bỏ hoàn toàn ô `Can thiệp ngôn ngữ vào file Backup trước khi Restore` khỏi UI để giao diện gọn gàng và bảo vệ file backup gốc nguyên vẹn 100%.
   - Sử dụng quy trình đổi ngôn ngữ chuẩn qua lệnh chính thức `ios.exe lang` tự động sau khi restore, an toàn tuyệt đối.

3. **Bảng màu Soft Mint & Loại bỏ màu Cam Đỏ Nguy Hiểm**:
   - Loại bỏ màu cam đỏ (#EA580C, #D97706) khi đảo kho B ➜ A và trên thẻ "Còn lại".
   - Chuẩn hóa toàn bộ sang tông màu Xanh Ngọc Emerald (`#059669`) và Xanh Biển Sky Blue (`#0284C7`), đồng bộ hài hòa với nền Mint-Sage dịu mắt.

3. **Thanh tiến trình Gradient hiện đại (`GradientProgressBar`)**:
   - Dải màu chuyển tiếp từ Cyan (`#06B6D4`) sang Electric Blue (`#2563EB`).
   - Rãnh nền xám mint nhạt (`#D5E8DD`).
   - Text trạng thái và số % được dời lên phía trên thanh bar, không bao giờ bị cắt chữ.

4. **Cơ chế Cảnh báo An Toàn khi bấm nút [X] (`WM_DELETE_WINDOW`)**:
   - Tự động theo dõi luồng Restore, Backup, Activate; cảnh báo nguy cơ Treo Táo / Hỏng Backup nếu người dùng bấm đóng ứng dụng khi có máy đang chạy.

5. **Lưu bền vững lựa chọn Kho A/B (Persistence Fix)**:
   - Đọc và ghi đồng bộ `settings.json` ngay từ đầu, giữ nguyên kho A/B khi mở lại app.

6. **Tự động Activate sau Restore**:
   - Đếm ngược 80 giây cho iPhone khởi động xong rồi tự động chạy Batch Activate 3 giai đoạn.

---

## 🔧 Quyết định kỹ thuật quan trọng:
- **Apple Configuration Profile (`com.apple.webClip.managed`)**: Phương pháp chuẩn của Apple để đưa web app ra màn hình chính, mở toàn màn hình (PWA) mà không cần cài thêm app phụ trợ.
- **Background Threading cho Web App Push**: Đẩy cấu hình đồng loạt tới hàng chục máy qua cổng USB mà không làm đông cứng giao diện Tkinter.
- **Canvas-based Gradient Progress Bar**: Dùng Canvas vẽ dải màu thay vì ttk.Progressbar đơn sắc thô cứng.
- **Protocol WM_DELETE_WINDOW**: Bảo vệ thiết bị tránh bị brick / treo táo do ngắt ngang tiến trình restore.

---

## 📁 File quan trọng:
- [BB_RB.py](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py): Mã nguồn chính của ứng dụng.
- [settings.json](file:///c:/TIKTOOL%20PRO%20V4/settings.json): File lưu trữ cấu hình người dùng (đã bổ sung `customWebclipLink`).
- [tiktok.png](file:///c:/TIKTOOL%20PRO%20V4/tiktok.png), [tiktok_lite.png](file:///c:/TIKTOOL%20PRO%20V4/tiktok_lite.png), [fun.png](file:///c:/TIKTOOL%20PRO%20V4/fun.png), [2FA.png](file:///c:/TIKTOOL%20PRO%20V4/2FA.png): Bộ icon tài nguyên cho Web App.
- [.brain/brain.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json): Bộ nhớ tĩnh kiến trúc dự án.
- [.brain/session.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json): Lịch sử phiên làm việc.
- [docs/architecture/system_overview.md](file:///c:/TIKTOOL%20PRO%20V4/docs/architecture/system_overview.md): Tài liệu kiến trúc hệ thống.
- [CHANGELOG.md](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md): Nhật ký thay đổi.

