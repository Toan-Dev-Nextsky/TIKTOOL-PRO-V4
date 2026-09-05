# 📘 TÀI LIỆU KIẾN TRÚC HỆ THỐNG: TIKTOK PRO (TIKTOOL PRO V4)

## 1. Giới Thiệu Tổng Quan
**TikTok Pro** (trước đây là BB Manager Pro) là công cụ kỹ thuật chuyên dụng phục vụ việc quản lý, kích hoạt hàng loạt (Batch Activate), sao lưu dữ liệu (Backup) và khôi phục chuyển kho hai chiều (Restore chuyển kho A ➜ B / B ➜ A) - **Phiên bản hiện tại**: `4.8.3 High-Contrast Store Selection Boxes Edition`
- **Tập tin chạy chính**: `BB_RB.py` (hoặc mở ngầm qua `TIKTOOL_PRO.pyw` / `CHAY_TIKTOOL.bat`)
- **Ngôn ngữ & Thư viện**: Python 3.11 (100% Python Standard Library, Zero-Pip Dependencies), Tkinter GUI, Custom Canvas Components, Threading đa luồng, Semaphore, SQLite3, Plistlib, Runpy.
- **Công cụ nhị phân tích hợp**: `libimobiledevice` (Windows x64) và `ios.exe`.

---

## 2. Các Tính Năng Cốt Lõi

### 2.1. Khôi Phục Chuyển Kho Hai Chiều (Dual Store Restore)
- **Cơ chế chọn kho**: Hỗ trợ chuyển dữ liệu linh hoạt:
  - **Kho A ➜ Kho B**: Dữ liệu từ Kho A (Mục Nhập, viền Xanh Lục `#34D399`) sau khi nạp xong sẽ tự động chuyển sang Kho B (Mục Xuất, viền Xanh Dương `#2563EB`).
  - **Kho B ➜ Kho A**: Dữ liệu từ Kho B (Mục Nhập) tự động nạp và chuyển sang Kho A (Mục Xuất).
- **Lưu trữ trạng thái kho bền vững**: Lựa chọn kho nguồn A/B được lưu trực tiếp vào `settings.json` và nạp đồng bộ ngay khi khởi động app, không bị reset về A.
- **Bộ đếm kho thông minh (Real-time Store Counter)**:
  - **TỔNG KHO**: Tổng phạm vi các bản backup thuộc kho đang thao tác (`CÒN LẠI + ĐÃ CHUYỂN`).
  - **ĐÃ CHUYỂN**: Số lượng thiết bị iPhone đã restore và di chuyển thư mục qua kho đích thành công (có nút `` để reset về 0).
  - **CÒN LẠI**: Số lượng bản backup còn lại thực tế trong thư mục kho nguồn.
- **Động cơ phân bổ 2 lớp (2-Layer Matching Engine)**:
  - *Lớp 1 (Ưu tiên cao nhất)*: Tìm bản backup có UDID trùng khớp chính xác với UDID của iPhone.
  - *Lớp 2 (Ưu tiên tiếp theo)*: Nếu không có bản trùng UDID, tự động ghép bản backup có phiên bản iOS tương thích (`iOS backup <= iOS iPhone`).
- **Can thiệp trực tiếp file Backup trước khi nạp**:
  - Tự động patch UDID máy vào `Info.plist` của bản backup ngay tại kho (xem 2.4), thời gian chuẩn bị ~0.004s/máy.
  - Tự động patch ngôn ngữ / locale vào cơ sở dữ liệu `Manifest.db` nếu bật tùy chọn.

