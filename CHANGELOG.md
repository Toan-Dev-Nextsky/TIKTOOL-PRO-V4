# Nhật Ký Thay Đổi (Changelog) - BB MANAGER PRO

Tất cả những thay đổi và nâng cấp quan trọng của dự án được ghi nhận đầy đủ tại đây.

## [4.8.6 Astro Bot Companion Edition] - 2026-09-06

### Astro Bot — Linh Vật Đồng Hành Theo Trạng Thái Công Việc
- Thêm `AstroBotCompanion(tk.Frame)` bằng Canvas vector thuần Tkinter, không ảnh ngoài và không thêm dependency.
- Astro Bot lơ lửng mượt ở khoảng 12 FPS, chớp mắt tự nhiên, đèn antenna và LED trạng thái phát sáng theo ngữ cảnh; nhấp vào bot để bot nhảy nhẹ và đổi lời động viên.
- Tám sắc thái tự động: chờ cắm máy, máy sẵn sàng, Restore, chờ reboot, Batch Activate, Backup, cảnh báo chưa Trust/lỗi và ăn mừng hoàn tất.
- Bong bóng thoại hiển thị số máy, tiến độ Restore trung bình và hướng dẫn ngắn phù hợp với trạng thái hiện tại.
- Trạng thái Activate có **mắt sao sáng mạnh hơn** (halo tím + lõi trắng) và thêm **hiệu ứng tia lửa điện** quanh thân Astro Bot, thay đổi theo chu kỳ animation để dễ nhận biết pipeline đang kích hoạt.
- Tích hợp an toàn với UI queue: worker nền không chạm trực tiếp Tkinter; trạng thái được gửi về UI thread qua `_set_mascot_state()`.
- Thêm bộ phân giải ưu tiên trạng thái `_resolve_mascot_state()` và 2 unit tests; toàn bộ đạt **37/37 tests**, kiểm tra render đủ 8 trạng thái thành công.

## [4.8.5 Instant Restore Preparation Edition] - 2026-09-05

### ⚡ Xoá Bỏ 10-15 Giây Chờ "Check" Mỗi Lần Ấn Restore
- **Nguyên nhân đo được**: `create_restore_stage()` chạy tới **4 lượt I/O toàn bộ bản backup** cho mỗi máy: `backup_fingerprint(nguồn)` (SHA-256 đọc từng byte) ➜ `shutil.copytree` (copy nguyên bản sang `.tiktool_work\restore-xxxx`) ➜ `backup_fingerprint(nguồn)` lần 2 ➜ `backup_fingerprint(bản copy)` lần 3.
  - Benchmark thật trên `14_iPhone_honginhhng8316` (115 MB / 1053 file, cache nóng, 1 máy): `0.81s + 0.65s + 0.54s` ≈ **2.8 giây/máy** (~460 MB I/O). Cắm 14 iPhone chạy song song trên cùng một ổ đĩa ⇒ ~1.6 GB đọc + 1.6 GB ghi trước khi lệnh restore đầu tiên khởi động ⇒ đúng 10–15 giây chờ.
- **Chuyển sang nạp trực tiếp tại kho (như `IphoneToolPro_V26.04.26`)**: Thêm `prepare_restore_in_place()` — chỉ `validate_backup()` (đọc `Status.plist`) rồi ghi UDID máy đích thẳng vào `Info.plist` của bản backup gốc, sau đó `idevicebackup2 restore` nạp ngay từ thư mục kho. **Không copy, không hash byte.**
  - Benchmark sau khi sửa: **0.004 giây/máy** (nhanh hơn ~700 lần); 14 máy vào lệnh restore gần như tức thì.
