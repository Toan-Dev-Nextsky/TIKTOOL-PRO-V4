# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-20 11:05:00 (GMT+7)  
**Phiên bản hiện tại**: `4.9.7 Batch iOS Update Blocker Edition`  
**Trạng thái**: Sẵn sàng hoạt động trong sản xuất (Production Ready) — Đã tích hợp tính năng Chặn & Gỡ Chặn Cập Nhật iOS Hàng Loạt (NOOTA tvOS 26 Beta Profile CMS-Signed từ Apple, hạn dùng đến 20/05/2027), điều phối luồng USB an toàn qua semaphore, giao diện nút bấm Tab Cài IPA; toàn bộ **84/84 tests** kiểm thử tự động PASS 100%.

---

## 📍 ĐANG LÀM & TIẾN ĐỘ TỔNG THỂ
* **Tác vụ vừa hoàn tất**: 
  1. Tích hợp tính năng **Chặn & Gỡ Chặn Cập Nhật iOS Hàng Loạt** (Batch Block / Unblock OTA Update) bằng Profile Apple tvOS 26 Beta đã ký số chính thức (CMS-Signed bởi Apple Root CA).
  2. Bổ sung cụm nút điều khiển chuyên biệt trong **Tab Cài IPA**.
  3. Phân tích chuyên sâu và giải đáp thắc mắc về tính bền vững của Profile và cơ chế nạp/restore phôi backup của dàn farm.
* **Tiến độ**: 
  - Giai đoạn 1: Nâng cấp Binary libimobiledevice v1.4.0 & Sửa bão log Restore ✅ (Hoàn tất 2026-09-12)
  - Giai đoạn 2: Tự động Bật Developer Mode cho cả dàn iOS 16+ ✅ (Hoàn tất 2026-09-12)
  - Giai đoạn 3: Cẩm nang toàn thư kiến trúc libimobiledevice & Quản trị farm HTML v4 ✅ (Hoàn tất 2026-09-13)
  - Giai đoạn 4: Tích hợp Profile Apple tvOS 26 Beta chặn OTA hàng loạt (hạn 2027) ✅ (Hoàn tất 2026-09-20)
  - Giai đoạn 5: Tự động hóa Gỡ chặn Update qua `ios.exe profile remove` ✅ (Hoàn tất 2026-09-20)
  - Giai đoạn 6: Kiểm thử tự động (84/84 PASS) & Lưu trữ bộ nhớ vĩnh viễn (`/save_brain`) ✅ (Hoàn tất 2026-09-20)

---

## ✅ CHI TIẾT CÁC HẠNG MỤC ĐÃ HOÀN TẤT TRONG PHIÊN LÀM VIỆC (2026-09-20)

### 1. Phân Tích & Tuyển Chọn Giải Pháp Chặn Cập Nhật iOS (OTA)
* **Yêu cầu từ thực tế phone farm**:
  - Dàn iPhone làm TikTok thường xuyên bị tự động tải ngầm hoặc nhảy thông báo ép cập nhật iOS 17/18/26, gây nghẽn bộ nhớ, xung đột jailbreak/tweak/chứng chỉ, hoặc làm chậm máy.
  - Cần giải pháp chặn cập nhật **hàng loạt 1 click cho cả dàn**, tương tự tính năng của 3uTools nhưng tích hợp liền mạch ngay trong tool.
* **Đối chiếu 2 phương pháp kỹ thuật**:
  - *Cách 1: Cài Profile Apple tvOS Beta Software Profile (Khuyên dùng & Đã chọn)*:
    - Hoạt động ở tầng sâu hệ điều hành: Đánh lừa tiến trình `MobileSoftwareUpdate` của iOS chuyển hướng tìm bản cập nhật từ máy chủ Apple TV (tvOS). Do iPhone không thể cài tvOS, iOS sẽ luôn báo *"iOS của bạn đã là bản mới nhất"*.
    - **Ưu điểm vượt trội**: Không can thiệp mạng, không đụng chạm DNS hay Local VPN, không xung đột với cục WiFiTock hay proxy tĩnh của dàn farm, không tốn pin hay RAM.
  - *Cách 2: Chặn domain Apple OTA qua DNS / Local VPN*:
    - Xung đột nghiêm trọng với proxy TikTok của dàn farm, dễ bị ngắt kết nối khi đổi mạng, tốn pin.

### 2. Trích Xuất & Thẩm Định Profile Ký Số Hợp Lệ (CMS-Signed)
* **Hiện tượng phát hiện**:
  - File `NOOTA.mobileconfig` đi kèm bản cài sẵn của 3uTools có `RemovalDate: 2026-05-01` ➔ **ĐÃ HẾT HẠN** (nếu cài máy sẽ báo lỗi chứng chỉ không hợp lệ).
