# Nhật Ký Thay Đổi (Changelog) - BB MANAGER PRO

Tất cả những thay đổi và nâng cấp quan trọng của dự án được ghi nhận đầy đủ tại đây.

---

## [4.7.1 Web App Link Fix & Portable Launcher Edition] - 2026-09-05

### 🌐 Sửa Lỗi Nhập Link Web App Tự Chọn (Custom WebClip URL Fix)
- **Khắc phục lỗi nhảy về link mặc định khi dán URL mới**:
  - Phát hiện nguyên nhân: Vòng lặp đồng bộ `_start_json_sync_loop` chạy mỗi 1 giây ngầm gọi `_apply_settings_to_ui()`, liên tục ghi đè biến `var_custom_webclip_link` về giá trị lưu trong `settings.json`.
  - Giải pháp: Thêm cờ kiểm tra khởi động `if not getattr(self, '_webclip_link_loaded', False):` đảm bảo URL tùy chỉnh chỉ nạp 1 lần duy nhất lúc mở app, người dùng có thể tự do xóa, gõ, hoặc dán link bất kỳ (`https://...`) mà không bao giờ bị ghi đè hay giật lùi về `https://linkm.site/`.
- **Bổ sung Menu Chuột Phải Cho Ô Nhập Liệu (Context Menu: Cut / Copy / Paste / Select All)**:
  - Tích hợp phương thức `_bind_context_menu()` cho các ô nhập liệu `Entry` (`ent_custom_link`, `ent_custom`), hỗ trợ nhấp chuột phải để Cắt, Sao chép, Dán (Paste) và Chọn tất cả cực kỳ tiện lợi trên Windows.

### 🚀 Sửa Lỗi Khởi Động TIKTOOL_PRO.pyw & Khả Năng Di Chuyển Máy (Portability)
- **Sửa lỗi không mở được khi nhấp đúp vào `TIKTOOL_PRO.pyw`**:
  - Nguyên nhân: Phương thức `exec()` cũ không truyền biến toàn cục `__file__`, làm dòng lệnh `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` trong `BB_RB.py` gặp lỗi `NameError: name '__file__' is not defined` và tắt âm thầm khi chạy dưới `pythonw`.
  - Giải pháp: Chuyển sang sử dụng thư viện chuẩn `runpy.run_path(target, run_name="__main__")`, tự động thiết lập đầy đủ môi trường runtime, biến `__file__` và tham số hệ thống.
- **Tối ưu hóa file khởi động `CHAY_TIKTOOL.bat`**:
  - Tự động dò tìm `pythonw` trong PATH hệ thống hoặc các thư mục mặc định `C:\Python311\pythonw.exe`, fallback linh hoạt về `python` nếu chưa đăng ký file association.
- **Khẳng định tính độc lập & dễ dàng cài đặt sang máy tính khác (Zero-Pip Dependencies)**:
  - Ứng dụng hoạt động 100% bằng thư viện gốc của Python (Standard Library), không cần chạy bất kỳ lệnh `pip install` nào.
  - Kiểm tra bản quyền (`_require_license`) luôn trả về `True` (không khóa cứng theo phần cứng máy tính).
  - Để chạy trên máy khác: Chỉ cần cài Python 64-bit (tích chọn *Add python.exe to PATH*) + Cài iTunes/3uTools (lấy Apple Mobile Device Support driver) và copy nguyên thư mục app sang là dùng được ngay.

---

## [4.7.0 Layout Refinement & Device Display Edition] - 2026-09-05

### 🖥️ Hoàn Thiện Bố Cục Trên - Dưới & Lưới Co Giãn Linh Hoạt (Responsive Grid)
- **Duy trì bố cục Trên - Dưới nguyên bản (Full-width)**:
  - Khung Thiết bị kết nối đặt ở nửa trên trải dài toàn bộ chiều rộng app.
  - Khung Nhật ký hệ thống (Terminal OLED box) đặt ở nửa dưới trải dài toàn bộ chiều rộng app.
  - Thanh trạng thái (`Trust: X • Tổng: Y • Not Trust: Z • Restored: W`) đặt sát đáy ứng dụng.
