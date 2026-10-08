# Nhật ký sửa Restore chuyển kho và Auto Activate — 08/10/2026

## Phạm vi và tình trạng bàn giao

Sửa luồng Restore theo đợt và Skip Setup của Auto Activate trong TIKTOOL PRO V4 4.9.8. Các thay đổi nằm trong `BB_RB.py`, `tiktool_core.py`, `tests/test_restore_batch.py`, `tests/test_app_workflows.py` và `CHANGELOG.md`.

Restore đã có bằng chứng chạy thực tế thành công sau bản sửa. Bản sửa Auto Activate mới được kiểm chứng bằng unit test; chưa xác nhận trên thiết bị thật. Lỗi driver Apple vẫn tồn tại và không được xem là đã khắc phục tận gốc.

## 1. Sự cố ban đầu và bằng chứng

- Người dùng vừa cài lại Windows, đã cấp lại quyền toàn bộ ổ D. Restore Kho A ↔ Kho B vẫn gặp `Could not receive from mobilebackup2 (-256)` và `Restore Aborted`.
- Người dùng xác nhận không rút/cắm dây hoặc thay đổi nguồn hub lúc 19:03:29.
- Log `logs/tiktool-20261008-185806.log`: đợt lỗi lúc 19:03:29 có 4/14 máy thành công, 10 máy bị hủy.
- Kiểm tra quyền và mở file backup: tài khoản hiện tại có quyền Modify; kiểm tra đọc/mở các thư mục backup và Info.plist không phát hiện lỗi quyền tương ứng. Các file payload được nhắc trong lỗi cũng đọc được. Bằng chứng này không ủng hộ việc quy lỗi hiện tại cho NTFS.
- Windows ghi nhận DriverFrameworks UserMode 10110/10116 cùng thời điểm: driver host dừng và Apple Mobile Device USB Device offline. Windows Error Reporting 1001 ghi `WUDFVerifierFailure` với `AppleUsbFilter.dll`.
- Driver được kiểm tra có phiên bản file 538.0.0.0, ngày 14/06/2023, chữ ký Microsoft Windows Hardware Compatibility Publisher hợp lệ. Apple Mobile Device Support 19.4.0.10 được cài ngày 08/10/2026. Windows 10 Pro 22H2 build 19045.6456.

## 2. Thử xử lý driver Windows và trạng thái còn lại

- Đã thử repair Apple Mobile Device Support bằng MSI cache ký bởi Apple. MSI trả mã 1641 và gây reboot Windows lúc 19:20:10 dù đã truyền `/norestart`; các bước sau repair bị gián đoạn. Đã sửa script để thêm `REBOOT=ReallySuppress REBOOTPROMPT=S`, nhưng không chạy repair lại.
- Sau repair, lỗi driver vẫn tái xuất hiện: 19:25:28 có 4/14 restore thành công; 19:37:25 có 2/14 thành công.
- Đã thử tắt pooling cho riêng AppleUsbFilter qua `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\WUDF\DebugMode`: `DebugModeFlags=2`, `DebugModeBinaries=AppleUsbFilter.dll`. Đã lưu trạng thái registry trước khi sửa; không có bằng chứng cấu hình này giải quyết được crash.
- Cấu hình registry thử nghiệm chưa được rollback trong phiên làm việc này. Script local `logs/isolate-apple-driver.ps1` hỗ trợ `-Rollback`; không tự chạy rollback khi máy đang làm việc.
- Các script, bản sao registry và log MSI nằm trong `logs/`, được giữ tại máy và không đưa vào commit. Các file tham khảo: `repair-apple-driver.ps1`, `repair-apple-driver-result.json`, `isolate-apple-driver.ps1`, `apple-driver-isolation-backup.json`, `apple-driver-isolation-result.json`, `diagnosis-restore-20261008-190329.txt`.

## 3. Bản sửa Restore theo đợt

Trước đây idevicebackup2 tự reboot máy vừa nạp xong trong khi các máy khác còn truyền dữ liệu. Driver USB crash trong khoảng này có thể làm hủy các lượt restore còn chạy.

- Thêm `RestoreBatchGate` dùng lock và Event để chờ toàn bộ lệnh restore của đợt kết thúc, kể cả các nhánh thất bại.
- Đăng ký đủ thành viên và giữ operation của cả đợt trước khi khởi chạy worker; chặn bắt đầu một đợt Restore khác khi đợt hiện tại chưa xong.
- Restore theo đợt truyền `--no-reboot`; sau khi gate mở mới gửi `idevicediagnostics -u <UDID> restart`.
- Worker nạp xong nhả semaphore truyền dữ liệu trước khi chờ gate, tránh deadlock khi số máy lớn hơn số slot.
- Lỗi pairing, chuẩn bị backup, truyền dữ liệu, exception hoặc khởi chạy thread đều giải phóng thành viên khỏi gate.
- Restore thành công vẫn chuyển backup và cập nhật bộ đếm. Lỗi gửi reboot được báo riêng, không xếp Auto Activate cho máy đó; không khẳng định toàn đợt thành công nếu còn lỗi.
- Log file ghi đủ UDID, tên backup và mã thoát; giao diện hiển thị đầu và cuối UDID để phân biệt các máy trùng tiền tố.
- Giới hạn: máy nạp xong sớm phải chờ máy cuối trước khi reboot. Cơ chế này tránh reboot xen giữa truyền dữ liệu, không sửa bên trong driver Apple.

### Bằng chứng chạy thật sau sửa