- **Hoàn tác an toàn khi restore lỗi (`rollback_restore_info()`)**: Nội dung `Info.plist` nguyên bản được giữ trong RAM; nếu `idevicebackup2 restore` thất bại, ứng dụng ghi lại y nguyên byte cũ để bản backup trong kho không bị mang UDID của máy vừa nạp lỗi. Restore thành công thì bản backup được chuyển kho với UDID mới (đúng như tool cũ) nên Lớp 1 của động cơ ghép nối vẫn nhận đúng máy ở lần sau.
- **Không còn thư mục rác `.tiktool_work` trong luồng Restore**: Restore không tạo staging nên không cần dọn dẹp; `.tiktool_work` chỉ còn dùng cho tác vụ Backup.
- **Dọn code chết**: Xoá `create_restore_stage()`, `_patch_staged_info()`, dataclass `RestoreStage` trong `tiktool_core.py` và hàm `patch_info_plist()` không ai gọi trong `BB_RB.py`.
- **Kiểm thử**: Thay bài test staging bằng 3 bài mới (patch không copy/không sinh `.tiktool_work`, hoàn tác UDID khi restore lỗi, từ chối backup chưa `finished`). Toàn bộ đạt **35/35**.

## [4.8.4 Honest Activation Verification Edition] - 2026-09-05

### 🛠️ Sửa Lỗi Auto Activate "Báo Thành Công Nhưng iPhone Chưa Được Kích Hoạt"
- **Nguyên nhân gốc**: Giai đoạn 2 `ios.exe prepare --skip-all` gán `skip_ok = True` cho **mọi** trường hợp lỗi (timeout 40s, `rc=127` do không tìm thấy `ios.exe`, lỗi khác), sau đó pipeline luôn nhảy tới dòng `Batch Activate hoàn tất thành công` và thanh tiến trình 100%. Trên máy tính khác (thiếu `ios.exe`/bị antivirus chặn, chưa có pairing record, lockdownd chưa sẵn sàng), lệnh thất bại nhưng nhật ký vẫn báo thành công nên phải Activate lại bằng tay.
- **Tiền kiểm công cụ trong worker (`_batch_activate_worker`)**: Kiểm tra `ideviceactivation.exe` và `ios.exe` tồn tại thật trước khi chạy; thiếu file sẽ báo đỏ `Thiếu công cụ bắt buộc` và dừng. Trước đây chỉ nút Batch thủ công kiểm tra, luồng Auto đi tắt nên không được bảo vệ.
- **Xác minh trạng thái kích hoạt thật (`ideviceactivation state`)**: Thêm `query_activation_state()` và `activation_state_is_activated()`; sau Giai đoạn 1 và trước khi kết luận, ứng dụng hỏi lại chính thiết bị. Nếu thiết bị trả về `Unactivated` / `FactoryActivated`, pipeline báo lỗi thay vì báo thành công theo exit code.
- **Giai đoạn 2 báo cáo trung thực (tri-state `ok` / `sent` / `failed`)**:
  - `ok`: iPhone xác nhận đã bỏ qua Setup Assistant → mới được báo `hoàn tất thành công`.
  - `sent`: timeout 40s không có phản hồi (đã tự gửi lại tối đa 3 lần) → báo vàng `Skip Setup chưa xác nhận`, nhắc kiểm tra màn hình iPhone.
  - `failed`: lỗi thật → báo đỏ `Skip Setup Assistant THẤT BẠI` kèm nội dung lỗi gốc và dừng luồng.
- **Tự động re-pair khi gặp lỗi kết nối**: Giai đoạn 2 gặp lỗi `lockdownd` / `connection` / `pair` / `not trusted` sẽ chạy `idevicepair validate` rồi thử lại (3 lần).
- **Không còn nuốt lỗi tiến trình**: `CommandResult.error` (ví dụ `[WinError 2] The system cannot find the file specified`) được ghi thẳng vào nhật ký ở cả Giai đoạn 2 và 3.
- **Luồng Auto Activate được chuẩn bị thiết bị đúng cách (`_auto_activate_launch`)**: Chờ lockdownd phản hồi (tối đa 30s) và xác thực lại pairing trước khi chạy pipeline — hai bước này trước đây nằm trong `_post_restore_activate_worker` nhưng hàm đó đã trở thành code chết không ai gọi. Đã xoá hàm chết và gộp logic vào coordinator.
- **Quét USB ổn định hơn**: `get_connected_udids(timeout=...)` cho phép nâng thời gian chờ; coordinator Auto Activate dùng `timeout=8` để `idevice_id -l` không bị cắt sớm khi cắm dàn 16 máy, tránh reset bộ đếm ổn định.
- **Kiểm thử**: Bổ sung 5 bài test chống báo thành công sai (thiếu công cụ, Skip Setup lỗi, thiết bị vẫn `Unactivated`, timeout không xác nhận, re-pair trước khi Activate). Toàn bộ đạt **33/33**.

