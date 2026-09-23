# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-24 02:37:35 (GMT+9)
**Phiên bản hiện tại**: `4.9.8 Astro Companion UX Edition`  
**Trạng thái**: Bản sửa độ tin cậy Restore đã hoàn tất; kiểm thử tự động **119/119 PASS**. Tài khoản Windows hiện tại đã được cấp Modify trên E: và F:. Còn việc đối soát thủ công các backup của một đợt trước đã restore trên iPhone nhưng nằm lại Kho A.

---

## ✅ PHIÊN 2026-09-24 — SỬA LỖI QUYỀN NTFS, CHUYỂN KHO VÀ BỘ ĐẾM RESTORE

* **Nguyên nhân `WinError 5`**: Sau khi cài lại Windows, tài khoản local mới có SID mới. Các kho NTFS cũ giữ ACL trỏ tới SID trước đó; quyền Read/Write không đủ để thay `Info.plist` atomic hoặc đổi tên/xóa thư mục backup. Tài khoản hiện tại được cấp Modify đệ quy trên E: và F: bằng `icacls /grant ... /T /C /L /Q`. Các từ chối còn lại ở `System Volume Information` là vùng hệ thống, không phải backup.
* **Các lỗi được sửa trong mã**:
  - `tiktool_core._write_info_bytes()` dùng temporary file duy nhất, dọn tệp tạm và đưa thông báo hướng dẫn Modify khi Windows từ chối `os.replace()`.
  - Thêm `move_restored_backup()` để đổi tên cùng volume an toàn, chọn tên đích khác khi trùng/race, thử lại quyền truy cập bị từ chối tối đa 9 lần và dùng copy đã fingerprint khi khác volume.
  - Sửa nhánh copy khác volume chỉ cleanup đích nếu lượt chạy đã tạo đích đó.
  - `BB_RB.App._restore_worker()` phân biệt rõ restore trên iPhone thành công với việc chuyển backup thất bại; bộ đếm theo đợt cập nhật đồng bộ để banner không báo thiếu máy khi UI queue trễ.
* **Kết quả thực tế**: Log `tiktool-20260924-021205.log` có 18/18 `Restore Successful`, 18/18 chuyển kho, không có lỗi chuẩn bị/chuyển kho; 9/9 Batch Activate ở đợt đầu thành công. Banner 8 máy trong đợt 9 máy là lỗi bộ đếm và đã được sửa.
* **Kiểm thử**: 119/119 unit tests PASS. Có test cho đích trùng/race, quyền bị từ chối tạm thời/vĩnh viễn, cleanup temporary và banner khi UI queue trễ.
* **Ảnh hưởng dữ liệu / việc còn lại**: Mã chỉ ghi `Info.plist` khi gắn UDID đích; payload backup không bị sửa bởi helper. Tám backup của đợt trước restore thành công trên điện thoại nhưng chuyển kho thất bại vẫn ở Kho A và `Info.plist` có thể mang UDID đích. Một backup bị từ chối lúc chuẩn bị còn tệp tạm `Info.plist.tmp`; `Info.plist` gốc vẫn đọc được và backup qua kiểm tra cấu trúc. Sau khi cấp quyền, cần chuyển tám backup còn lại sang kho đối diện và chỉ chạy lại máy chưa restore. Các đường dẫn/cấu hình `settings.json` thuộc người dùng, không đưa vào commit.

---

## 📍 ĐANG LÀM & TIẾN ĐỘ TỔNG THỂ
* **Tác vụ vừa hoàn tất (phiên 2026-09-24)**:
  1. Điều tra và sửa lỗi Restore `WinError 5`/`WinError 183` sau khi cài lại Windows; giữ source backup an toàn khi chuyển kho thất bại.
  2. Sửa bộ đếm/banner Restore bị thiếu một máy do UI queue cập nhật trễ.
  3. Cấp quyền Modify trên E:/F: cho tài khoản hiện tại; xác nhận 18/18 restore + chuyển kho thành công ở hai đợt, Activate 9/9; 119/119 tests PASS.
* **Tác vụ hoàn tất trước đó (phiên 2026-09-23)**:
  1. Sửa lỗi bot Astro hiển thị sai trạng thái cho các thao tác chưa được ánh xạ (`devmode`, `clear_crashlog`, `block_update`/`unblock_update`, `erase`, `shutdown`, `reboot`).
  2. Thêm 6 trạng thái mới, lời thoại luân phiên và hoạt ảnh riêng theo từng thao tác; sửa tương tác bấm vào bot.
  3. Đồng bộ phiên bản: `APP_VERSION` nâng từ `4.9.6` lên `4.9.8` (khắc phục lệch giữa mã nguồn và tài liệu).
