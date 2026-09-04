# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-04 21:45:00  
**Phiên bản**: `4.5.0 Modern Light Dashboard & Clean Staging Edition`  
**Trạng thái**: Hoàn tất 100% việc tối ưu giao diện Modern Light Dashboard siêu gọn, bổ sung bộ đếm thống kê restore theo ngày, kiểm tra chuẩn hóa restore flow và tự động dọn sạch thư mục tạm `.tiktool_work`.

---

## 📍 Đang làm & Tiến độ

* **Phiên bản**: `4.5.0 Modern Light Dashboard & Clean Staging Edition`
* **Tiến độ**: Ứng dụng hoạt động ổn định, mượt mà, phản hồi tức thì. Giao diện sáng thanh lịch (Modern Light Dashboard), bố cục siêu gọn gàng, thanh trạng thái đáy tối giản, thẻ máy sạch sẽ không còn nút thừa, bộ đếm restore theo ngày lưu tự động vào `settings.json`, quy trình restore chuẩn chỉ và thư mục staging được xóa sạch sẽ không để lại dấu vết.

---

## ✅ Những gì đã hoàn thành trong phiên làm việc:

1. **Chuyển đổi giao diện sang Modern Light Dashboard**:
   - Chuyển toàn bộ ứng dụng sang phong cách Modern Light: nền Slate-100 (`#F8FAFC`), card trắng tinh (`#FFFFFF`), viền Slate-200 (`#E2E8F0`), điểm nhấn Soft Indigo (`#4F46E5`, `#6366F1`) và Emerald (`#10B981`).
   - Thu gọn toàn bộ cụm điều khiển phía trên (Top Card): Logo, Đổi ngôn ngữ, Batch Activate, Tạo Web App thành các hàng siêu ngắn gọn, tiết kiệm diện tích màn hình tối đa.
   - Thay thế các nút hộp màu thô to ở thanh trạng thái đáy (`Trust`, `Tổng`, `Not Trust`, `Restored`) thành chuỗi text thanh mảnh, tinh tế, ngăn cách bằng vạch ` | `.
   - Xóa bỏ 2 nút đơn lẻ `Lang` và `Active` trên từng thẻ máy `DeviceCard`, giúp card nhỏ gọn, tăng khoảng trống cho danh sách thiết bị.

2. **Thống kê số lượng máy đã Restore trong ngày (Daily Restore Counter)**:
   - Bổ sung nhãn `Hôm nay: X` với phong cách Soft Indigo trên thanh tiêu đề thiết bị (`dev_title_bar`).
   - Lưu trữ bền vững vào `settings.json` (`dailyRestoreDate`, `dailyRestoreCount`).
   - Tự động kiểm tra và reset về 0 khi bắt đầu ngày mới.

3. **Kiểm tra chuẩn hóa Restore Logic**:
   - Kiểm tra kỹ câu lệnh gọi `idevicebackup2`:
     ```powershell
     idevicebackup2 -u <udid> -s <src_name> restore <base_dir> --settings --remove
     ```
   - Quy trình Staging an toàn: Sao chép đọc-chỉ từ backup gốc, patch UDID vào `Info.plist` của bản staging, xác thực fingerprint toàn vẹn, hoàn tất restore thì di chuyển thư mục sang kho đối diện (`transfer_backup_immutable`).

4. **Khắc phục và tự động dọn dẹp thư mục `.tiktool_work`**:
   - Bản chất: Là thư mục workspace tạm để tạo bản copy staging restore tránh làm hỏng backup gốc.
   - Sửa hàm `cleanup_owned_job` trong `tiktool_core.py`: Tự động kiểm tra và xóa bỏ luôn thư mục cha `.tiktool_work` sau khi hoàn thành restore nếu nó rỗng.
   - Đã quét và dọn sạch folder `.tiktool_work` tồn dư trong kho `D:\TKBAND DONG MOI 3.9 A`.

---

## 🔧 Quyết định kỹ thuật quan trọng:
- **Clean Staging Persistence**: Giữ staging trên cùng ổ đĩa với kho dữ liệu để tận dụng tốc độ di chuyển cực nhanh (`os.rename`), nhưng tự động xóa sạch thư mục cha `.tiktool_work` để giao diện Explorer của người dùng luôn sạch sẽ 100%.
- **Inline Text Status Bar**: Chuyển các nút trạng thái đáy thành chuỗi text ngắn gọn để loại bỏ hoàn toàn cảm giác thô cứng, tiết kiệm chiều cao cho vùng làm việc chính.
- **Batch-Oriented Device Card**: Xóa bỏ các nút bấm đơn lẻ trên từng card máy vì người dùng vận hành số lượng lớn thiết bị theo lô thông qua thanh điều khiển phía trên.
- **Daily Counter Mechanism**: Dùng định dạng `YYYY-MM-DD` so sánh ngày hiện tại; nếu khác thì reset bộ đếm về 0, giúp người dùng theo dõi sản lượng từng ngày chính xác mà không cần bấm nút reset thủ công.

---

## 📁 File quan trọng:
- [BB_RB.py](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py): Mã nguồn chính của ứng dụng.
- [tiktool_core.py](file:///c:/TIKTOOL%20PRO%20V4/tiktool_core.py): Lõi quản lý backup, staging, fingerprint và dọn dẹp thư mục tạm.
- [settings.json](file:///c:/TIKTOOL%20PRO%20V4/settings.json): Cấu hình người dùng (kho, ngôn ngữ, link web, bộ đếm ngày).
- [CHANGELOG.md](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md): Nhật ký thay đổi phiên bản.
- [docs/architecture/system_overview.md](file:///c:/TIKTOOL%20PRO%20V4/docs/architecture/system_overview.md): Tài liệu kiến trúc hệ thống cập nhật.
- [.brain/brain.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json): Bộ nhớ tĩnh dự án.
- [.brain/session.json](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json): Trạng thái phiên làm việc hiện tại.