## [4.8.3 High-Contrast Store Selection Boxes Edition] - 2026-09-05

### 📁 Nâng Cấp Hộp Chọn Kho Rõ Nét, Nền Trắng, Font To Đậm & Badge Màu Đồng Bộ
- **Hộp chọn thư mục Kho chuẩn thiết kế tương phản cao (High-Contrast Store Input Boxes)**:
  - **MỤC NHẬP (Kho A / Kho B)**:
    - Viền ngoài xanh lục nổi bật `#10B981` (Emerald/Green), độ dày 2px.
    - Nền hộp bên trong màu trắng tinh khiết `#FFFFFF`.
    - Badge trực tiếp bên trái: Nền xanh lục `#10B981`, chữ in hoa màu trắng `MỤC NHẬP (KHO A)` font `Segoe UI 9 Bold`.
    - Đường dẫn thư mục: Chữ màu đen tuyền `#000000`, font to đậm `Segoe UI 10 Bold`, căn trái rõ ràng, dễ đọc từ khoảng cách xa.
  - **MỤC XUẤT (Kho B / Kho A)**:
    - Viền ngoài màu cam nổi bật `#F97316` (Vivid Orange), độ dày 2px.
    - Nền hộp bên trong màu trắng tinh khiết `#FFFFFF`.
    - Badge trực tiếp bên trái: Nền màu cam `#F97316`, chữ in hoa màu trắng `MỤC XUẤT (KHO B)` font `Segoe UI 9 Bold`.
    - Đường dẫn thư mục: Chữ màu đen tuyền `#000000`, font to đậm `Segoe UI 10 Bold`.
  - **KHO BACKUP**:
    - Viền ngoài màu tím nổi bật `#7C3AED` (Vivid Purple), độ dày 2px.
    - Nền hộp bên trong màu trắng `#FFFFFF`.
    - Badge trực tiếp bên trái: Nền tím `#7C3AED`, chữ in hoa màu trắng `KHO BACKUP` font `Segoe UI 9 Bold`.
    - Đường dẫn thư mục: Chữ màu đen tuyền `#000000`, font to đậm `Segoe UI 10 Bold`.
    - Nút `BẮT ĐẦU SAO LƯU (BACKUP ALL)` nâng cấp lên `GradientButton` bo góc 6px với dải màu tím sang xanh dương (`#7C3AED` ➔ `#6D28D9` ➔ `#2563EB`).
- **Cố định màu sắc nhận diện Kho & Border thông minh theo lựa chọn**:
  - **Kho A**: Badge luôn giữ màu Xanh lục `#10B981` đặc trưng. Khi chọn `Kho A ➜ B`, Kho A là nguồn có **border đậm Xanh lục `#10B981` (2px)**. Khi chọn `Kho B ➜ A`, Kho A là đích có **border màu tối `#3A414F` (1px)**.
  - **Kho B**: Badge luôn giữ màu Cam `#F97316` đặc trưng. Khi chọn `Kho B ➜ A`, Kho B là nguồn có **border đậm Cam `#F97316` (2px)**. Khi chọn `Kho A ➜ B`, Kho B là đích có **border màu tối `#3A414F` (1px)**.
  - Màu sắc không bị nhảy loạn hoặc hoán đổi giữa Kho A và Kho B; kho nào được chọn làm nguồn thì viền sáng đậm màu tương ứng, kho còn lại giữ viền tối như bản cũ.
  - Nhấp chuột vào bất kỳ vị trí nào trên hộp (badge, khoảng trắng hoặc đường dẫn) đều mở hộp thoại duyệt thư mục nhanh chóng (`cursor="hand2"`).