* **Tiến độ**: 
  - Giai đoạn 1: Nâng cấp Binary libimobiledevice v1.4.0 & Sửa bão log Restore ✅ (Hoàn tất 2026-09-12)
  - Giai đoạn 2: Tự động Bật Developer Mode cho cả dàn iOS 16+ ✅ (Hoàn tất 2026-09-12)
  - Giai đoạn 3: Cẩm nang toàn thư kiến trúc libimobiledevice & Quản trị farm HTML v4 ✅ (Hoàn tất 2026-09-13)
  - Giai đoạn 4: Tích hợp Profile Apple tvOS 26 Beta chặn OTA hàng loạt (hạn 2027) ✅ (Hoàn tất 2026-09-20)
  - Giai đoạn 5: Tự động hóa Gỡ chặn Update qua `ios.exe profile remove` ✅ (Hoàn tất 2026-09-20)
  - Giai đoạn 6: Kiểm thử tự động (84/84 PASS) & Lưu trữ bộ nhớ vĩnh viễn (`/save_brain`) ✅ (Hoàn tất 2026-09-20)
  - Giai đoạn 7: Nâng cấp bot đồng hành Astro (trạng thái đầy đủ + lời thoại luân phiên + hoạt ảnh riêng) & đồng bộ phiên bản 4.9.8 ✅ (Hoàn tất 2026-09-23)
  - Giai đoạn 8: Sửa độ tin cậy Restore NTFS/chuyển kho, bộ đếm theo đợt và lưu kết quả bàn giao ✅ (Hoàn tất 2026-09-24)

---

## ✅ CHI TIẾT HẠNG MỤC HOÀN TẤT TRONG PHIÊN 2026-09-23 (v4.9.8)

### 1. Sửa Lỗi Bot Astro Hiển Thị Sai Trạng Thái
* **Hiện tượng**: Trong lúc dàn máy đang bật Developer Mode, xóa crash log, chặn/gỡ chặn Update, Reset dòng 2, tắt nguồn hoặc khởi động lại, bot vẫn hiển thị *"Đã kết nối N máy sẵn sàng. Sếp bấm nút là nạp ngay!"* như đang rảnh.
* **Nguyên nhân**: `App._resolve_mascot_state` chỉ ánh xạ `restore`, `install_ipa`, `activate`/`language`/`webclip`, `backup`, `auto_activate`; các operation kind còn lại rơi vào nhánh cuối và bị coi là rảnh.
* **Khắc phục**: Ánh xạ đủ 14 operation kind với thứ tự ưu tiên `erase` > `restore` > `install_ipa` > `noota` > `devmode` > `crashlog` > `activate` > `backup` > `shutdown` > `power` > `auto_activate` > `alert` > `idle`.

