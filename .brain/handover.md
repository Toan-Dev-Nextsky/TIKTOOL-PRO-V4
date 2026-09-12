# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-12 19:47:00 (GMT+7)  
**Phiên bản hiện tại**: `4.9.5 libimobiledevice v1.4.0 & Batch Developer Mode Edition`  
**Trạng thái**: Sẵn sàng hoạt động trong sản xuất (Production Ready) — Đã nâng cấp toàn diện bộ công cụ kết nối iOS lên `libimobiledevice v1.4.0-9` (OpenSSL 3.x, Zstandard), xử lý triệt để sự cố bão log và đơ giật giao diện Restore, tích hợp tính năng tự động Bật Developer Mode cho cả dàn iPhone qua USB; 65/65 tests kiểm thử tự động PASS 100%.

---

## 📍 ĐANG LÀM & TIẾN ĐỘ TỔNG THỂ
* **Tác vụ vừa hoàn tất**: Nâng cấp `libimobiledevice v1.4.0`, sửa thuật toán đọc tiến độ tránh bão log, bổ sung tính năng Bật Developer Mode hàng loạt cho iOS 16+.
* **Tiến độ**: 
  - Giai đoạn 1: Nâng cấp Binary & Thư viện liên kết (`jrjr/libimobile-suite-latest_w64`) ✅ (Hoàn tất)
  - Giai đoạn 2: Sửa lỗi bão log & tối ưu hóa luồng giao diện Tkinter ✅ (Hoàn tất)
  - Giai đoạn 3: Kiểm thử thực tế trên dàn 4 iPhone và xác nhận kết quả sạch ✅ (Hoàn tất)
  - Giai đoạn 4: Tạo tài liệu báo cáo nâng cấp trực quan dạng HTML Tailwind CSS v4 ✅ (Hoàn tất)
  - Giai đoạn 5: Tích hợp công cụ `idevicedevmodectl.exe` & tính năng Bật Developer Mode cho cả dàn ✅ (Hoàn tất)
  - Giai đoạn 6: Bổ sung Unit Tests (65/65 PASS) & Lưu trữ bộ nhớ vĩnh viễn (`/save_brain`) ✅ (Hoàn tất)

---

## ✅ CHI TIẾT CÁC HẠNG MỤC ĐÃ HOÀN TẤT TRONG PHIÊN LÀM VIỆC (2026-09-12)

### 1. Nâng Cấp Toàn Diện Bộ Nhị Phân `libimobiledevice` Lên v1.4.0
* **Hiện trạng cũ**: Bản 1.3.0-git (từ năm 2020), OpenSSL 1.1 cũ, gặp lỗi kinh điển tính toán sai dung lượng ổ đĩa trống trên Windows khi sao lưu dữ liệu lớn.
* **Nâng cấp mới**:
  - Đồng bộ 45 file nhị phân `.exe` và thư viện động `.dll` từ bản đóng gói chính thống `jrjr/libimobile-suite-latest_w64` (phiên bản `v1.4.0-9-gfa0f791`).
  - Nâng cấp OpenSSL 3.x, bổ sung thư viện nén giải nén hiệu năng cao `zstd` (Zstandard) và `brotli`.
  - Giữ lại an toàn các công cụ chuyên dụng: `ideviceinstaller.exe`, `ideviceactivation.exe`, `idevicerestore.exe`.
  - Toàn bộ phiên bản cũ được sao lưu nguyên vẹn tại: `c:\TIKTOOL PRO V4\backup_libimobiledevice_20260912_185131/`.

### 2. Khắc Phục Triệt Để Sự Cố "Giao Diện Chạy Loạn Không Dừng" Khi Restore
* **Nguyên nhân cốt lõi**:
  - `idevicebackup2.exe v1.4.0` đổi cách xuất tiến độ sang khối 4 dòng giả lập terminal VT100:
    - Dòng 1: `Backup [####] 21%` (Tiến độ tổng thể của thiết bị, số nguyên).
    - Dòng 3: `[=====>] 32.8% 688 KB / 2.1 MB` (Tiến độ của file con đang nạp, số thập phân).
  - Biểu thức chính quy cũ `(\d{1,3})\s*%` đã bắt nhầm số `8%` từ `32.8%`, khiến thanh tiến độ của máy giật liên tục giữa `21%` và `8%` hàng trăm lần mỗi giây.
  - Sự lặp lại không ngừng đẩy 43.761 dòng log vào Tkinter Text Widget, làm nghẽn hàng đợi giao diện khiến người dùng thấy ứng dụng "chạy loạn không dừng".
* **Giải pháp đã triển khai**:
  - **Tầng thấp (`tiktool_core.py`)**: Tự động lọc sạch toàn bộ mã thoát con trỏ ANSI VT100 (`\033[2K`, `\033[1G`) bằng `ANSI_ESCAPE_RE`.
  - **Tầng phân tích tiến độ (`BB_RB.py`)**:
    - Nâng cấp hàm `_parse_any_percent`: Bỏ qua các dòng chứa số thập phân (`\d+\.\d+%`), chứa đơn vị kích thước (`KB`, `MB`, `GB`, `Bytes`), hoặc chứa thanh tiến trình con (`>`).
    - Nâng cấp hàm `_should_log_stream_line`: Chặn triệt để việc ghi lặp lại cùng một mốc phần trăm (`pct == last_pct`), bỏ qua các dòng tài nguyên phụ bắt đầu bằng `Sending` hoặc `Receiving`.
    - Điều tiết sự kiện UI (`on_line`): Chỉ kích hoạt `row.set_pct()` khi phần trăm thực sự thay đổi giá trị.
