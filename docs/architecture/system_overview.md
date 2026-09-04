# 📘 TÀI LIỆU KIẾN TRÚC HỆ THỐNG: TIKTOK PRO (TIKTOOL PRO V4)

## 1. Giới Thiệu Tổng Quan
**TikTok Pro** (trước đây là BB Manager Pro) là công cụ kỹ thuật chuyên dụng phục vụ việc quản lý, kích hoạt hàng loạt (Batch Activate), sao lưu dữ liệu (Backup) và khôi phục chuyển kho hai chiều (Restore chuyển kho A ➜ B / B ➜ A) cho số lượng lớn iPhone thông qua kết nối USB trên nền tảng Windows.

- **Phiên bản hiện tại**: `4.4.0 Stability & Immutable Backup Edition`
- **Tập tin chạy chính**: `BB_RB.py`
- **Ngôn ngữ & Thư viện**: Python 3.11, Tkinter GUI, Custom Canvas Components, Threading đa luồng, Semaphore, SQLite3, Plistlib.
- **Công cụ nhị phân tích hợp**: `libimobiledevice` (Windows x64) và `ios.exe`.

---

## 2. Các Tính Năng Cốt Lõi

### 2.1. Khôi Phục Chuyển Kho Hai Chiều (Dual Store Restore)
- **Cơ chế chọn kho**: Hỗ trợ chuyển dữ liệu linh hoạt:
  - **Kho A ➜ Kho B**: Dữ liệu từ Kho A (Mục Nhập, viền Xanh Ngọc `#34D399`) sau khi nạp xong sẽ tự động chuyển sang Kho B (Mục Xuất, viền Cam `#FBBF24`).
  - **Kho B ➜ Kho A**: Dữ liệu từ Kho B (Mục Nhập) tự động nạp và chuyển sang Kho A (Mục Xuất).
- **Lưu trữ trạng thái kho bền vững**: Lựa chọn kho nguồn A/B được lưu trực tiếp vào `settings.json` và nạp đồng bộ ngay khi khởi động app, không bị reset về A.
- **Bộ đếm kho thông minh (Real-time Store Counter)**:
  - **TỔNG KHO**: Tổng phạm vi các bản backup thuộc kho đang thao tác (`CÒN LẠI + ĐÃ CHUYỂN`).
  - **ĐÃ CHUYỂN**: Số lượng thiết bị iPhone đã restore và di chuyển thư mục qua kho đích thành công (có nút `↺` để reset về 0).
  - **CÒN LẠI**: Số lượng bản backup còn lại thực tế trong thư mục kho nguồn.
- **Động cơ phân bổ 2 lớp (2-Layer Matching Engine)**:
  - *Lớp 1 (Ưu tiên cao nhất)*: Tìm bản backup có UDID trùng khớp chính xác với UDID của iPhone.
  - *Lớp 2 (Ưu tiên tiếp theo)*: Nếu không có bản trùng UDID, tự động ghép bản backup có phiên bản iOS tương thích (`iOS backup <= iOS iPhone`).
- **Can thiệp trực tiếp file Backup trước khi nạp**:
  - Tự động patch UDID máy vào `Info.plist` của bản backup.
  - Tự động patch ngôn ngữ / locale vào cơ sở dữ liệu `Manifest.db` nếu bật tùy chọn.

### 2.2. Kích Hoạt Thiết Bị Hàng Loạt (Batch Activate Pipeline)
Quy trình 3 giai đoạn tự động qua lệnh USB đa luồng:
1. **Giai đoạn 1 (Activate)**: Gọi `ideviceactivation.exe activate -u {udid} -b` để kích hoạt thiết bị với Apple Server.
2. **Giai đoạn 2 (Skip Setup Assistant)**: Gọi `ios.exe prepare --skip-all --udid={udid} --nojson` để bỏ qua toàn bộ các bước thiết lập ban đầu (Hello screen, Wifi, FaceID, Passcode).
3. **Giai đoạn 3 (Set Language / Locale)**: Tùy chọn gọi `ios.exe lang --setlocale={locale} --setlang={lang} --udid={udid} --nojson` để đưa máy về ngôn ngữ mong muốn (ví dụ: Nhật Bản `ja_JP|ja`, Việt Nam `vi_VN|vi`).
4. **Tự động kích hoạt sau khi Restore (Auto Activate)**: Đếm ngược 80 giây cho iPhone reboot hoàn tất rồi tự động kích hoạt toàn bộ luồng trên mà không cần can thiệp thủ công.

### 2.3. Sao Lưu Dữ Liệu (Backup All)
- Tự động sao lưu toàn bộ thiết bị đang cắm qua lệnh `idevicebackup2.exe backup --full`.
- Cơ chế tự động đổi tên thư mục backup chuẩn hóa: `1_iPhone`, `2_iPhone`... tránh trùng lặp.
- Tùy chọn tự động gỡ bỏ TikTok / TikTok Lite sau khi hoàn tất backup.
- Mỗi tác vụ ghi vào một job riêng trong `.tiktool_work`; lỗi tác vụ không xóa hay ghi đè thư mục backup cũ.