### 2. Thêm Trạng Thái, Lời Thoại Luân Phiên và Hoạt Ảnh Riêng
* **6 trạng thái mới** trong `STATE_STYLES`: `devmode` (#22D3EE), `crashlog` (#94A3B8), `noota` (#F59E0B), `erase` (#EF4444), `shutdown` (#F97316), `power` (#FBBF24).
* **Lời thoại luân phiên**: `STATE_STYLES` chuyển sang tuple nhiều câu mỗi trạng thái; `ROTATE_EVERY_TICKS = 80` (~6.4 giây) cùng `_rotate_message()` đổi câu khi trạng thái không đổi.
* **Hoạt ảnh riêng** (`ANIMATED_STATES` vẽ lại mắt mỗi khung hình): vòng xoay Dev Mode, vệt quét crash log, cung khiên NOOTA, khung cảnh báo Reset, mắt mờ dần khi tắt nguồn, điểm dữ liệu backup. Toàn bộ vẽ thuần Canvas, **không thêm file ảnh** ➔ giữ zero-pip.
* **Sửa nháy mắt** trong trạng thái `activate` (trước đây bị vẽ lại liên tục nên không thấy).
* **Bổ sung tiến độ** cho `backup` trong `_refresh_mascot_state`.

### 3. Sửa Tương Tác Bấm Vào Bot
* Trước đây câu đùa chỉ hiện 180ms rồi bị `set_state` ghi đè; vòng refresh của poll (~0.3s) cũng xóa ngay.
* Nay dùng mốc `_poke_until` với `POKE_HOLD_SECONDS = 3.0`; `POKE_LINES` mở rộng từ 4 lên 12 câu.

### 4. Đồng Bộ Phiên Bản
* Nâng `APP_VERSION` trong [tiktool_core.py](file:///c:/TIKTOOL%20PRO%20V4/tiktool_core.py) từ `4.9.6` lên `4.9.8` (footer hiển thị `v4.9.8 • libimobiledevice v1.4.0`).

### 5. Kiểm Thử
* Thêm 6 test trong `MascotStateTests` ([tests/test_app_workflows.py](file:///c:/TIKTOOL%20PRO%20V4/tests/test_app_workflows.py)): ánh xạ đủ 14 loại thao tác, `erase` thắng `restore`, mọi trạng thái có màu + câu, lời thoại đổi câu, câu đùa không bị poll xóa, hoạt ảnh không tràn canvas.
* **113/113 unit tests PASS (100%)**.

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

### 3. Quy Tắc Bảo Trì Bot Đồng Hành Astro
* **Thêm operation kind mới**: Phải cập nhật đồng thời **3 chỗ** — `STATE_STYLES`, `_resolve_mascot_state` và nhánh đếm `active_count` trong `_refresh_mascot_state`. Bỏ sót một chỗ là bot sẽ hiển thị nhầm trạng thái rảnh trong lúc máy đang chạy.
* **Hoạt ảnh**: Vẽ thuần hình học bằng Canvas, gắn tag `('robot', 'fx')` để được dọn cùng, và phải nằm trong canvas 76x64. Lưu ý `bbox` của Tk tính thêm nửa độ dày outline nên cần chừa biên.
* **Trạng thái trong `ANIMATED_STATES`** được vẽ lại mắt mỗi khung hình ➔ hiệu ứng nháy mắt bằng `itemconfigure('eyes', state='hidden')` không còn tác dụng, phải vẽ nháy trực tiếp trong `_draw_eyes`.
* **Câu đùa khi bấm** (`_poke`) dùng mốc `_poke_until` (`POKE_HOLD_SECONDS = 3.0`); không được để `set_state` hoặc `_rotate_message` ghi đè trong thời gian giữ.
* **Giọng điệu**: Vui cho `idle_*`/`backup`/`celebrate`, nhưng nghiêm túc và ngắn gọn cho `erase`, `shutdown` và `alert`.
* **Không thêm file ảnh**: BB_RB.py giữ ràng buộc zero-pip 100% chuẩn Tkinter.

---

## 📁 CÁC FILE QUAN TRỌNG TRONG HỆ THỐNG

| Đường dẫn file | Mô tả & Chức năng |
|---|---|
| [`BB_RB.py`](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py) | Ứng dụng chính TIKTOOL PRO V4: Quản lý dàn máy, Restore/Backup, Cài IPA, Bật Developer Mode, Chặn/Gỡ Chặn Update iOS |
| [`NOOTA_tvOS26_signed.mobileconfig`](file:///c:/TIKTOOL%20PRO%20V4/NOOTA_tvOS26_signed.mobileconfig) | File cấu hình Apple tvOS 26 Beta đã ký số chính thức (Apple Root CA, hạn 2027-05-20) |
| [`ios.exe`](file:///c:/TIKTOOL%20PRO%20V4/ios.exe) | Công cụ quản trị iOS đa năng: prepare, skip-all, setlang, profile add/remove/list |
| [`tiktool_core.py`](file:///c:/TIKTOOL%20PRO%20V4/tiktool_core.py) | Lõi thực thi ngầm: Phiên bản 4.9.8, lọc ANSI VT100, điều phối subprocess an toàn |
| [`idevicedevmodectl.exe`](file:///c:/TIKTOOL%20PRO%20V4/idevicedevmodectl.exe) | Quản lý Developer Mode iOS 16+ qua dịch vụ com.apple.amfi.lockdown |
| [`TONG_HOP_KIEN_THUC_LIBIMOBILEDEVICE_TIKTOOL.html`](file:///c:/TIKTOOL%20PRO%20V4/TONG_HOP_KIEN_THUC_LIBIMOBILEDEVICE_TIKTOOL.html) | Toàn thư cẩm nang kiến trúc libimobiledevice & Quản trị farm (Đã cập nhật Chương 8 bằng Tailwind CSS v4) |
| [`CHAN_UPDATE_IOS_VA_TIKTOK_BACKUP_RESTORE.html`](file:///c:/TIKTOOL%20PRO%20V4/CHAN_UPDATE_IOS_VA_TIKTOK_BACKUP_RESTORE.html) | Bản tin chuyên sâu: Chặn & Gỡ Update iOS tvOS 26 Beta, mốc hạn 2027 và an toàn dữ liệu phôi TikTok Lite (Tailwind CSS v4) |
| [`CHANGELOG.md`](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md) | Nhật ký thay đổi phiên bản (Cập nhật bản v4.9.8) |
| [`tests/test_app_workflows.py`](file:///c:/TIKTOOL%20PRO%20V4/tests/test_app_workflows.py) | Kiểm thử hồi quy luồng công việc, gồm `MascotStateTests` cho bot Astro |
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
  - **113/113 unit tests PASS (100%)** — Thời gian thực thi: `~5.5s` (bao gồm 6 test mới của `MascotStateTests`).