### 2.2. Kích Hoạt Thiết Bị Hàng Loạt (Batch Activate Pipeline)
Quy trình 3 giai đoạn tự động qua lệnh USB đa luồng (kèm **tiền kiểm công cụ**: thiếu `ideviceactivation.exe` hoặc `ios.exe` sẽ dừng và báo đỏ ngay, áp dụng cho cả luồng thủ công và Auto):
1. **Giai đoạn 1 (Activate)**: Gọi `ideviceactivation.exe activate -u {udid} -b` để kích hoạt thiết bị với Apple Server. Sau đó **xác minh lại bằng `ideviceactivation state`**: nếu thiết bị trả về `Unactivated` / `FactoryActivated` thì báo lỗi, không tin exit code.
2. **Giai đoạn 2 (Skip Setup Assistant)**: Gọi `ios.exe prepare --skip-all --udid={udid} --nojson` để bỏ qua toàn bộ các bước thiết lập ban đầu (Hello screen, Wifi, FaceID, Passcode).
   - Kết quả được phân loại tri-state: `ok` (iPhone xác nhận) → mới báo thành công; `sent` (timeout 40s, đã gửi lại tối đa 3 lần, không có phản hồi) → báo vàng `Skip Setup chưa xác nhận`; `failed` (lỗi thật) → báo đỏ kèm nội dung lỗi gốc và dừng luồng.
   - Lỗi thuộc nhóm `lockdownd` / `connection` / `pair` / `not trusted` sẽ tự chạy `idevicepair validate` rồi thử lại (3 lần).
   - Mọi `CommandResult.error` (ví dụ `[WinError 2]` khi thiếu binary) đều được ghi nguyên văn vào nhật ký, không bị nuốt.
3. **Giai đoạn 3 (Set Language / Locale)**: Tùy chọn gọi `ios.exe lang --setlocale={locale} --setlang={lang} --udid={udid} --nojson` để đưa máy về ngôn ngữ mong muốn (ví dụ: Nhật Bản `ja_JP|ja`, Việt Nam `vi_VN|vi`).
   - Tự động lọc bỏ các cảnh báo vô hại về go-ios tunnel (`go-ios agent is not running...`, `failed to get tunnel info...`).
   - Phân biệt timeout 20s do SpringBoard reload (bình thường, máy đã nhận lệnh) và ghi nhận log thông báo màu xanh/trắng, không gắn cờ đỏ lỗi.
4. **Tự động kích hoạt sau khi Restore (Auto Activate)**: Sau khi **toàn bộ đợt Restore** kết thúc, coordinator chờ **100 giây** cho iPhone reboot rồi quét USB (`idevice_id -l`, timeout 8s) tối đa 30 lần cách nhau 3 giây; một UDID phải xuất hiện 3 lần liên tiếp mới được chạy. Mỗi máy sẵn sàng đi qua `_auto_activate_launch`: **chờ lockdownd phản hồi (tối đa 30s) và xác thực lại pairing (`idevicepair`)** trước khi vào đúng pipeline `_batch_activate_worker` của nút Batch thủ công. Máy không trở lại USB được báo rõ và giải phóng operation, không chặn các máy khác.

### 2.3. Sao Lưu Dữ Liệu (Backup All)
- Tự động sao lưu toàn bộ thiết bị đang cắm qua lệnh `idevicebackup2.exe backup --full`.
- Cơ chế tự động đổi tên thư mục backup chuẩn hóa: `1_iPhone`, `2_iPhone`... tránh trùng lặp.
- Tự động gỡ bỏ TikTok / TikTok Lite sau khi hoàn tất backup.
- Mỗi tác vụ ghi vào một job riêng trong `.tiktool_work`; lỗi tác vụ không xóa hay ghi đè thư mục backup cũ.

### 2.4. Chuẩn Bị Restore Tức Thì (Instant In-Place Preparation)
- **Chỉ sửa duy nhất `Info.plist`**: `prepare_restore_in_place()` xác thực backup qua `Status.plist` (`SnapshotState == finished`) rồi ghi UDID máy đích thẳng vào `Info.plist` của bản backup trong kho. Toàn bộ file dữ liệu (thư mục `ab/`, `Manifest.db`, `Manifest.plist`...) không bị đọc lại hay copy.
- **Không copy staging, không hash byte**: Cơ chế cũ (`create_restore_stage`) tốn 4 lượt I/O toàn bộ backup mỗi máy (3 lần SHA-256 + 1 lần `copytree`) ≈ 2.8s/máy, gây 10–15s chờ khi cắm 14 iPhone. Cơ chế mới đo được **0.004s/máy**.
- **Hoàn tác khi restore lỗi**: Bytes gốc của `Info.plist` được giữ trong RAM và ghi trả lại bằng `rollback_restore_info()` nếu `idevicebackup2 restore` thất bại, nên bản backup trong kho không bị mang UDID của máy nạp lỗi.
- **Restore thành công** thì toàn bộ thư mục được `shutil.move` sang kho đối diện (giữ UDID vừa gắn, để Lớp 1 của động cơ ghép nối nhận đúng máy ở lần sau).
- Khi chuyển chéo ổ đĩa, bản đích được copy và xác minh trước; nguồn chỉ bị xóa sau khi bản đích khớp hoàn toàn.
- **`.tiktool_work` chỉ còn phục vụ tác vụ Backup**: Luồng Restore không tạo thư mục tạm nào trong kho A/B.