* **Kết quả đo lường thực tế**:
  - Dữ liệu nhật ký giảm từ **43.761 dòng (3.36 MB)** xuống chỉ còn **281 dòng (24.5 KB)** (giảm **99.4%** log rác).
  - Dàn 4 iPhone restore thành công 100%, nhảy từ Restore sang Tự động kích hoạt (Auto Activate) cực kỳ mượt mà, không đơ lag.

### 3. Tích Hợp Tính Năng "Bật Developer Mode Cho Cả Dàn" (`idevicedevmodectl.exe`)
* **Bối cảnh**: iOS 16, 17, 18 yêu cầu bắt buộc phải bật *Developer Mode* (Chế độ nhà phát triển) mới cho phép mở app TikTok Lite nạp qua file IPA ký riêng. Bật tay trên từng máy tốn nhiều thời gian.
* **Triển khai**:
  - Bổ sung nút bấm **`⚡ DEV MODE (ALL)`** trên Thanh Điều Khiển Hàng 1 (bên cạnh nút Kích hoạt hàng loạt).
  - Bổ sung nút **`⚡ Bật Developer Mode (Cả dàn)`** trong khung tùy chọn tab Cài IPA.
  - Bổ sung nút lệnh riêng lẻ trên từng thẻ thiết bị (`DeviceCard._trigger_single_devmode`).
* **Cơ chế xử lý thông minh (`_devmode_worker`)**:
  - Tự động kiểm tra phiên bản iOS: Bỏ qua máy iOS < 16 (không hỗ trợ/không cần thiết).
  - Kiểm tra trạng thái hiện tại qua `idevicedevmodectl list`: Nếu đã bật thì ghi nhận hoàn tất ngay.
  - Nếu chưa bật:
    - Đăng ký `reboot_tracker.mark(udid, 90.0)` để giữ trạng thái an toàn trên UI khi iPhone khởi động lại.
    - Gọi `idevicedevmodectl enable`:
      - **Máy không có Passcode**: Công cụ tự động kích hoạt, tự khởi động lại máy và tự xác nhận bật Developer Mode 100% không cần chạm vào màn hình iPhone.
      - **Máy có Passcode**: Thiết bị từ chối arm từ xa qua USB; công cụ tự động chuyển sang chế độ `DEV_MODE_REVEAL` để mở sẵn menu *Cài đặt -> Quyền riêng tư & Bảo mật -> Chế độ nhà phát triển* giúp thao tác cực nhanh.
  - Quản lý đồng thời an toàn bằng `OperationRegistry` và `SEMAPHORE`.