Trong `logs/tiktool-20261008-194615.log`, 4 đợt đầu sau sửa có tổng 49 lượt restore thành công:

| Bắt đầu | Hướng | Thành công / số máy | Restore cuối kết thúc | Gửi reboot đầu tiên |
| --- | --- | --- | --- | --- |
| 19:46:37 | B → A | 14/14 | 19:47:51 | 19:47:51 |
| 19:49:32 | B → A | 14/14 | 19:50:49 | 19:50:49 |
| 19:54:50 | B → A | 7/7 | 19:55:40 | 19:55:40 |
| 20:13:08 | A → B | 14/14 | 20:14:24 | 20:14:24 |

Cả 49 backup được chuyển kho; các máy kết nối lại sau reboot. Không có `Restore Aborted` hoặc `Could not receive` trong các đợt này. Windows vẫn ghi crash AppleUsbFilter lúc 20:14:33, sau khi lệnh restore đã kết thúc. Đây là bằng chứng cơ chế trì hoãn reboot có ích trong các lượt quan sát, không phải bảo đảm mọi đợt tương lai đều thành công.

## 4. Chẩn đoán Auto Activate / Skip Setup

- Ảnh Screenshot_3 và log 20:16:56–20:16:57: cả 14 máy timeout Skip Setup sau 40 giây và app gửi lại lệnh `ios prepare --skip-all`.
- Đợt đó cuối cùng 11/14 Auto Activate báo thành công; 3 máy trả lỗi `failed setting cloud config`, ErrorCode 14002, `A cloud configuration is already present on this device`.
- Code giữ `skip_state='sent'` của lần timeout trước nếu lần thử sau lỗi thật, làm thông báo cuối sai thành “không có phản hồi xác nhận”.
- Sự tồn tại cloud configuration không đủ chứng minh máy đã qua Setup Assistant. Lệnh trước có thể đã ghi cấu hình trước khi bị timeout, nên tự gửi lại cả lệnh có nguy cơ đụng cấu hình.
- Chưa chứng minh chạy 14 máy song song là nguyên nhân của timeout. `ios.exe` tại máy báo phiên bản v1.0.172; nguồn upstream dùng để đối chiếu trình tự, không giả định hoàn toàn giống binary đang cài.

## 5. Bản sửa Auto Activate

- Tăng timeout prepare từ 40 lên 120 giây để giảm việc dừng lệnh đang xử lý dở; vẫn có giới hạn thời gian.
- Ghi output từng lần thử, kể cả khi timeout. Mỗi lần thử khởi tạo lại trạng thái kết quả, tránh mang trạng thái timeout cũ sang lỗi mới.
- Khi timeout, đọc ActivationState để chẩn đoán rồi dừng tự gửi lại prepare. Activated chỉ xác nhận kích hoạt, không được dùng để báo Skip Setup thành công.
- Chỉ retry lỗi kết nối rõ ràng trước khi thấy prepare bắt đầu; yêu cầu pairing thành công, chờ 5 giây và xác nhận Activated trước lần thử sau. Không retry khi log cho thấy đã tới các bước xử lý cấu hình hoặc lỗi đã có cloud configuration.
- Chỉ nhận thành công khi `CommandResult.ok` đúng: exit 0, không timeout, không lỗi runner. Output chứa chuỗi `"ok"` không đủ để ghi đè mã thoát lỗi.
- Skip Setup thất bại hoặc chưa xác nhận sẽ dừng trước bước đổi ngôn ngữ. Timeout giữ tiến độ 45% và yêu cầu kiểm tra màn hình thiết bị; không báo xong 100%.
- Thông báo lỗi không tự kết luận iPhone còn ở màn hình Hello và không yêu cầu chạy lại hàng loạt khi chưa kiểm tra thiết bị.
- Giới hạn: chưa bổ sung cơ chế khôi phục một prepare đã ghi cấu hình nhưng chưa hoàn tất; trường hợp này được báo cần kiểm tra thay vì tự ghi lại cấu hình.

## 6. Kiểm chứng và cách áp dụng

- Compile: `python -m py_compile BB_RB.py tiktool_core.py tests/test_app_workflows.py` thành công.
- Bộ unit test đầy đủ: 140 tests PASS. Bản sửa Restore bổ sung 4 test, bao gồm các subcase lỗi; Auto Activate bổ sung 6 test cho output timeout, chặn replay/đổi ngôn ngữ, readiness trước retry, lỗi cuối và exit khác 0 có chuỗi ok.
- Settings được sao lưu trước test và test chạy với đường dẫn settings tạm. So sánh hash xác nhận settings thật không bị test thay đổi.
- Chỉ chạy kiểm thử giả lập; không tự gửi restore, prepare hoặc activate xuống iPhone thật để thử bản sửa Auto Activate.
- Chờ công việc đang chạy kết thúc, đóng app rồi mở lại `TIKTOOL_PRO.pyw` để tải mã mới. File exe đã đóng gói cũ không tự nhận thay đổi source.
- `settings.json` là trạng thái vận hành tại máy (đường dẫn kho, bộ đếm, lựa chọn UI), giữ nguyên ngoài commit.

## Tham khảo

- [Mã nguồn go-ios Prepare](https://github.com/danielpaulus/go-ios/blob/main/ios/mcinstall/prepare.go): trình tự SetCloudConfiguration và các bước tiếp theo.
- [WUDF DebugModeFlags của Microsoft](https://learn.microsoft.com/en-us/windows-hardware/drivers/wdf/registry-values-for-debugging-kmdf-drivers#debugmodeflags): bit 2 tắt driver pooling.