- **100% Zero-Pip Dependency**: Giữ vững cấu trúc thư viện chuẩn Python 3.11, vượt qua 24/24 unit test.

## [4.8.2 Rounded Gradient Buttons Edition] - 2026-09-05

### 🔘 Tích Hợp Nút Bấm Bo Góc & Hiệu Ứng Background Gradient (GradientButton)
- **Thiết kế Gradient Rounded Button chuẩn từ bản vẽ thiết kế**:
  - Xây dựng widget tùy biến `GradientButton(tk.Canvas)` với khả năng vẽ dải gradient đa điểm dừng (multi-stop gradient) theo lát cắt cong phương trình đường tròn, tạo góc bo mềm mại `radius=6px` cùng viền bo nhẹ (`subtle border`).
  - Hỗ trợ đầy đủ hiệu ứng tương tác:
    - **Hover (`<Enter>`)**: Dải màu sáng hơn tự nhiên (như `from-emerald-500 to-teal-500`).
    - **Click/Press (`<ButtonPress-1>`)**: Dịch chuyển text 1px tạo phản hồi bấm chân thực (tactile feedback).
    - **Leave (`<Leave>`)**: Phục hồi màu mặc định.
- **Áp dụng cho 2 nút hành động trọng tâm được khoanh vùng**:
  1. **Nút BATCH ACTIVATE (ALL)**:
     - Gradient: `from-emerald-600 to-teal-600` (`#059669` ➔ `#0D9488`), hover: `#10B981` ➔ `#14B8A6`.
     - Bo góc: `radius=6px`, viền `#34D399` sang trọng, kích thước 215×30px.
  2. **Nút BẮT ĐẦU RESTORE PRO**:
     - Kho A ➜ B: Gradient 3 điểm dừng `from-emerald-600 via-teal-600 to-sky-700` (`#059669` ➔ `#0D9488` ➔ `#0369A1`), hover `#10B981` ➔ `#14B8A6` ➔ `#0284C7`, viền `#34D399`.
     - Kho B ➜ A: Gradient 3 điểm dừng `from-blue-600 via-indigo-600 to-sky-700` (`#2563EB` ➔ `#4F46E5` ➔ `#0284C7`), hover `#3B82F6` ➔ `#6366F1` ➔ `#38BDF8`, viền `#38BDF8`.
     - Bo góc: `radius=6px`, chiều cao 38px trải rộng `sticky="ew"`.
- **Áp dụng bổ trợ cho các nút quan trọng khác**:
  - Logo `TikTok Pro`: Bo góc 6px, gradient Electric Blue (`#2563EB` ➔ `#1D4ED8`).
  - Nút `Tạo Web App`: Bo góc 6px, gradient Sky Blue (`#0284C7` ➔ `#0369A1`).
  - Hộp thoại Xác nhận: Nút `XÁC NHẬN RESTORE CHUYỂN KHO` (Gradient Emerald/Teal/Sky) & `HỦY BỎ` (Gradient Red).
- **100% Thuần Python - Zero Pip Dependency**:
  - Vẽ bằng toán học hình học giải tích trên nền `tk.Canvas`, không dùng thư viện ngoài, đảm bảo tương thích 100% trên mọi máy tính.

## [4.8.1 Soft Charcoal Slate Dark Theme Edition] - 2026-09-05

### 🎨 Chuyển Đổi Sang Soft Charcoal Slate Dark Theme (Nhẹ Nhàng & Dịu Mắt)
- **Hệ màu Warm Soft Slate-Charcoal cao cấp từ bản thiết kế mới**:
  - Nền chính ứng dụng: `#1A1D23` (appDark-950: warm soft slate-charcoal, thay vì màu đen kịt `#090D16`, giúp làm việc liên tục cả ngày không mỏi mắt).
  - Nền Panels / Container / Thẻ thiết bị: `#22262E` (appDark-900).
  - Nền Sub-panels / Input / Khối lồng / Slot Tag / Rãnh tiến độ: `#262A33` (appDark-850).
  - Nền Buttons elevated / Nút chức năng: `#2C313C` (appDark-800).
  - Nền Cửa sổ Nhật ký hệ thống (Terminal Log Console): `#1E2229` (êm dịu, dễ đọc text payload và log UDID).
  - Hệ thống viền tinh tế (Clean Subtle Borders): `#3A414F` (appDark-700) và `#343A46` (appDark-750).
