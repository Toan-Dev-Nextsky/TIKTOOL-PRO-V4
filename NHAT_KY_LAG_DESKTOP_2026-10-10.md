# Kiểm tra desktop bị vẽ chồng khi mở app lâu — 10/10/2026

## Bằng chứng tại máy

- Người dùng gửi Screenshot_6: desktop bị vẽ chồng icon/chữ, phải khởi động lại máy.
- Khi kiểm tra không còn tiến trình Python của TIKTOOL hoặc 3uTools đang chạy. Không có phép đo GDI/USER objects tại thời điểm desktop lỗi để kết luận app nào gây lỗi vẽ.
- Windows System, Resource-Exhaustion-Detector, event 2004 lúc 16:37:08 ngày 10/10: thiếu bộ nhớ ảo. `3uTools.exe` PID 19916 dùng 8.550.076.416 byte (~7,96 GiB), `pythonw.exe` PID 8280 dùng 361.799.680 byte (~345 MiB), MsMpEng dùng 392.699.904 byte.
- Ngày 09/10 lúc 06:28:48–06:28:50 cũng ghi thiếu bộ nhớ ảo, 3uTools dùng 8.661.553.152 byte. Application Error lúc 16:37:07 ngày 10/10 ghi crash 3uTools 9.10.6.0 trong Qt5Core.dll.
- Có crash AppleUsbFilter/UserMode driver lúc 18:51:13. Chưa có bằng chứng nối trực tiếp crash USB này với lỗi vẽ desktop trong ảnh.
- Log TIKTOOL gần nhất `logs/tiktool-20261010-135141.log` chạy khoảng 13:51–18:52, 22.596 dòng, ~2,7 MB.
- Xuất các sự kiện thiếu bộ nhớ vào `logs/desktop-memory-evidence-20261010.json` để đối chiếu tại máy. Không thay đổi driver, pagefile hay registry trong lần xử lý này.

## Các điểm sửa trong TIKTOOL

1. Chữ chạy khi ẩn bảng hiệu suất: trước đây chỉ loại ID khỏi danh sách Python khi ra khỏi màn hình, nhưng item vẫn còn trên Tk Canvas. Nay gọi `canvas.delete(item)` để giải phóng item đó.
2. Nhật ký giao diện: trước đây tích lũy toàn bộ nội dung đến khi tắt app. Nay giới hạn 2.000 dòng và 250.000 ký tự; dòng cũ được loại khỏi widget.
3. Một thông báo lớn được rút gọn còn khoảng 8.000 ký tự trước khi vào UI queue; bản đầy đủ vẫn được ghi file trước khi rút gọn.
4. UI queue nhường lại event loop sau khoảng 8 ms giữa các callback (vẫn tối đa 200 callback/lượt); không bỏ callback nghiệp vụ như cập nhật bộ đếm. Một callback riêng lẻ vẫn có thể lâu hơn giới hạn này.
5. Thanh tiến độ không xóa/vẽ lại gradient nếu giá trị không thay đổi; sự kiện đổi kích thước vẫn vẽ lại bình thường.

Các sửa này giảm tích tụ và công việc vẽ trong TIKTOOL. Chưa chứng minh chúng là nguyên nhân trực tiếp của ảnh desktop; cấu hình tại thời điểm kiểm tra có `performanceStatsHidden=false`, nên lỗi item ticker chỉ phát sinh khi tính năng chữ chạy được bật.

## Kiểm chứng và sử dụng

- Compile thành công; 146/146 unit tests PASS (52 giây), gồm 4 test mới. Hash settings thật không thay đổi sau kiểm thử. Chưa kiểm chứng một phiên chạy dài trên iPhone thật sau bản sửa.
- Test dùng Tk ẩn và dữ liệu giả, không gửi lệnh xuống thiết bị. Settings được sao lưu vào `logs/settings-before-ui-long-running-tests-20261010.json` và tách khỏi settings thật khi chạy.
- Test mô phỏng 12.000 khung hình ticker, hàng nghìn dòng log, bảo toàn bản log đầy đủ và nhường UI queue mà không mất callback.
- Cần mở lại TIKTOOL từ source để tải bản sửa và quan sát một phiên chạy dài thực tế.
- Dựa trên event 2004, nên đóng cửa sổ 3uTools khi không cần dùng, đặc biệt khi chỉ vận hành TIKTOOL. Nếu tái diễn, ghi lại Private Bytes/Commit size và GDI/USER objects của các tiến trình trước khi khởi động lại để phân biệt thiếu bộ nhớ và tài nguyên đồ họa.
- Không coi việc giới hạn log TIKTOOL là cách khắc phục hoàn toàn hiện tượng 3uTools chiếm gần 8 GiB.