### 2.5. Tạo Web App Ra Màn Hình iPhone (WebClip Profile Engine)
- **Cơ chế Apple Configuration Profile (`.mobileconfig`)**:
  - Tạo profile định dạng XML với Payload Type `com.apple.webClip.managed`.
  - Tự động nhúng trực tiếp ảnh Icon chuẩn Apple dạng nhị phân Base64. Hỗ trợ các icon chuyên biệt (`tiktok.png`, `tiktok_lite.png`, `fun.png`, `2FA.png`) và icon toàn năng mặc định cực đẹp (`webapp.png` - 3D Glassmorphic Holographic Globe & Link 512×512) cho tất cả các đường link tùy chỉnh bất kỳ (như `https://linkm.site/`).
  - Hỗ trợ chế độ toàn màn hình (`FullScreen: True`) cho trải nghiệm như ứng dụng gốc, và chế độ Safari đối với các tên miền đặc thù (`.fun`).
- **Nạp cấu hình trực tiếp qua cổng USB**:
  - Thực thi qua lệnh:
    ```powershell
    ios.exe profile add --path={profile_path} --udid={udid}
    ```
  - Khi gửi thành công, người dùng chỉ cần bấm xác nhận trên màn hình iPhone để icon xuất hiện ngay ngoài màn hình chính.
- **Tiện ích thao tác nhanh trên giao diện (Hàng 3 Top Card)**:
  - **Nhập link web tự do & chống ghi đè**: Ô nhập link trực quan, mặc định để trống `""` (người dùng tự do nhập/dán URL mong muốn). Ứng dụng tích hợp cờ `_webclip_link_loaded` chỉ nạp cấu hình một lần lúc mở máy, ngăn hiện tượng vòng lặp 1s sync loop giật lùi về URL cũ khi người dùng đang gõ hoặc dán link mới.
  - **Menu chuột phải trực quan (Context Menu)**: Tích hợp `_bind_context_menu()` hỗ trợ chuột phải Cắt, Sao chép, Dán (Paste) và Chọn tất cả trên các ô nhập link và tên.
  - **🚀 Tạo Web App**: Tự động trích xuất tên miền làm nhãn và đẩy link tắt tới toàn bộ thiết bị đang kết nối.
  - **📱 TikTok - AppStore** & **⚡ TikTok Lite - AppStore**: Các nút tắt tạo link tải TikTok/TikTok Lite nhanh từ kho ứng dụng.
  - Xử lý hoàn toàn trên tiểu trình nền (`threading.Thread`), cập nhật tiến trình trên từng thẻ thiết bị và hiển thị hộp thông báo kết quả.

### 2.6. Hệ Thống Thông Báo Hoàn Tất Đợt & Cảnh Báo Rút Máy (Audio-Visual Batch Alert)
- **Cơ chế gom đợt (Batch-level Notification)**:
  - Khi người dùng **tắt tính năng Auto Activate** để cắm đợt máy mới, hệ thống theo dõi số lượng máy đang chạy `active_restores`.
  - Chỉ khi **toàn bộ máy trong đợt hoàn tất** (`len(active_restores) == 0`), hệ thống mới phát thông báo duy nhất một lần (không spam thông báo lẻ tẻ từng máy).
- **Banner nổi bật trong Terminal Log**:
  - Xuất khung cảnh báo màu vàng cam viền đậm: `🔔 ĐÃ RESTORE XONG X MÁY – RÚT TẤT CẢ RA & CẮM ĐỢT MỚI!`, giải phóng người dùng ngay khi máy đang reboot.
- **Tích hợp file âm thanh riêng (`notify.wav`)**:
  - File chuông êm dịu `notify.wav` nằm trực tiếp trong thư mục gốc của app, sử dụng `winsound.PlaySound(..., SND_FILENAME)`.
  - **Khắc phục triệt để cài đặt Windows "No Sounds"**: Bỏ qua hoàn toàn cấu hình tắt âm thanh sự kiện của Windows, đảm bảo phát âm thanh chính xác.
  - Cho phép người dùng linh hoạt đổi file chuông tùy thích bằng cách ghi đè `notify.wav`.
