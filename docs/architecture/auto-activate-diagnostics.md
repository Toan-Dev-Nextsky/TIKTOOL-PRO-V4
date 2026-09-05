# Auto Activate: rollback và điều tra — 2026-09-05

## Trạng thái hiện tại

Đã hoàn tác toàn bộ sửa đổi Activate/Auto Activate của phiên trước theo yêu cầu người dùng. Hai worker khớp bản trước sửa; giữ nguyên các thay đổi UI có sẵn. Test workflow cũng khôi phục bản trước. Chưa áp dụng phương án thay thế vào ứng dụng.

## Bằng chứng mới

- Người dùng xác nhận Auto Activate lỗi trên máy khác nhưng bấm BATCH ACTIVATE (ALL) sau đó hoạt động.
- Bản sửa chặn cả máy vốn chạy tốt vì ideviceinfo --simple -k ActivationState trả chuỗi rỗng.
- Kiểm tra chỉ đọc trên một iPhone đang kết nối: ideviceactivation state trả `ActivationState: Activated` với exit 1; ideviceinfo --simple -k ActivationState trả rỗng với exit 0. Không được suy diễn trạng thái từ exit code hoặc trường không đọc được.
- Log cũ logs/tiktool-20260905-141838.log lúc 14:31:51: go-ios đã báo device is activated:true, nhưng prepare lỗi SetCloudConfiguration, ErrorCode 14002, A cloud configuration is already present on this device. App cũ vẫn báo thành công.
- Đây là lỗi Skip Setup đã có bằng chứng trên máy hiện tại; chưa chứng minh đó là nguyên nhân trên máy tính khác.

## Phương án tiếp theo

Giữ engine BATCH ACTIVATE đang dùng được. Thử thiết kế Auto Activate theo đợt: đợi toàn bộ restore hoàn tất, đợi kết nối sau reboot ổn định, rồi điều phối cùng pipeline thủ công cho đúng tập UDID của đợt. Ghi riêng kết quả Activate và Skip Setup. Đây là giả thuyết cần đối chiếu log tự động/thủ công trên máy bị lỗi trước khi thay đổi production.

Với lỗi cloud configuration, không xóa cấu hình hoặc sửa backup để thử. Cần kiểm tra trạng thái setup và đầu ra prepare trên đúng iPhone. Mã nguồn upstream go-ios ios/mcinstall/prepare.go trả lỗi ngay nếu SetCloudConfiguration thất bại, trước bước setupSkipSetup; vì vậy tăng thời gian chờ không đủ để giải quyết lỗi này.

Nguồn tham khảo: https://github.com/danielpaulus/go-ios/blob/main/ios/mcinstall/prepare.go

## Xác minh rollback

Đã so sánh chính xác hai worker với nội dung trước sửa và kiểm tra cú pháp. Không chạy lại test pipeline cũ vì mock của test đó không bao phủ các lệnh PROCESS_RUNNER trực tiếp. Không thực hiện lệnh activate/prepare/restore trên thiết bị trong lần rollback này.
