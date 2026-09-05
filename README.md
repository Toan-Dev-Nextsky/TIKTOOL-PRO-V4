# 🚀 TIKTOOL PRO V4 (TIKTOK PRO)

> **Hệ thống Quản lý, Sao lưu (Backup), Khôi phục chuyển kho hai chiều (Restore Dual Store), Kích hoạt hàng loạt (Batch Activate) và Tạo Web App chuyên nghiệp cho dàn máy iPhone qua cổng USB đa luồng.**

[![Phiên bản](https://img.shields.io/badge/Version-4.5.0_Modern_Light-6366F1.svg)](CHANGELOG.md)
[![Nền tảng](https://img.shields.io/badge/Platform-Windows_x64-0284C7.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.11-10B981.svg)](#)
[![Giao diện](https://img.shields.io/badge/UI-Modern_Light_Dashboard-4F46E5.svg)](#)

---

## 📖 1. Giới Thiệu Tổng Quan

**TIKTOOL PRO V4** (TikTok Pro) là giải pháp tự động hóa toàn diện được thiết kế chuyên biệt cho các nông trại iPhone (Phone Farm), đơn vị kinh doanh và kỹ thuật viên cần quản lý, cài đặt hàng loạt thiết bị iOS cùng lúc.

Ứng dụng kết hợp sức mạnh giao tiếp phần cứng trực tiếp qua bộ công cụ `libimobiledevice` và engine độc quyền `ios.exe`, mang lại tốc độ xử lý vượt trội, an toàn tuyệt đối cho hệ điều hành của máy và dữ liệu backup.

---

## ✨ 2. Các Tính Năng Cốt Lõi

### 🔄 2.1. Khôi Phục Chuyển Kho Hai Chiều (Dual Store Restore)
- **Đảo chiều luồng linh hoạt**:
  - **Kho A ➜ Kho B**: Dữ liệu từ Kho A (Mục Nhập) nạp vào iPhone, sau khi hoàn tất tự động chuyển thư mục sang Kho B (Mục Xuất).
  - **Kho B ➜ Kho A**: Dữ liệu từ Kho B nạp vào iPhone và tự động chuyển sang Kho A.
- **Chuẩn bị nạp tức thì (Instant In-Place Preparation)**:
  - Chỉ kiểm tra `Status.plist` rồi gắn UDID máy đích vào `Info.plist` ngay tại kho — **0.004 giây/máy**, cắm 14 iPhone vẫn vào lệnh restore tức thì (không copy, không hash toàn bộ file).
  - Nếu nạp thất bại, `Info.plist` được hoàn tác về nguyên trạng nên bản backup không bị mang UDID của máy lỗi.
  - Backup chỉ được di chuyển sang kho đối diện sau khi nạp thành công 100%.
- **Không sinh thư mục rác trong kho**:
  - Luồng Restore không tạo `.tiktool_work`; thư mục tạm này chỉ dùng cho tác vụ Backup và tự dọn sau khi xong.
- **Động cơ phân bổ 2 lớp (2-Layer Matching Engine)**:
  - *Lớp 1 (Ưu tiên tuyệt đối)*: Tự động ghép bản backup có tên/metadata trùng khớp chính xác với UDID của iPhone đang cắm.
  - *Lớp 2 (Tương thích)*: Nếu không có bản trùng UDID, tự động ghép bản backup có phiên bản iOS nhỏ hơn hoặc bằng iOS máy (`iOS backup <= iOS iPhone`).

### ⚡ 2.2. Kích Hoạt Thiết Bị Hàng Loạt (Batch Activate Pipeline)
Quy trình 3 giai đoạn tự động qua cổng USB:
1. **Giai đoạn 1 (Activate)**: Kích hoạt thiết bị với Apple Activation Server (`ideviceactivation.exe`).
2. **Giai đoạn 2 (Skip Setup Assistant)**: Vượt qua toàn bộ màn hình thiết lập ban đầu (Hello, Wi-Fi, FaceID, Passcode, Điều khoản) vào thẳng màn hình chính (`ios.exe prepare --skip-all`).
3. **Giai đoạn 3 (Set Language / Locale)**: Tùy chọn chuyển ngôn ngữ và vùng địa lý mong muốn (Việt Nam `vi_VN|vi`, Nhật Bản `ja_JP|ja`, Hoa Kỳ `en_US|en`...).
- **⚡ Tự động kích hoạt sau khi Restore (Auto Activate)**:
  - Sau khi nạp dữ liệu xong, ứng dụng tự động đếm ngược 80 giây cho iPhone khởi động lại hoàn tất rồi tự chạy pipeline Batch Activate, không cần thao tác thủ công.

### 📊 2.3. Thống Kê Sản Lượng Theo Ngày (Daily Restore Counter)
- **Nhãn hiển thị `Hôm nay: X`**: Nằm ngay trên thanh tiêu đề thiết bị với phong cách Soft Indigo thanh lịch.
- **Lưu trữ bền vững**: Dữ liệu được ghi trực tiếp vào `settings.json` (`dailyRestoreDate`, `dailyRestoreCount`), không bị mất khi khởi động lại ứng dụng.
- **Tự động sang ngày mới**: Cơ chế tự so sánh ngày hệ thống (YYYY-MM-DD) và reset bộ đếm về `0` khi bước sang ca làm việc ngày mới.

### 🌐 2.4. Tạo Web App Ra Màn Hình iPhone (WebClip Profile Engine)
- **Cơ chế Apple Configuration Profile (`.mobileconfig`)**:
  - Tạo cấu hình chuẩn của Apple với Payload Type `com.apple.webClip.managed`.
  - Nạp thẳng qua cổng USB bằng lệnh `ios.exe profile add`.
  - Biểu tượng xuất hiện ngoài màn hình chính, hỗ trợ mở chế độ toàn màn hình (PWA) như một ứng dụng cài đặt thực thụ.
- **Icon Toàn Năng Siêu Đẹp (`webapp.png`)**:
  - Thiết kế 3D Glassmorphic Holographic Globe & Link chuẩn HD 512×512, làm icon mặc định cao cấp cho mọi link web bất kỳ (ví dụ `https://linkm.site/`), không bị icon xám Safari.
  - Hỗ trợ các icon phím tắt chuyên biệt: TikTok, TikTok Lite, 2FA, Fun.

### 🎨 2.5. Giao Diện Modern Light Dashboard & Tối Giản Diện Tích
- **Bảng màu tinh tế**: Tông nền Slate-100 (`#F8FAFC`), card trắng viền Slate (`#E2E8F0`), điểm nhấn Soft Indigo (`#4F46E5`, `#6366F1`) và Emerald (`#10B981`).
- **Thanh điều khiển phía trên (Top Card) siêu gọn**: Thu nhỏ kích thước, xếp các cụm chức năng theo hàng ngang tiết kiệm tối đa diện tích làm việc.
- **Thanh trạng thái đáy tối giản**: Thay thế các nút hộp màu to bằng chuỗi text thanh mảnh, ngăn cách bằng dấu ` | `, giảm tối đa chiều cao phần chân trang.
- **Tối giản thẻ thiết bị (DeviceCard)**: Bỏ các nút bấm đơn lẻ để tập trung hiển thị thông tin máy và thanh tiến trình `GradientProgressBar` mượt mà.

### 🛡️ 2.6. Quản Lý Đa Luồng & An Toàn Thiết Bị (Resilience)
- **Kiểm soát nghẽn USB bằng Semaphore**: Giới hạn tối đa 4 tác vụ nặng đồng thời (có thể cấu hình trong `apps_config.json`), bảo vệ đường truyền USB.
- **Khóa chống Treo Táo (`WM_DELETE_WINDOW`)**: Chặn sự kiện đóng ứng dụng khi có thiết bị đang trong quá trình ghi dữ liệu hoặc khởi động lại.
- **Reboot Tracker**: Khóa trạng thái thiết bị trong 135 giây khi máy khởi động lại để tránh luồng Polling hiểu nhầm là mất kết nối hoặc Not Trust.

---

## 📁 3. Cấu Trúc Thư Mục Dự Án

```text
C:\TIKTOOL PRO V4\
├── BB_RB.py                 # Mã nguồn giao diện chính và luồng xử lý ứng dụng
├── tiktool_core.py          # Thư viện lõi (quản lý backup, staging, fingerprint, cleanup)
├── settings.json            # Cấu hình người dùng (đường dẫn kho, ngôn ngữ, thống kê ngày...)
├── apps_config.json         # Cấu hình giới hạn luồng đồng thời và ngưỡng hệ thống
├── license.json             # Bản quyền kích hoạt máy
├── README.md                # Tài liệu hướng dẫn sử dụng này
├── CHANGELOG.md             # Lịch sử chi tiết các phiên bản phát hành
├── docs/
│   └── architecture/
│       └── system_overview.md   # Tài liệu phân tích kiến trúc hệ thống chuyên sâu
├── .brain/                  # Bộ nhớ ngữ cảnh vĩnh viễn của trợ lý AI
│   ├── brain.json           # Kiến trúc tĩnh, tech stack, quy chuẩn dự án
│   ├── session.json         # Lịch sử phiên làm việc, trạng thái hiện tại
│   └── handover.md          # Biên bản bàn giao kỹ thuật
├── webapp.png               # Icon toàn năng 3D Glassmorphic cho Web App
├── tiktok.png, fun.png...   # Các icon chuyên dụng cho phím tắt
└── *.exe, *.dll             # Bộ công cụ libimobiledevice và ios.exe cho Windows
```

---

## 🛠️ 4. Yêu Cầu Hệ Thống & Cài Đặt

### 4.1. Yêu Cầu Môi Trường
- **Hệ điều hành**: Windows 10 hoặc Windows 11 (64-bit).
- **Trình điều khiển Apple**: Cần cài đặt **iTunes** (bản tải từ trang chủ Apple, không dùng bản Microsoft Store) hoặc **Apple Mobile Device Support**.
- **Python**: Python phiên bản 3.10 hoặc 3.11 (64-bit).

### 4.2. Khởi Chạy Ứng Dụng (Ấn đúp để chạy)
Bạn có thể mở ứng dụng dễ dàng bằng các cách sau mà **không cần gõ lệnh terminal**:

1. **Cách 1 (Khuyên dùng - Nhanh nhất)**: Ra ngoài **Màn hình chính (Desktop)**, ấn đúp chuột vào biểu tượng shortcut **`TIKTOOL PRO V4`** (icon chữ Q xanh). Ứng dụng sẽ mở ngay lập tức, không hiện cửa sổ đen!
2. **Cách 2**: Trong thư mục `C:\TIKTOOL PRO V4`, ấn đúp chuột vào file **`CHAY_TIKTOOL.bat`**.
3. **Cách 3**: Trong thư mục `C:\TIKTOOL PRO V4`, ấn đúp chuột vào file **`TIKTOOL_PRO.pyw`**.
4. **Cách 4 (Dành cho lập trình viên)**: Mở Terminal và chạy lệnh:
   ```powershell
   python BB_RB.py
   ```

---

## 🚀 5. Hướng Dẫn Vận Hành

### Bước 1: Kết nối thiết bị
1. Cắm dàn iPhone vào máy tính qua cổng USB hoặc USB Hub chuyên dụng.
2. Mở màn hình iPhone, chọn **Tin cậy (Trust)** máy tính và nhập mật khẩu màn hình (nếu có).
3. Thẻ thiết bị sẽ hiển thị trên lưới với viền xanh lá (Trust), kèm tên máy, iOS version, UDID và dung lượng pin.

### Bước 2: Thiết lập Kho dữ liệu (Kho A & Kho B)
1. Trên thanh tab **Restore Pro**, chọn thư mục **Kho A** và **Kho B** bằng nút **[Chọn]**.
2. Chọn chiều nạp mong muốn:
   - `Kho A ➜ Kho B`: Lấy backup từ kho A nạp vào máy, xong chuyển sang B.
   - `Kho B ➜ Kho A`: Lấy backup từ kho B nạp vào máy, xong chuyển sang A.

### Bước 3: Thực hiện Khôi phục (Restore Pro)
1. Tích chọn `⚡ Tự Activate sau Restore` nếu muốn máy tự động kích hoạt sau khi khởi động lại.
   - *Mẹo*: Nếu **tắt** tùy chọn này để cắm đợt máy mới, ngay khi cả đợt restore xong app sẽ **phát chuông ding êm ái**, **nhấp nháy icon Taskbar màu cam** và **báo log rõ ràng** để bạn rút toàn bộ máy ra cắm đợt tiếp theo mà không cần ngồi chờ iPhone reboot!
2. Bấm nút **[⚡ BẮT ĐẦU RESTORE PRO]**.
3. Bảng xác nhận phân bổ ghép nối 2 lớp sẽ hiện ra hiển thị chi tiết: Tên bản backup, iOS backup, Tên máy nhận, UDID và Phương thức ghép (Trùng UDID hoặc Khớp iOS).
4. Bấm **[XÁC NHẬN BẮT ĐẦU]** để tiến hành.

### Bước 4: Kích hoạt hoặc Tạo Web App độc lập
- **Batch Activate**: Chọn ngôn ngữ mong muốn ở cụm trên cùng rồi bấm nút **[⚡ Batch Activate Toàn Bộ Máy]**.
- **Tạo Web App**: Nhập link trang web (ví dụ `https://linkm.site/`) vào ô nhập ở Hàng 3 rồi bấm **[🚀 Tạo Web App]**. Trên màn hình iPhone chỉ cần bấm xác nhận cài đặt Profile là icon sẽ hiển thị ngay ngoài màn hình.

---

## 📋 6. Lệnh Trợ Lý Hỗ Trợ (Workflows)

Dự án đã được tích hợp bộ công cụ ghi nhớ và quản trị theo quy chuẩn AWF (Antigravity Workflow):
- `/save_brain`: Lưu lại toàn bộ tiến độ, kiến trúc và quyết định kỹ thuật vào `.brain/`.
- `/recap`: Đọc lại toàn bộ bộ nhớ của dự án để tiếp tục làm việc mà không bị quên bối cảnh.
- `/audit`: Kiểm tra chất lượng mã nguồn, kiểm tra bảo mật và tối ưu hóa hệ thống.

---

**TIKTOOL PRO V4** — *Tối ưu hóa hiệu suất, nâng tầm vận hành nông trại iPhone của bạn.*