### 2.4. Restore bất biến backup nguồn
- Backup nguồn chỉ được mở để đọc và tính fingerprint; ứng dụng không sửa, thêm hoặc xóa file bên trong.
- Một bản sao đầy đủ được tạo trong staging, sau đó chỉ `Info.plist` của bản staging mới được gắn UDID đích.
- Sau khi restore thành công, fingerprint nguồn được kiểm tra lại rồi toàn bộ thư mục được chuyển sang kho đối diện.
- Khi chuyển chéo ổ đĩa, bản đích được copy và xác minh trước; nguồn chỉ bị xóa sau khi bản đích khớp hoàn toàn.

### 2.5. Tạo Web App Ra Màn Hình iPhone (WebClip Profile Engine)
- **Cơ chế Apple Configuration Profile (`.mobileconfig`)**:
  - Tạo profile định dạng XML với Payload Type `com.apple.webClip.managed`.
  - Tự động nhúng trực tiếp ảnh Icon chuẩn Apple dạng nhị phân Base64. Hỗ trợ các icon chuyên biệt (`tiktok.png`, `tiktok_lite.png`, `fun.png`, `2FA.png`) và icon toàn năng mặc định cực đẹp (`webapp.png` - 3D Glassmorphic Holographic Globe & Link 512×512) cho tất cả các đường link tùy chỉnh bất kỳ (như `https://linkm.site/`).
  - Hỗ trợ chế độ toàn màn hình (`FullScreen: True`) cho trải nghiệm như ứng dụng gốc, và chế độ Safari đối với các tên miền đặc thù (`.fun`).
- **Nạp cấu hình trực tiếp qua cổng USB**:
  - Thực thi qua lệnh:
    ```powershell
    ios.exe profile add <path.mobileconfig> --udid=<udid> --nojson
    ```
  - Khi gửi thành công, người dùng chỉ cần bấm xác nhận trên màn hình iPhone để icon xuất hiện ngay ngoài màn hình chính.
- **Tiện ích thao tác nhanh trên giao diện (Hàng 3 Top Card)**:
  - **Nhập link web**: Ô nhập link trực quan, mặc định sẵn `https://linkm.site/`, tự động lưu cấu hình vào `settings.json`.
  - **🚀 Tạo Web App**: Tự động trích xuất tên miền làm nhãn và đẩy link tắt tới toàn bộ thiết bị đang kết nối.
  - **📱 TikTok - AppStore** & **⚡ TikTok Lite - AppStore**: Các nút tắt tạo link tải TikTok/TikTok Lite nhanh từ kho ứng dụng.
  - Xử lý hoàn toàn trên tiểu trình nền (`threading.Thread`), cập nhật tiến trình trên từng thẻ thiết bị và hiển thị hộp thông báo kết quả.

---

## 3. Kiến Trúc Giao Diện (Soft Mint & Gradient Dashboard)
Thiết kế hướng đến sự tập trung cao, dịu mắt và thẩm mỹ cao cấp:

| Vùng giao diện | Vai trò | Màu sắc chủ đạo |
| :--- | :--- | :--- |
| **Nền ứng dụng** | Khung chứa toàn bộ giao diện | Soft Mint `#EAF4EE` |
| **Top Card** | Logo `TikTok Pro`, Đổi ngôn ngữ, Batch Activate, Tạo Web App Hàng 3 | Nền mint nhạt `#F0FAF4`, viền `#A7C4B0` |
| **Tab Section** | Chuyển đổi giữa Restore Pro và Backup | Tab active `#0284C7`, inactive `#D5EAD9` |
| **Stats Title Bar** | Hiển thị `[X máy]` và cụm 3 thẻ BỘ ĐẾM KHO | Nền `#F0FAF4`, chữ số to đậm rõ ràng |
| **Device Grid** | Lưới thẻ iPhone tích hợp `GradientProgressBar` | Card `#F0FAF4`, viền `#10B981` (Trust) / `#EF4444` |
| **Thanh tiến trình** | Hiển thị % và tiến trình làm việc | Gradient Cyan `#06B6D4` ➜ Electric Blue `#2563EB` |
| **Dòng trạng thái thẻ** | Hiển thị tác vụ hiện tại và số % bên trên bar | Chữ trạng thái `#059669`, % font Consolas `#0284C7` |
| **Log Terminal** | Nhật ký hệ thống thời gian thực | Dark Box OLED `#050811`, chữ trắng `#F0FAF4` |

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
- **Đồng bộ cài đặt JSON tự động**: Quét mtime của `settings.json` mỗi giây một lần để đồng bộ cài đặt ngay cả khi có tiến trình khác can thiệp.

---

## 5. Danh Mục Phím Tắt & Thao Tác Nhanh
- **📂 Chọn**: Bấm vào nút Chọn hoặc click trực tiếp lên đường dẫn để duyệt thư mục.
- **⚡ BẮT ĐẦU RESTORE PRO**: Khởi chạy quy trình ghép nối và nạp chuyển kho.
- **⚡ Active (trên thẻ iPhone)**: Kích hoạt nhanh đơn lẻ cho riêng chiếc iPhone đó.
- **🌐 Lang (trên thẻ iPhone)**: Đổi nhanh ngôn ngữ đơn lẻ cho riêng chiếc iPhone đó.
- **↺ (trên thanh thống kê)**: Reset nhanh bộ đếm "Đã chuyển" về 0 khi bắt đầu ca làm việc mới.