- **Cải tiến hiển thị thanh thống kê & Bảng Kho**:
  - Thanh thống kê giữa (Quick Stats Overview): Nền trong suốt `#1A1D23` kết hợp các thẻ pill `#22262E` viền `#3A414F`, số liệu nổi bật rõ ràng.
  - Bảng Kho (Restore & Backup Panel): Nền `#262A33` viền `#3A414F`, các hộp chọn thư mục `#22262E` tạo chiều sâu phân cấp thị giác nhẹ nhàng và hài hòa.
  - Bổ sung chỉ báo trạng thái động cơ `SYSTEM ENGINE ACTIVE` ở góc phải thanh trạng thái chân trang.
- **Giữ trọn 100% Hệ Thống Icon Font Segoe MDL2 Assets & Logic Lõi**:
  - Toàn bộ vector icon PUA Windows tiếp tục hiển thị sắc nét trên nền giao diện soft dark mới.
  - Zero-pip dependency, vượt qua 24/24 unit test.

## [4.8.0 Stitch Dark Theme & Windows Segoe MDL2 Icon Font Edition] - 2026-09-05

### 🎨 Chuyển Đổi Toàn Diện Sang Giao Diện Stitch Dark Theme
- **Bảng màu Tech Dark Slate & Cyan/Emerald cao cấp**:
  - Nền ứng dụng chính: `#090D16` (appDark-950).
  - Nền Panels / Header / Cards: `#0F172A` (appDark-900).
  - Khối con / Sub-cards: `#131E33` (appDark-850).
  - Bảng Kho nâng cao (Restore/Backup Panel): `#16233B` (appDark-850+) với viền `#2E446B`.
  - Nút bấm thứ cấp / Badge: `#1E293B` (appDark-800).
  - Hệ thống viền vi tinh chỉnh: `#26344B` (appDark-750) và `#334155`.
  - Hệ thống chữ Slate: `#F8FAFC` (Slate-50), `#E2E8F0` (Slate-200), `#94A3B8` (Slate-400), `#64748B` (Slate-500).
  - Điểm nhấn: Tech Cyan `#38BDF8`, Tech Emerald `#34D399` / `#059669`, Electric Blue `#2563EB`.
- **Thanh Tiêu Đề Tối Chuẩn Windows (Windows Dark Titlebar)**:
  - Tích hợp hàm `DwmSetWindowAttribute(DWMWA_USE_IMMERSIVE_DARK_MODE)` qua thư viện `ctypes.windll.dwmapi`.
- **Thanh Tiến Trình Gradient Mượt Mà (Canvas GradientProgressBar)**:
  - Vẽ dải chuyển màu liền mạch từ Electric Blue `#2563EB` sang Tech Cyan `#38BDF8`, rãnh trượt tối chìm `#090D16`.

### 🔣 Tích Hợp Icon Font Chính Thức Của Windows (Segoe MDL2 Assets)
- **Thay thế 100% Emoji đen trắng thô sơ**:
  - Toàn bộ các emoji cũ (`⚙️`, `🌐`, `📂`, `📱`, `⚡`, `🚀`, `💡`, `📦`, `💾`, `↺`, `🔑`) đã được thay thế bằng các glyph vector Private Use Area của font `Segoe MDL2 Assets`.
  - Bổ sung lớp hằng số `Icons` quản lý tập trung: `PHONE`, `WARNING`, `GLOBE`, `GEAR`, `LIGHTNING`, `FOLDER`, `SAVE`, `REFRESH`, `ROCKET`, `CLIPBOARD`, `LIGHTBULB`, `PACKAGE`, `CHECK`, `CANCEL`, `KEY`, `ARROW_RIGHT`.