* **Giải pháp**:
  - Dò quét cache cập nhật mới nhất của 3uTools và tìm thấy tệp `9CE6C842E107901F37186BAC993911F6.mobileconfig` (kích thước 6.834 bytes).
  - Phân tích cấu trúc nhị phân ASN.1 DER CMS Signature:
    - Ký số chính thức bởi: **Apple iPhone Device CA / Apple Root CA**.
    - Payload Identifier: `com.apple.mobileconfig.embeddedratvOSSoftwareProfile`.
    - Display Name: `tvOS 26 Beta Software Profile`.
    - Ngày hết hạn (`RemovalDate`): **2027-05-20** (Thời hạn bảo hộ dài đến hơn 1 năm, an tâm vận hành).
  - Đưa trực tiếp vào thư mục gốc dự án: [`NOOTA_tvOS26_signed.mobileconfig`](file:///c:/TIKTOOL%20PRO%20V4/NOOTA_tvOS26_signed.mobileconfig).

### 3. Tận Dụng & Mở Rộng Đường Ống `ios.exe profile`
* Tận dụng công cụ `ios.exe` đã được đóng gói sẵn trong dự án:
  - Nạp profile: `ios.exe profile add <path> --udid=<udid> --nojson`
  - Liệt kê profile: `ios.exe profile list --udid=<udid> --nojson`
  - Gỡ profile: `ios.exe profile remove <profileName> --udid=<udid> --nojson`
* **Triển khai trong [`BB_RB.py`](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py)**:
  - **Hằng số**:
    ```python
    NOOTA_PROFILE_FILENAME = "NOOTA_tvOS26_signed.mobileconfig"
    NOOTA_PROFILE_IDENTIFIER = "tvOS 26 Beta Software Profile"
    NOOTA_PAYLOAD_UUID = "com.apple.mobileconfig.embeddedratvOSSoftwareProfile"
    NOOTA_SEMAPHORE = threading.Semaphore(MAX_CONCURRENCY)
    ```
  - **Worker Functions**:
    - `_block_update_worker(udid, card)`: Đẩy profile tvOS 26 qua USB, cập nhật nhãn thẻ thiết bị: *"Đã nạp Profile Chặn Update! Vào Cài đặt để xác nhận cài"*, xuất log chi tiết.
    - `_unblock_update_worker(udid, card)`: Gọi `ios.exe profile list`, trích xuất tên profile có chứa `tvos` hoặc `noota`, sau đó gọi `ios.exe profile remove` xóa sạch, cập nhật thẻ thiết bị: *"Đã gỡ chặn OTA!"*.
  - **Batch Launchers**:
    - `batch_block_update_all()`: Hộp thoại xác nhận ➔ Lọc thiết bị được chọn (hoặc toàn bộ máy online) ➔ Spawn worker có Semaphore điều phối.
    - `batch_unblock_update_all()`: Tương tự, gỡ bỏ đồng loạt cho cả dàn.

### 4. Bổ Sung Giao Diện Người Dùng Trong Tab Cài IPA
* Thêm hàng nút điều khiển `row_noota` nằm ngay dưới khu vực Developer Mode:
  - **`🛡️ Chặn Update iOS (Cả dàn)`**: Màu Amber Gold `#D97706` -> `#B45309`, viền `#F59E0B`.
  - **`🔓 Gỡ Chặn Update (Cả dàn)`**: Màu Emerald Dark `#065F46`, viền `#10B981`.
  - Nhãn hướng dẫn: *(Cài profile tvOS Beta chặn OTA triệt để - Hạn 2027)*.

---

## 🔧 QUY TẮC & KINH NGHIỆM VẬN HÀNH PHÔI FARM (GOTCHAS)

### 1. Tính Bền Vững Của Profile Chặn Update
* **Profile KHÔNG vĩnh viễn**, nhưng lưu giữ rất ổn định:
  - **Không mất khi tắt/bật hay khởi động lại máy (Reboot).**
  - **Chỉ mất trong 4 trường hợp**:
    1. **Reset dòng 2 (Xóa tất cả nội dung & cài đặt)**: Làm sạch toàn bộ máy về xuất xưởng.
    2. **Chạy lại phần mềm (Flash firmware / Restore IPSW)**: Xóa sạch phân vùng hệ thống.
    3. **Hết hạn chứng chỉ Apple**: Profile tvOS 26 này có hạn đến **20/05/2027**.
    4. **Người dùng chủ động gỡ**: Bằng tay trong Cài đặt hoặc qua nút *Gỡ Chặn Update* trên TikTool.

### 2. Restore "Phôi" iPhone Đã Backup Từ Trước Có Mất Không?
* **Cơ chế sao lưu của iOS (iTunes / 3uTools / idevicebackup2)**:
  - Bản backup chỉ lưu trữ app container, ảnh, tin nhắn, keychain, settings cơ bản.
  - **Apple TUYỆT ĐỐI KHÔNG BAO GIỜ sao lưu Profile cấu hình (Configuration Profiles)** vào file backup chuẩn.
* **Ảnh hưởng thực tế**:
  - Nếu quy trình làm farm là: **Reset dòng 2 / Chạy lại máy trắng ➔ Nạp phôi backup**: Profile **CHẮC CHẮN MẤT 100%**.
  - Nếu restore đè backup lên máy đang có profile: Profile có thể còn nhưng một số cấu hình cập nhật có thể bị kích hoạt lại.
* **Quy trình chuẩn cho dàn máy**:
  ```
  [1] Nạp phôi / Restore backup / Setup tài khoản xong xuôi
                         ↓
  [2] Cắm dàn máy vào TIKTOOL PRO V4
                         ↓
  [3] Vào Tab Cài IPA ➔ Bấm "🛡️ Chặn Update iOS (Cả dàn)" (1 click duy nhất)
                         ↓
  [4] Hoàn tất: Toàn bộ dàn máy được bảo vệ an toàn đến 2027!
  ```

---

## 📁 CÁC FILE QUAN TRỌNG TRONG HỆ THỐNG

| Đường dẫn file | Mô tả & Chức năng |
|---|---|
| [`BB_RB.py`](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py) | Ứng dụng chính TIKTOOL PRO V4: Quản lý dàn máy, Restore/Backup, Cài IPA, Bật Developer Mode, Chặn/Gỡ Chặn Update iOS |
| [`NOOTA_tvOS26_signed.mobileconfig`](file:///c:/TIKTOOL%20PRO%20V4/NOOTA_tvOS26_signed.mobileconfig) | File cấu hình Apple tvOS 26 Beta đã ký số chính thức (Apple Root CA, hạn 2027-05-20) |
| [`ios.exe`](file:///c:/TIKTOOL%20PRO%20V4/ios.exe) | Công cụ quản trị iOS đa năng: prepare, skip-all, setlang, profile add/remove/list |
| [`tiktool_core.py`](file:///c:/TIKTOOL%20PRO%20V4/tiktool_core.py) | Lõi thực thi ngầm: Phiên bản 4.9.6+, lọc ANSI VT100, điều phối subprocess an toàn |
| [`idevicedevmodectl.exe`](file:///c:/TIKTOOL%20PRO%20V4/idevicedevmodectl.exe) | Quản lý Developer Mode iOS 16+ qua dịch vụ com.apple.amfi.lockdown |
| [`TONG_HOP_KIEN_THUC_LIBIMOBILEDEVICE_TIKTOOL.html`](file:///c:/TIKTOOL%20PRO%20V4/TONG_HOP_KIEN_THUC_LIBIMOBILEDEVICE_TIKTOOL.html) | Toàn thư cẩm nang kiến trúc libimobiledevice & Quản trị farm (Đã cập nhật Chương 8 bằng Tailwind CSS v4) |
| [`CHAN_UPDATE_IOS_VA_TIKTOK_BACKUP_RESTORE.html`](file:///c:/TIKTOOL%20PRO%20V4/CHAN_UPDATE_IOS_VA_TIKTOK_BACKUP_RESTORE.html) | Bản tin chuyên sâu: Chặn & Gỡ Update iOS tvOS 26 Beta, mốc hạn 2027 và an toàn dữ liệu phôi TikTok Lite (Tailwind CSS v4) |
| [`CHANGELOG.md`](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md) | Nhật ký thay đổi phiên bản (Cập nhật bản v4.9.7) |
| [`.brain/brain.json`](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json) | Bộ nhớ tri thức kiến trúc, pipelines và quy tắc gotchas vĩnh viễn |
| [`.brain/session.json`](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json) | Bộ nhớ trạng thái phiên làm việc hiện tại |
| [`.brain/handover.md`](file:///c:/TIKTOOL%20PRO%20V4/.brain/handover.md) | Tài liệu bàn giao chi tiết cho phiên làm việc tiếp theo |

---

## 🧪 KẾT QUẢ KIỂM THỬ TỰ ĐỘNG
* **Cú pháp Python (`py_compile`)**:
  - `BB_RB.py`: Clean ✅
  - `tiktool_core.py`: Clean ✅
  - `TIK_SIGNER.py`: Clean ✅
* **Kiểm thử hồi quy (`python -m unittest discover -s tests`)**:
  - **84/84 unit tests PASS (100%)** — Thời gian thực thi: `0.38s`.