- **Mặc định hiển thị đúng 3 thiết bị / 1 hàng & phóng to 5 thiết bị / 1 hàng**:
  - Tinh chỉnh hàm `_calculate_columns`:
    - Ở kích thước mặc định (~1300px): Hiển thị chuẩn **3 thiết bị trên 1 hàng** (rộng rãi, thông số ECID/Model rõ ràng).
    - Khi bấm phóng to toàn màn hình (Full HD 1920px): Tự động mở rộng thành **5 thiết bị trên 1 hàng**.
    - Khi thu nhỏ về kích thước cũ: Tự động co về 3 cột mượt mà.
  - **Khắc phục lỗi Tkinter uniform weight cleanup**: Sử dụng `uniform=""` thay cho `uniform=None` để xóa hoàn toàn nhóm ràng buộc cột cũ, loại bỏ triệt để hiện tượng thẻ bị bóp dẹt khi un-maximize.

### 🎨 Thẻ Thiết Bị Viền Đen & Chuẩn Hóa Tiêu Đề
- **Viền thẻ thiết bị màu đen (`#000000`)**:
  - Chuyển toàn bộ viền thẻ thiết bị sang màu đen thanh lịch, tương phản cao và rõ ràng từng ô thiết bị (vẫn giữ viền đỏ cảnh báo nếu máy chưa bấm Tin Cậy).
- **Tối ưu vị trí và kiểu dáng tiêu đề**:
  - Tiêu đề **`NHẬT KÝ HỆ THỐNG`**: Căn sát lề TRÁI của thanh ngăn cách console log.
  - Thông tin **`Số thiết bị đang kết nối: X`**: Đặt ở lề PHẢI của thanh này dưới dạng text thuần font đậm (`Segoe UI 10 bold`, màu xanh rêu sẫm `#0A2B17`), loại bỏ hoàn toàn khung viền button/pill theo đúng ý người dùng.
  - **Thanh trên tinh gọn**: Xóa bỏ ô đếm thiết bị thừa ở thanh trên, đưa cụm `Tổng: X (Hôm nay) ↺` sang lề trái và giữ các thẻ `Tổng kho / Đã chuyển / Còn lại` ở lề phải, tạo sự cân đối và thoáng đãng.
  - **Liên kết cập nhật thời gian thực**: Kết nối `self.lbl_log_dev_info` trực tiếp vào hàm `_sync_cards()`, đảm bảo số lượng thiết bị luôn cập nhật tức thì 100% khi cắm hoặc rút máy.

---

## [4.6.0 Batch Activate & Audio-Visual Notification Edition] - 2026-09-04

### 🔔 Thông Báo Hoàn Tất Restore Đợt & Rút Máy (Batch Restore Notification)
- **Thông báo gom cả đợt khi tắt Auto Activate**:
  - Không thông báo lẻ tẻ từng máy gây phiền phức; chỉ thông báo đúng **1 lần duy nhất** khi toàn bộ máy trong đợt restore hoàn thành (`len(active_restores) == 0`).
  - Banner chữ nổi bật màu vàng cam (`alert` tag) trong ô Terminal Log: `🔔 ĐÃ RESTORE XONG X MÁY – RÚT TẤT CẢ RA & CẮM ĐỢT MỚI!`.
- **Âm thanh tích hợp sẵn trong App (`notify.wav`)**:
  - Tích hợp sẵn file âm thanh êm ái `notify.wav` ngay trong thư mục app.
  - Sử dụng cờ `SND_FILENAME` phát trực tiếp từ file, hoàn toàn không bị ảnh hưởng kể cả khi Windows đang cài đặt chế độ âm thanh `No Sounds`.
  - Người dùng có thể tự thay đổi âm thanh thông báo tùy thích bằng cách thay file `notify.wav`.
- **Nhấp nháy Taskbar Windows (`FlashWindow`)**:
  - Tích hợp gọi Windows User32 `FlashWindow` làm nhấp nháy icon TikTool màu vàng cam ở thanh Taskbar.
  - Giúp nhận biết máy đã xong ngay cả khi người dùng **tắt loa / mute âm lượng máy tính hoàn toàn** hoặc đang dùng ứng dụng khác.

