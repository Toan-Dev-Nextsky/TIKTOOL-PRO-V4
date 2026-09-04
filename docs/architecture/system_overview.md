# 📘 TÀI LIỆU KIẾN TRÚC HỆ THỐNG: BB MANAGER PRO (TIKTOOL PRO V4)

## 1. Giới Thiệu Tổng Quan
**BB MANAGER PRO** là công cụ kỹ thuật chuyên dụng phục vụ việc quản lý, kích hoạt hàng loạt (Batch Activate), sao lưu dữ liệu (Backup) và khôi phục chuyển kho hai chiều (Restore chuyển kho A ➜ B / B ➜ A) cho số lượng lớn iPhone thông qua kết nối USB trên nền tảng Windows.

- **Phiên bản hiện tại**: `4.0.0 Pro Dark Edition`
- **Tập tin chạy chính**: `BB_RB.py`
- **Ngôn ngữ & Thư viện**: Python 3.11, Tkinter GUI, Threading đa luồng, Semaphore, SQLite3, Plistlib.
- **Công cụ nhị phân tích hợp**: `libimobiledevice` (Windows x64) và `ios.exe`.

---

## 2. Các Tính Năng Cốt Lõi

### 2.1. Khôi Phục Chuyển Kho Hai Chiều (Dual Store Restore)
- **Cơ chế chọn kho**: Hỗ trợ chuyển dữ liệu linh hoạt:
  - **Kho A ➜ Kho B**: Dữ liệu từ Kho A (Mục Nhập, viền Xanh Ngọc `#34D399`) sau khi nạp xong sẽ tự động chuyển sang Kho B (Mục Xuất, viền Cam `#FBBF24`).
  - **Kho B ➜ Kho A**: Dữ liệu từ Kho B (Mục Nhập) tự động nạp và chuyển sang Kho A (Mục Xuất).
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

### 2.3. Sao Lưu Dữ Liệu (Backup All)
- Tự động sao lưu toàn bộ thiết bị đang cắm qua lệnh `idevicebackup2.exe backup --full`.
- Cơ chế tự động đổi tên thư mục backup chuẩn hóa: `1_iPhone`, `2_iPhone`... tránh trùng lặp.
- Tùy chọn tự động gỡ bỏ TikTok / TikTok Lite sau khi hoàn tất backup.

---

## 3. Kiến Trúc Giao Diện (Pro Dark High-Contrast Dashboard)
Được thiết kế dựa trên bộ chỉ dẫn **`ui-ux-pro-max-skill`** dành cho *Developer Tool / IDE Dashboard*:

| Vùng giao diện | Vai trò | Màu sắc chủ đạo |
| :--- | :--- | :--- |
| **Nền ứng dụng** | Khung chứa toàn bộ giao diện | Deep Midnight Slate `#0B0F19` |
| **Top Card** | Logo `BB PRO`, Đổi ngôn ngữ, Batch Activate | Elevated Navy Slate `#151E2E`, viền `#2D3B54` |
| **Tab Section** | Chuyển đổi giữa Restore Pro và Backup | Tab active `#0284C7`, inactive `#1A263B` |
| **Stats Title Bar** | Hiển thị `[X máy]` và cụm 3 thẻ BỘ ĐẾM KHO | Nền `#151E2E`, thẻ `#0D1524`, `#064E3B`, `#451A03` |
| **Device Grid** | Lưới thẻ iPhone siêu gọn ~80px (3 cột) | Card `#151E2E`, viền `#10B981` (Trust) / `#EF4444` |
| **Log Terminal** | Nhật ký hệ thống thời gian thực | Dark Box OLED `#050811`, chữ trắng `#F8FAFC` |
| **Status Bar** | Thông số tổng kết nhanh | Badges glowing: Trust, Total, Not Trust, Restored |

---

## 4. Quản Lý Đồng Thời & Độ Tin Cậy (Concurrency & Resilience)
- **Kiểm soát luồng với Semaphore**: Sử dụng `threading.Semaphore` để giới hạn số tác vụ đồng thời, đảm bảo đường truyền USB không bị nghẽn và CPU không quá tải.
- **Polling siêu tốc không delay**: Quét `idevice_id -l` liên tục ở luồng nền với `ThreadPoolExecutor(max_workers=20)` để cập nhật trạng thái cắm/rút thiết bị tức thì.
- **Khóa trạng thái Reboot (RESTORE_LOCK_CACHE)**: Khi thiết bị vừa restore xong sẽ tự động khởi động lại (reboot). Cơ chế khóa cache 35 giây ngăn không cho luồng Polling hiểu nhầm thiết bị rơi vào trạng thái `Not Trust`.
- **Đồng bộ cài đặt JSON tự động**: Quét mtime của `settings.json` mỗi giây một lần để đồng bộ cài đặt ngay cả khi có tiến trình khác can thiệp.

---

## 5. Danh Mục Phím Tắt & Thao Tác Nhanh
- **📂 Chọn**: Bấm vào nút Chọn hoặc click trực tiếp lên đường dẫn để duyệt thư mục.
- **⚡ BẮT ĐẦU RESTORE PRO**: Khởi chạy quy trình ghép nối và nạp chuyển kho.
- **⚡ Active (trên thẻ iPhone)**: Kích hoạt nhanh đơn lẻ cho riêng chiếc iPhone đó.
- **🌐 Lang (trên thẻ iPhone)**: Đổi nhanh ngôn ngữ đơn lẻ cho riêng chiếc iPhone đó.
- **↺ (trên thanh thống kê)**: Reset nhanh bộ đếm "Đã chuyển" về 0 khi bắt đầu ca làm việc mới.
