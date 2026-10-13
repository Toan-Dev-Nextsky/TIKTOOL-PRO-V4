# Restore đã nạp xong nhưng chờ reboot — 13/10/2026

## Bằng chứng

Ảnh Screenshot_7 hiển thị 10 máy ở bước “Đã nạp xong • Chờ cả đợt trước khi reboot”. Đối chiếu `logs/tiktool-20261013-062459.log`:

- 14:46:20: đợt được phân bổ cho **12 máy**, không phải 10.
- 14:46:22: 12 lệnh restore bắt đầu, dùng `--no-reboot`.
- 14:47:15–14:47:33: 10 lệnh restore trả exit 0.
- 14:47:30: hai máy có UDID kết thúc bằng `2610001E` và `36FA001E` mất kết nối, thẻ biến mất khỏi giao diện. Hai lệnh restore vẫn còn chạy, chưa xác nhận thành công.
- 14:50:56: hai lệnh đó trả exit 1; sau đó 10 máy thành công mới được gửi lệnh reboot.

Người dùng mô tả đóng app thì iPhone reboot. Log phù hợp với việc các lệnh đang giữ cả đợt được kết thúc khi app đóng, nhưng không có đủ dữ liệu để khẳng định cơ chế nội bộ trên từng iPhone. Đây là tình trạng chờ thành viên mất kết nối, không phải toàn bộ 12 máy đã restore thành công. Phần chờ cả đợt trước đây thiếu cơ chế dừng sớm lệnh của máy đã mất kết nối.

## Sửa trong app

- `_sync_cards` lưu thời điểm máy đang restore vắng mặt; xóa thời điểm khi máy xuất hiện lại.
- Worker chỉ yêu cầu dừng khi máy vắng liên tục ít nhất 30 giây **và** không có output không-lỗi từ lệnh restore ít nhất 30 giây. Mất kết nối thoáng qua hoặc lệnh còn có hoạt động không đáp ứng điều kiện này.
- `ProcessRunner.run_stream` hỗ trợ callback yêu cầu hủy, kiểm tra mỗi tối đa 0,5 giây trong lúc chờ tiến trình. Dừng tiến trình trước khi trả kết quả lỗi và nhả batch gate; không coi việc bị hủy là exit thành công.
- Máy bị hủy không chuyển backup, không cộng thành công, không xếp Auto Activate; hoàn tác Info.plist nguồn theo luồng lỗi hiện có.
- Các máy thành công chỉ reboot sau khi toàn bộ lệnh restore đã kết thúc, kể cả lệnh bị dừng. Không bỏ qua gate để reboot trong khi máy khác còn truyền dữ liệu.
- Khi gate chưa mở, mỗi 15 giây log liệt kê các UDID còn chờ để tránh chỉ thấy các máy hoàn tất trên giao diện.
- Dọn dữ liệu vắng mặt khi worker kết thúc. Không sửa timeout/thuật toán backup hoặc tự gửi lệnh vào iPhone để kiểm thử.

## Giới hạn

Kiểm chứng: compile thành công, 148/148 unit tests PASS (53 giây); gồm dừng/reap tiến trình ngủ giả lập, điều kiện vắng mặt và im lặng, giữ backup nguồn và giải phóng gate. Settings được sao lưu trước test và hash sau test không đổi.

- Mốc vắng mặt dựa trên kết quả poll USB đã đưa lên UI. Khi UI tắc hoàn toàn, cơ chế này có thể phát hiện chậm.
- Nếu máy vẫn hiện trên USB nhưng lệnh không thoát, điều kiện hủy do mất kết nối không áp dụng; timeout tổng của lệnh vẫn tồn tại.
- Chưa kiểm chứng trên đợt thiết bị thật sau sửa. Cần khởi động lại app để nhận mã mới.