### ⚡ Khắc Phục Treo 80% Batch Activate (Reliability Fix)
- **Sửa lỗi đứng tiến trình 80% khi đổi ngôn ngữ**:
  - Rút ngắn timeout lệnh `ios.exe lang` từ 120s xuống 20s và xử lý ngoại lệ mềm dẻo khi SpringBoard reload.
  - Bổ sung helper thread-safe `_update_card_progress` và `_update_card_step` bảo vệ UI khi thiết bị vừa khởi động lại.

### 🎨 Tối Ưu Nút Bấm Chuyển Kho & Tiện Ích Khởi Động
- **Phân biệt màu sắc nút bấm theo chiều chuyển kho**:
  - Chiều Kho A ➜ B: Màu Xanh Emerald (`#059669`) nổi bật.
  - Chiều Kho B ➜ A: Màu Xanh Đại Dương Ocean Blue (`#0284C7`) rõ ràng, tránh nhầm lẫn hướng thao tác.
- **Tiện ích mở app bằng 1 cú nhấp đúp chuột**:
  - Bổ sung `CHAY_TIKTOOL.bat` và file chạy ngầm không hiện console `TIKTOOL_PRO.pyw`.

---

## [4.5.0 Modern Light Dashboard & Clean Staging Edition] - 2026-09-04

### 🎨 Tối ưu Giao diện & Trải Nghiệm (UI/UX Compacting)
- **Chuyển đổi giao diện sang Modern Light Dashboard**:
  - Thiết kế bảng màu hiện đại dịu mắt với tông Slate-100 (`#F8FAFC`), viền Slate-200 (`#E2E8F0`), điểm nhấn Soft Indigo (`#4F46E5`, `#6366F1`) và xanh Emerald (`#10B981`).
  - Thu gọn toàn bộ cụm điều khiển phía trên (Top Card): Logo, Đổi ngôn ngữ, Batch Activate, Tạo Web App thành các hàng ngắn gọn, siêu tiết kiệm diện tích.
  - Tinh gọn thanh trạng thái đáy: Thay thế các nút hộp màu thô cứng (`Trust`, `Tổng`, `Not Trust`, `Restored`) bằng chuỗi text thanh mảnh kèm dấu phân cách ` | ` inline, giảm triệt để chiều cao và diện tích đáy.
  - Tối giản thẻ thiết bị (`DeviceCard`): Xóa bỏ 2 nút đơn lẻ `Lang` và `Active` trên từng card để layout gọn gàng, thoáng mắt, ưu tiên điều khiển hàng loạt từ thanh công cụ.

### 📊 Thống Kê Số Lượng Restore Trong Ngày (Daily Restore Counter)
- **Bộ đếm Restore trong ngày (`Hôm nay: X`)**:
  - Tích hợp nhãn thống kê số máy đã restore thành công trong ngày ngay trên thanh tiêu đề thiết bị (`dev_title_bar`) với phong cách Soft Indigo thanh lịch.
  - Lưu trữ bền vững trong `settings.json` (`dailyRestoreDate`, `dailyRestoreCount`), không bị mất khi tắt app.
  - Cơ chế tự động nhận diện ngày mới và reset bộ đếm về 0 khi sang ngày tiếp theo.

### 🛡️ Chuẩn Hóa Restore & Tự Động Dọn Dẹp Staging (.tiktool_work)
- **Kiểm tra chuẩn hóa Restore Logic**:
  - Khẳng định tính chuẩn xác của lệnh `idevicebackup2 -u {udid} -s {src_name} restore {base_dir} --settings --remove`.
  - Quy trình staging bất biến an toàn: Sao chép đọc-chỉ bản backup gốc, patch UDID trong staging `Info.plist`, kiểm tra fingerprint toàn vẹn và chuyển kho sau khi hoàn tất.
- **Tự động xóa thư mục cha `.tiktool_work`**:
  - Cải tiến hàm `cleanup_owned_job` trong `tiktool_core.py` tự động xóa luôn thư mục cha `.tiktool_work` nếu rỗng sau khi dọn dẹp job restore, không để lại bất kỳ thư mục rác nào trong kho A hoặc kho B của người dùng.
  - Đã quét và dọn sạch thư mục `.tiktool_work` tồn dư trong kho dữ liệu.

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
