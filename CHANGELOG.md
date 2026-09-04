# Nhật Ký Thay Đổi (Changelog) - BB MANAGER PRO

Tất cả những thay đổi và nâng cấp quan trọng của dự án được ghi nhận đầy đủ tại đây.

---

## [4.4.0 Stability & Immutable Backup Edition] - 2026-09-04

### An toàn dữ liệu
- Restore luôn chạy từ một bản sao staging; không sửa, thêm hoặc xóa file bên trong backup nguồn.
- Chỉ chuyển nguyên thư mục backup sau khi restore thành công và fingerprint toàn bộ cây file vẫn khớp.
- Backup mới chạy trong job riêng, nên lỗi giữa chừng không thể xóa hoặc ghi đè backup cũ trùng UDID.
- Validation yêu cầu `Status.plist` hợp lệ ở trạng thái `Finished`; không tự tổng hợp metadata thiếu.

### Ổn định vận hành
- Giới hạn đồng thời lấy từ `apps_config.json`, mặc định 4 và chặn thao tác trùng trên cùng UDID.
- Mọi lệnh ngoài có timeout, được theo dõi và có thể dừng khi đóng ứng dụng.
- Worker cập nhật giao diện qua queue; polling metadata chạy nền, coalesce kết quả và giữ card khi máy reboot.
- Batch Activate chỉ báo thành công khi Activate, Skip Setup và bước Language tùy chọn đều thành công.
- Sửa WebClip khi không có thiết bị, giữ HTTPS, kiểm tra license theo máy và ghi log bền vững có che khóa.

### Kiểm thử
- Bổ sung 24 regression test cho tính bất biến backup, chuyển kho, timeout tiến trình, registry, reboot, cấu hình, license, pipeline và WebClip.

---

## [4.3.0 Web App & Soft Mint Edition] - 2026-09-04

### 🚀 Tính Năng Mới (Added)
- **Tạo Web App / Shortcut Link Tắt Ra Màn Hình iPhone (`create_custom_webclip_all`)**:
  - Tự động sinh Apple Configuration Profile (`.mobileconfig`) với Payload Type `com.apple.webClip.managed`.
  - Tự động nạp profile qua lệnh `ios.exe profile add <path> --udid=<udid> --nojson` nạp trực tiếp qua cổng USB.
  - Sau khi nạp, trên iPhone bấm Install để icon link tắt hiển thị ngay ngoài màn hình chính, truy cập tức thì.
- **Hàng 3 Điều Khiển Web App Trong Top Card**:
  - **Nhập link web**: Ô nhập link trực quan, mặc định sẵn `https://linkm.site/`, đồng bộ lưu trong `settings.json`.
  - **Nút [🚀 Tạo Web App]**: Đẩy link tắt tới toàn bộ thiết bị đang kết nối cùng lúc.
  - **Nút [📱 TikTok - AppStore]**: Phím tắt tạo shortcut mở cài TikTok trên AppStore.
  - **Nút [⚡ TikTok Lite - AppStore]**: Phím tắt tạo shortcut mở cài TikTok Lite trên AppStore.
- **Bộ Icon Tích Hợp Sẵn & Icon Toàn Năng Siêu Đẹp (`webapp.png`)**:
  - Tích hợp icon `webapp.png` (3D Glassmorphic Holographic Globe & Link) làm icon toàn năng mặc định cho mọi link web bất kỳ (ví dụ `https://linkm.site/`), không còn bị icon Safari xám nhạt ngoài màn hình iPhone.
  - Hỗ trợ các icon chuyên biệt: `tiktok.png`, `tiktok_lite.png`, `fun.png`, `2FA.png`.
- **Xử Lý Nền Đa Luồng An Toàn**:
  - Toàn bộ quá trình đẩy Web App chạy trên `threading.Thread`, cập nhật tiến trình trên thẻ máy và hiển thị hộp thông báo kết quả bằng `self.after(0, ...)`, chống đơ giật UI.

### 🎨 Cải Tiến Giao Diện & An Toàn Dữ Liệu (Changed & Safety)
- **Xóa Bỏ Checkbox Can Thiệp Backup Nguy Hiểm**:
  - Xóa bỏ hoàn toàn ô `Can thiệp ngôn ngữ vào file Backup trước khi Restore` khỏi UI để giao diện gọn gàng và bảo vệ file backup gốc nguyên vẹn 100%, chỉ giữ lại tùy chọn chuẩn an toàn `⚡ Tự Activate sau Restore`.
- **Loại Bỏ Màu Cam Đỏ Nguy Hiểm**:
  - Thay thế màu cam đỏ (#EA580C, #D97706) khi chọn chiều `Kho B ➜ Kho A` và trên thẻ `Còn lại` bằng màu xanh ngọc Emerald (`#059669`) và xanh biển Sky Blue (`#0284C7`), mang lại cảm giác dịu nhẹ, chuyên nghiệp và an toàn.

---

## [4.2.0 Soft Mint & Gradient Edition] - 2026-09-04

### 🚀 Tính Năng Mới & An Toàn (Added & Safety)
- **Thanh Tiến Trình Gradient (`GradientProgressBar`)**:
  - Thiết kế widget Canvas tùy biến hiển thị dải màu chuyển tiếp hiện đại từ Cyan (`#06B6D4`) sang Electric Blue (`#2563EB`) với rãnh nền xám mint (`#D5E8DD`), trải dài full 100% chiều ngang card.
- **Dời Text Trạng Thái & Số % Lên Phía Trên**:
  - Tách riêng một dòng thông tin trạng thái (`status_row`) đặt ngay trên thanh tiến trình: bên trái hiển thị toàn bộ nội dung bước (`lbl_step`), bên phải hiển thị số phần trăm đậm (`lbl_pct`).
  - Khắc phục triệt để lỗi text bị nhồi vào ô 4 ký tự biến thành `: 45%`.
- **Cơ Chế Cảnh Báo An Toàn Khi Tắt App (`WM_DELETE_WINDOW`)**:
  - Tự động theo dõi các thiết bị đang Restore, Backup hoặc Activate.
  - Khi người dùng bấm nút `[X]`, nếu còn thiết bị đang chạy, hệ thống sẽ chặn lại và bật hộp thoại cảnh báo nguy cơ treo táo / hỏng file backup, hỏi xác nhận trước khi cho phép thoát.
- **Tự Động Activate Sau Restore**:
  - Tối ưu thời gian đếm ngược còn 80 giây cho iPhone reboot xong rồi tự động chạy Batch Activate 3 giai đoạn.

### 🎨 Cải Tiến Giao Diện & Thương Hiệu (Changed & UI/UX)
- **Đổi Tên Thương Hiệu & Logo Sang `TikTok Pro`**:
  - Đổi logo và tiêu đề cửa sổ sang `TikTok Pro` (`TIKTOK PRO - FULL RESTORE & LANGUAGE ENGINE`).
  - Gỡ bỏ dòng text phụ dài `Developer by Tumaemo • Full iPhone Tool Pro Engine Synchronized`.
  - Đẩy cụm Cấu hình ngôn ngữ vào sát ngay bên phải Logo TikTok Pro.
- **Giao Diện Soft Mint Dashboard**:
  - Áp dụng bảng màu xanh bạc hà dịu mát (`#EAF4EE`, `#F0FAF4`, `#E4F1EA`, `#0F2318`) bảo vệ thị giác khi làm việc liên tục.

### 🐛 Sửa Lỗi (Fixed)
- Sửa lỗi không lưu trạng thái kho đang chọn (Kho A/B) khi khởi động lại app bằng cách nạp cấu hình đồng bộ trước khi timer UI kích hoạt.

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