- **Tách Màu Icon Riêng Biệt Cho Thẻ iPhone (DeviceCard)**:
  - Nhãn icon điện thoại riêng biệt: hiển thị màu Tech Cyan `#38BDF8` khi máy Trusted và màu Đỏ `#EF4444` khi Not Trust.
  - Tên máy và phiên bản iOS hiển thị trắng sáng sắc nét `#F8FAFC`.

### 🎛️ Nâng Tông & Tách Biệt Thị Giác Cho Bảng Kho (Restore & Backup Panel)
- **Khắc phục hiện tượng Bảng Kho tiệp màu với các thẻ iPhone bên dưới**:
  - Nâng màu nền Bảng Kho lên `#16233B` cùng viền `#2E446B` và các ô lồng `#0B111D`.
  - Tab `KHÔI PHỤC (RESTORE PRO)`: Dùng màu Electric Blue `#2563EB` sang trọng.
  - Nút `BẮT ĐẦU RESTORE PRO`:
    - Khi chọn Kho A ➜ B: Màu Xanh Lục Emerald `#059669`.
    - Khi chọn Kho B ➜ A: Màu Xanh Electric Blue `#2563EB` (thay vì cyan `#0284C7`), tạo độ tương phản cao và không trùng với text của iPhone cards.

---

## [4.7.2 Auto-Activate Timing & Web App Default Edition] - 2026-09-05

### ⏳ Tăng Thời Gian Chờ Reboot Sau Restore (80s ➜ 100s)
- **Đảm bảo iPhone khởi động hoàn tất trước khi Batch Activate**:
  - Tăng thời gian đếm ngược `TOTAL_WAIT` từ 80 giây lên **100 giây** sau khi Restore xong.
  - Lý do thực tế: Các dòng máy iPhone khi Restore nạp dữ liệu lớn mất từ 60-90 giây để nạp xong SpringBoard và khởi động `lockdownd` daemon. Nếu kích hoạt quá sớm ở mốc 80s máy chưa sẵn sàng sẽ dễ báo lỗi hoặc timeout.
  - Thời gian 100 giây kết hợp với vòng đệm kiểm tra kết nối tối đa 45 giây mang lại tổng thời gian an toàn 145 giây, giúp tỷ lệ kích hoạt thành công đạt mức tối đa và iPhone hoạt động ổn định nhất.

### 🛡️ Lọc Bỏ Cảnh Báo Tunnel & Xử Lý Timeout SpringBoard Khi Đổi Ngôn Ngữ
- **Ẩn cảnh báo vô hại của go-ios**:
  - Lọc bỏ dòng thông báo `go-ios agent is not running...` và `failed to get tunnel info...` khi chạy `ios.exe lang`. Đây là cảnh báo cho daemon/tunnel chế độ thử nghiệm trên iOS 17+, không ảnh hưởng đến giao tiếp USB qua socket thông thường.
- **Xử lý mềm dẻo hiện tượng SpringBoard Reload Timeout (20s)**:
  - Khi đổi ngôn ngữ, iOS buộc phải reload SpringBoard, dẫn đến socket USB bị ngắt trong 1-2 giây và lệnh trả về timeout.
  - Phân biệt rõ ràng giữa timeout do SpringBoard reload và lỗi thực tế: hiển thị log thông tin màu xanh/trắng `⚡ Lệnh đổi ngôn ngữ đã gửi (SpringBoard đang cập nhật, timeout 20s là bình thường)` thay vì gắn cờ đỏ lỗi `is_err=True`.

### 🌐 Mặc Định Để Trống Ô Nhập Link Web App
- **Xóa URL mặc định `https://linkm.site/`**:
  - Thiết lập giá trị mặc định của `customWebclipLink` thành chuỗi rỗng `""` trong cả code `DEFAULT_SETTINGS` và `settings.json`.
  - Người dùng có toàn quyền nhập link web mong muốn hoặc để trống mà không cần phải xóa link gợi ý ban đầu.

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
