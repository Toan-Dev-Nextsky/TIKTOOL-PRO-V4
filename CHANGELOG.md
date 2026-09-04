# Nhật Ký Thay Đổi (Changelog) - BB MANAGER PRO

Tất cả những thay đổi và nâng cấp quan trọng của dự án được ghi nhận đầy đủ tại đây.

---

## [4.0.0 Pro Dark Edition] - 2026-09-04

### 🚀 Tính Năng Mới (Added)
- **Cụm Thống Kê Chuyển Kho Thời Gian Thực**:
  - Thẻ `TỔNG KHO 📁`: Tổng số lượng bản backup trong kho đang thao tác.
  - Thẻ `ĐÃ CHUYỂN 📁`: Số lượng thiết bị iPhone đã restore và di chuyển qua kho đích thành công.
  - Thẻ `CÒN LẠI`: Số lượng bản backup còn lại thực tế trong thư mục kho nguồn.
  - Tích hợp nút `↺` để reset nhanh bộ đếm đã chuyển về 0 khi bắt đầu ca mới.
- **Tính Năng Chọn Kho Nguồn & Chuyển Kho Hai Chiều**:
  - Hỗ trợ đảo chiều linh hoạt giữa `Kho A ➜ B` và `Kho B ➜ A`.
  - Tự động hiển thị và đồng bộ hóa số lượng backup có sẵn trong từng kho.
  - Tự động cập nhật nhãn `MỤC NHẬP` (kho nguồn) và `MỤC XUẤT` (kho đích) theo màu sắc neon trực quan.
- **Tính Năng Batch Activate 3 Giai Đoạn**:
  - Tích hợp đầy đủ quy trình: Kích hoạt Apple Server (`ideviceactivation`) ➜ Bỏ qua Setup Assistant (`ios.exe prepare --skip-all`) ➜ Cài đặt ngôn ngữ/locale (`ios.exe lang`).
  - Hỗ trợ popup trực quan chọn ngôn ngữ/locale có sẵn hoặc tự nhập tùy chỉnh (`open_lang_popup`).
- **Bộ Nhớ Dự Án Dài Hạn (`.brain/`)**:
  - Khởi tạo `.brain/brain.json` lưu trữ kiến thức tĩnh, kiến trúc, quy ước và bài học kinh nghiệm.
  - Khởi tạo `.brain/session.json` lưu trữ trạng thái phiên làm việc và lịch sử quyết định kỹ thuật.
  - Tạo tài liệu kiến trúc hệ thống chi tiết tại `docs/architecture/system_overview.md`.

### 🎨 Cải Tiến Giao Diện & Trải Nghiệm (Changed & UI/UX)
- **Thiết Kế Lại Toàn Diện Theo `ui-ux-pro-max-skill` (High-Contrast Pro Dark)**:
  - Thay thế toàn bộ nền trắng chói bằng bảng màu tối kỹ thuật cao cấp: Deep Midnight Slate (`#0B0F19`), Elevated Navy Slate (`#151E2E`), Dark Inset Well (`#0D1524`), và viền Crisp Slate (`#2D3B54`).
  - Chữ chính đạt độ tương phản 100% Trắng sáng (`#F8FAFC`) dễ đọc, không gây mỏi mắt.
- **Ưu Tiên Bộ Đếm Kho & Thu Gọn Số Thiết Bị**:
  - Chuyển số thiết bị kết nối thành một Pill Badge nhỏ gọn `[ X máy ]` nằm cạnh tiêu đề `THIẾT BỊ KẾT NỐI`, loại bỏ thẻ card to chiếm diện tích.
  - Mở rộng kích thước và độ nổi bật cho 3 thẻ bộ đếm kho (`TỔNG KHO`, `ĐÃ CHUYỂN`, `CÒN LẠI`).
- **Tối Ưu Thẻ Thiết Bị (DeviceCard) Siêu Nhỏ Gọn**:
  - Giảm chiều cao thẻ từ 125px xuống ~80px (tiết kiệm ~40% diện tích dọc).
  - Loại bỏ các dòng trống không cần thiết (`IMEI: —  SN: —`), gộp `Model` và `ECID` vào 1 dòng.
  - Đưa nút `[🌐 Lang]` và `[⚡ Active]` lên góc phải hàng tiêu đề từng thẻ.
  - Bỏ ép cứng `height=125` trong hàm bố cục lưới `_relayout_cards_3x4`.
- **Sửa Lỗi Nút Bấm Restore**:
  - Rút gọn nhãn nút bấm thành `⚡ BẮT ĐẦU RESTORE PRO (A ➜ B • {count} iPhone)` để không bao giờ bị cắt chữ hay tràn viền trên mọi kích thước màn hình.

### 🐛 Sửa Lỗi & Tối Ưu Hệ Thống (Fixed & Optimized)
- Sửa lỗi `TclError: unknown font style 'semibold'` trên môi trường Windows Tkinter bằng cách chuẩn hóa font tuple sang weight `bold`.
- Khắc phục lỗi mã hóa `cp1252` trên Windows console trong các script kiểm thử tự động bằng cách cấu hình `sys.stdout.reconfigure(encoding='utf-8')`.
- Giữ nguyên cơ chế `RESTORE_LOCK_CACHE` 35 giây ngăn ngừa báo sai trạng thái `Not Trust` khi iPhone tự reboot sau khi restore.