- **Nhấp nháy biểu tượng Taskbar (`FlashWindow`)**:
  - Tích hợp Windows User32 `FlashWindow` làm nhấp nháy màu vàng cam biểu tượng TikTool trên thanh taskbar.
  - Đảm bảo người dùng vẫn nhận biết tức thì ngay cả khi **tắt loa / mute volume máy tính hoàn toàn** hoặc đang chuyển sang làm việc tại cửa sổ khác.

---

## 3. Kiến Trúc Giao Diện (Soft Charcoal Slate Dark Theme & Segoe MDL2 Icon Font)
Thiết kế cao cấp theo phong cách Soft Charcoal Slate Dark Theme (nhẹ nhàng, dịu mắt, chống mỏi mắt khi vận hành cả ngày):

| Vùng giao diện | Vai trò | Thiết kế & Màu sắc |
| :--- | :--- | :--- |
| **Nền ứng dụng** | Khung chứa toàn bộ giao diện | Warm Soft Slate-Charcoal `#1A1D23` (appDark-950) |
| **Thanh tiêu đề OS** | Titlebar của Windows | Windows Dark Titlebar qua DWM (`DwmSetWindowAttribute`) |
| **Top Card** | Logo, Đổi ngôn ngữ, Batch Activate, Tạo Web App Hàng 2 | Nền `#22262E` (appDark-900), viền `#3A414F`, chữ `#F8FAFC`, icon Segoe MDL2 Assets |
| **Batch Activate Button** | Nút kích hoạt toàn bộ thiết bị hàng 1 | `GradientButton` bo góc 6px, gradient `#059669` ➔ `#0D9488`, viền `#34D399` |
| **Bảng Kho (Control Deck)**| Khung chuyển tab và cấu hình kho Restore / Backup | Nền nâng cao `#262A33` (appDark-850), viền `#3A414F`, cấu trúc rõ nét tương phản cao |
| **Hộp Chọn Kho (Store Boxes)** | Chọn đường dẫn Kho A, Kho B & Kho Backup | Nền trắng `#FFFFFF`, chữ đen to đậm `Segoe UI 10 Bold`; Kho A badge Xanh lục `#10B981`, Kho B badge Cam `#F97316`, Kho Backup badge Tím `#7C3AED`; Kho được chọn có border 2px đậm theo màu tương ứng, kho không chọn có border tối `#3A414F` (1px) |
| **Nút Bắt Đầu Restore** | Nút hành động chính tại Bảng Kho | `GradientButton` bo góc 6px; Kho A ➜ B: Gradient 3 điểm dừng Emerald ➔ Teal ➔ Sky (`#059669` ➔ `#0D9488` ➔ `#0369A1`); Kho B ➔ A: Gradient Electric Blue ➔ Indigo ➔ Sky (`#2563EB` ➔ `#4F46E5` ➔ `#0284C7`) |
| **Nút Bắt Đầu Backup** | Nút sao lưu dữ liệu tại Tab Backup | `GradientButton` bo góc 6px; Gradient dải màu Tím sang Xanh dương (`#7C3AED` ➔ `#6D28D9` ➔ `#2563EB`), viền `#A78BFA` |
| **Thanh Tab** | Chuyển đổi giữa Restore Pro và Backup | Tab active `#2563EB` (Electric Blue), inactive `#2C313C` (appDark-800) |
| **Stats Title Bar** | Hiển thị bộ đếm kho và thống kê ngày | Nền `#1A1D23` với các pill card `#22262E` viền `#3A414F`, số liệu `#38BDF8` & `#34D399` |
| **Device Grid** | Lưới thẻ iPhone co giãn thông minh (Responsive Grid) | Card `#22262E` viền `#3A414F`, slot tag `#262A33`, icon điện thoại Tech Cyan `#38BDF8` (hoặc Đỏ `#EF4444` khi Not Trust) |
| **Thanh tiến trình** | Hiển thị % và tiến trình làm việc | Canvas Gradient mượt mà từ Electric Blue `#2563EB` sang Tech Cyan `#38BDF8`, rãnh trượt `#262A33` viền `#3A414F` |
| **Dòng trạng thái thẻ** | Hiển thị tác vụ hiện tại và số % bên trên bar | Chữ trạng thái `#34D399` / `#38BDF8`, % font Consolas `#38BDF8` |
| **Thanh trạng thái đáy** | Hiển thị tổng kết kết nối, thiết bị và đã restore | Nền `#22262E` viền `#3A414F`, chỉ báo `SYSTEM ENGINE ACTIVE` góc phải |
| **Log Terminal Header** | Tiêu đề log và bộ đếm thiết bị kết nối | Trái: `❯_ NHẬT KÝ HỆ THỐNG`, Phải: `Số thiết bị đang kết nối: X` (badge `#262A33` viền `#3A414F`, số `#34D399`) |
| **Log Terminal** | Nhật ký hệ thống thời gian thực | Soft Charcoal Console `#1E2229` viền `#3A414F`, text Consolas `#CBD5E1`, êm dịu dễ đọc |