### 4. Báo Cáo Nâng Cấp Trực Quan Chuẩn HTML/CSS Tailwind CSS v4
* Đã tạo file: [`BAO_CAO_NANG_CAP_LIBIMOBILEDEVICE_V1.4.html`](file:///c:/TIKTOOL%20PRO%20V4/BAO_CAO_NANG_CAP_LIBIMOBILEDEVICE_V1.4.html)
* Thiết kế Dark Mode hiện đại, sử dụng Tailwind CSS v4 (Play CDN), bảng đối chiếu tính năng 1.3.0 vs 1.4.0, biểu đồ so sánh hiệu năng và hướng dẫn vận hành chi tiết.

### 5. Kiểm Thử Tự Động Toàn Diện
* Bổ sung lớp kiểm thử `DeveloperModeTests` trong `tests/test_app_workflows.py` (kiểm tra bỏ qua iOS < 16, xử lý máy đã bật, cơ chế kích hoạt tự reboot, và chống chạy trùng lặp tác vụ).
* Tổng số bài kiểm thử tăng từ 58 lên **65 tests**.
* **100% tests PASS (65/65)** chỉ trong 0.32 giây.

---

## 🔧 CÁC QUYẾT ĐỊNH KỸ THUẬT QUAN TRỌNG

1. **Giữ Vững Nguyên Tắc Zero-Pip Cho Ứng Dụng Chính**:
   - Ứng dụng chính `BB_RB.py` chạy hoàn toàn bằng Python chuẩn + Tkinter mặc định, không yêu cầu cài thêm thư viện bên ngoài qua pip.
2. **Khử Mã ANSI Ngay Tại Tầng Thấp**:
   - `tiktool_core.py` xử lý sạch ký tự VT100 trước khi dữ liệu đến tay GUI, bảo vệ toàn diện các module khác trong tương lai khỏi lỗi giật màn hình terminal.
3. **Phân Tách Dòng Tiến Độ File Con Khỏi Tiến Độ Tổng**:
   - Loại trừ triệt để các chuỗi có định dạng `float%` (như `32.8%`) và đơn vị dữ liệu (`KB/MB`) để chỉ giữ lại tiến độ tổng nguyên vẹn của thiết bị.
4. **Bảo Vệ Luồng Tkinter Với RebootTracker**:
   - Khi thiết bị khởi động lại để kích hoạt Developer Mode hoặc sau khi Restore, `reboot_tracker` ghi nhận thời gian chờ 90s, ngăn hệ thống ngắt kết nối hoặc chuyển trạng thái sang "Not Trust" sai thực tế.

---

## ⚠️ LƯU Ý QUAN TRỌNG KHI VẬN HÀNH DÀN MÁY

1. **Lỗi `MismatchedApplicationIdentifierEntitlement` Khi Cài IPA**:
   - **Hiện tượng**: Quá trình cài IPA báo lỗi không khớp `application-identifier`.
   - **Nguyên nhân**: Trên iPhone đang có sẵn bản app TikTok Lite được cài từ trước bằng một chứng chỉ khác (hoặc khác Team ID).
   - **Cách xử lý**: Bấm gỡ ứng dụng cũ trên thiết bị trước, sau đó bấm cài đặt bản IPA mới ký.
2. **Dàn Máy Có Mật Khẩu Khóa Màn Hình (Passcode)**:
   - Khi chạy Developer Mode cho máy có passcode, sau khi tool hoàn tất, vào *Cài đặt -> Quyền riêng tư & Bảo mật -> Chế độ nhà phát triển* để gạt Bật và nhập passcode xác nhận một lần duy nhất.
   - Để tự động hóa 100% không cần chạm tay, nên tắt passcode trên dàn máy làm phôi.
3. **Phôi App Store vs Phôi Cài Qua Chứng Chỉ Riêng**:
   - Nếu máy đích đã tải app TikTok Lite trực tiếp từ App Store, khi restore phôi sẽ nhận app ngay mà **KHÔNG cần bật Developer Mode** và **KHÔNG tốn chứng chỉ**.
   - Chỉ các máy cài app qua file IPA ký riêng (`.ipa`) mới bắt buộc bật Developer Mode.

---

## 📁 CÁC FILE QUAN TRỌNG TRONG HỆ THỐNG

| Đường dẫn file | Mô tả & Chức năng |
|---|---|
| [`BB_RB.py`](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py) | Ứng dụng chính TIKTOOL PRO V4: Quản lý dàn máy, Restore/Backup, Cài IPA, Bật Developer Mode, Grid IPA 3 cột |
| [`tiktool_core.py`](file:///c:/TIKTOOL%20PRO%20V4/tiktool_core.py) | Lõi thực thi ngầm: Lọc mã màu ANSI, điều phối luồng subprocess, phát sự kiện an toàn |
| [`idevicedevmodectl.exe`](file:///c:/TIKTOOL%20PRO%20V4/idevicedevmodectl.exe) | Nhị phân mới v1.4.0 quản lý Developer Mode iOS 16+ qua dịch vụ com.apple.amfi.lockdown |
| [`BAO_CAO_NANG_CAP_LIBIMOBILEDEVICE_V1.4.html`](file:///c:/TIKTOOL%20PRO%20V4/BAO_CAO_NANG_CAP_LIBIMOBILEDEVICE_V1.4.html) | Báo cáo chi tiết kỹ thuật nâng cấp v1.4.0 (Tailwind CSS v4 Dark Mode) |
| [`TIK_SIGNER.py`](file:///c:/TIKTOOL%20PRO%20V4/TIK_SIGNER.py) | Ứng dụng ký IPA hàng loạt độc lập (ttkbootstrap Darkly Theme) |
| [`CHAY_SIGNER.bat`](file:///c:/TIKTOOL%20PRO%20V4/CHAY_SIGNER.bat) | File khởi chạy 1-click cho công cụ TIK SIGNER PRO |
| [`CHANGELOG.md`](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md) | Nhật ký thay đổi phiên bản (Cập nhật bản v4.9.5) |
| [`.brain/brain.json`](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json) | Bộ nhớ tri thức kiến trúc, pipelines và quy tắc gotchas vĩnh viễn |
| [`.brain/session.json`](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json) | Bộ nhớ trạng thái phiên làm việc hiện tại |
| [`.brain/handover.md`](file:///c:/TIKTOOL%20PRO%20V4/.brain/handover.md) | Tài liệu bàn giao chi tiết cho phiên làm việc tiếp theo |
| `backup_libimobiledevice_20260912_185131/` | Thư mục sao lưu toàn bộ 45 file nhị phân v1.3.0 cũ |

---

## 🧪 KẾT QUẢ KIỂM THỬ TỰ ĐỘNG
* **Cú pháp Python (`py_compile`)**:
  - `BB_RB.py`: Clean ✅
  - `tiktool_core.py`: Clean ✅
  - `TIK_SIGNER.py`: Clean ✅
* **Kiểm thử hồi quy (`unittest discover -s tests`)**:
  - **65/65 unit tests PASS (100%)** — Thời gian thực thi: `0.32s`.