---

## 4. Quản Lý Đồng Thời & Độ Tin Cậy (Concurrency & Resilience)
- **Kiểm soát luồng với Semaphore**: Sử dụng `threading.Semaphore` để giới hạn số tác vụ đồng thời, đảm bảo đường truyền USB không bị nghẽn và CPU không quá tải.
- **Bảo vệ an toàn khi đóng ứng dụng (`WM_DELETE_WINDOW`)**: Bắt sự kiện khi người dùng bấm dấu `[X]`, nếu còn thiết bị đang Restore/Backup sẽ bật hộp thoại cảnh báo nguy cơ treo táo / hỏng backup, tránh ngắt đột ngột.
- **Giới hạn đồng thời có cấu hình**: Giá trị lấy từ `apps_config.json`, mặc định 4 và được giới hạn trong khoảng 1–8 để tránh nghẽn USB.
- **Operation registry theo UDID**: Một thiết bị chỉ có một thao tác thay đổi trạng thái tại một thời điểm; luồng Restore có thể chuyển quyền sở hữu sang Auto Activate.
- **Polling nền có coalesce**: Đọc metadata ngoài UI thread và chỉ giữ bản cập nhật giao diện mới nhất, tránh tích tụ callback.
- **Theo dõi reboot độc lập USB**: Card thiết bị được giữ trong lúc máy biến mất tạm thời và trạng thái chỉ xóa khi reconnect đã xác minh hoặc hết hạn.
- **UI queue**: Worker không thao tác widget hay biến Tk trực tiếp; toàn bộ cập nhật đi qua queue do UI thread xử lý.
- **Process runner**: Lệnh ngoài có timeout, lưu registry tiến trình và được dừng có kiểm soát khi người dùng xác nhận đóng ứng dụng.
- **Đồng bộ cài đặt JSON tự động**: Quét mtime của `settings.json` mỗi giây một lần để đồng bộ cài đặt ngay cả khi có tiến trình khác can thiệp (chỉ đồng bộ các trường trạng thái, không ghi đè input người dùng đang soạn thảo).
- **Khởi động không cửa sổ dòng lệnh (`TIKTOOL_PRO.pyw`)**: Sử dụng thư viện chuẩn `runpy.run_path` để khởi chạy `BB_RB.py` một cách êm ái, cung cấp đầy đủ biến toàn cục `__file__` và ngữ cảnh thực thi chuẩn mà không mở bất kỳ cửa sổ console đen nào.
- **Tính di động cực cao (Zero-Pip Deployment)**: Toàn bộ dự án được xây dựng 100% bằng thư viện gốc của Python. Khi chuyển sang máy tính mới, chỉ cần cài Python và Apple Driver (iTunes/3uTools) là có thể copy chạy ngay mà không cần internet để tải gói phụ thuộc bên ngoài.

---

## 5. Danh Mục Thao Tác & Phím Tắt Nhanh
- **📂 Chọn**: Bấm vào nút Chọn hoặc click trực tiếp lên đường dẫn để duyệt thư mục.
- **⚡ BẮT ĐẦU RESTORE PRO**: Khởi chạy quy trình ghép nối và nạp chuyển kho.
- **⚡ Batch Activate**: Kích hoạt hàng loạt cho toàn bộ thiết bị đang kết nối.
- **🚀 Tạo Web App**: Tạo shortcut ra màn hình chính cho toàn bộ thiết bị.
- **↺ (trên thanh thống kê)**: Reset nhanh bộ đếm "Đã chuyển" về 0 khi bắt đầu ca làm việc mới.
- **Hôm nay: X (thống kê ngày)**: Tự động ghi nhận số lượng restore hoàn tất trong ngày và lưu vào `settings.json`.
