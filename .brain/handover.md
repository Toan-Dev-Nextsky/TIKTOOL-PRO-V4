# 📋 TÀI LIỆU BÀN GIAO (HANDOVER DOCUMENT)

**Dự án**: TikTok Pro (TIKTOOL PRO V4)  
**Thời gian cập nhật**: 2026-09-11  
**Phiên bản**: `4.8.9 Batch IPA Signer & Smart UDID Multi-Device Edition`  
**Trạng thái**: Hoàn thiện toàn diện quy trình Ký IPA Hàng Loạt bằng `TIK SIGNER PRO` (ttkbootstrap) + Khớp nối tự động thông minh theo UDID trong `TIKTOOL PRO V4` (`BB_RB.py`); toàn bộ 54/54 unit tests PASS (100%).

---

## 🚀 TỔNG HỢP CÁC NÂNG CẤP ĐÃ HOÀN TẤT TRONG PHIÊN LÀM VIỆC (2026-09-11)

### 1. Xây Dựng Ứng Dụng Mới: TIK SIGNER PRO (`TIK_SIGNER.py` + `CHAY_SIGNER.bat`)
* **Mục đích**: Tự động hóa 100% công đoạn ký IPA cho dàn 10 máy làm phôi TikTok Lite Nhật, loại bỏ hoàn toàn việc gõ lệnh thủ công.
* **Công nghệ**: Python + `ttkbootstrap 2.2.2` (Darkly Theme) hiện đại, sắc nét.
* **Tính năng chuyên biệt**:
  1. **Quét Thiết Bị & UDID**: Tự động đọc danh sách iPhone đang kết nối (`idevice_id.exe -l`) và tên máy (`ideviceinfo.exe`).
  2. **Trích xuất nhanh**: Nút **"📋 Sao chép 10 UDID"** và **"💾 Xuất file UDID (.txt)"** để gửi ngay cho bên bán chứng chỉ.
  3. **Tự động nhận diện chứng chỉ**: Tự quét thư mục `certs/`, đọc file `.mobileprovision` (trích xuất `ProvisionedDevices`), khớp file `.p12` và password (`pass.txt`).
  4. **Ký hàng loạt đa luồng (1-Click Batch Sign)**: Bấm **`⚡ KÝ IPA HÀNG LOẠT CHO TẤT CẢ MÁY`** ➔ Tool tự động gọi `zsign.exe` với tham số tối ưu `-z 9 -E -W`, ký ra file `TikTok_Lite_<UDID>_Signed.ipa` lưu vào thư mục `ipas/`.
  5. **Đặt tên chuẩn hóa chống nhầm**: Mỗi file IPA sinh ra đều chứa toàn bộ mã UDID của máy tương ứng.

---

### 2. Nâng Cấp Tính Năng "Smart UDID Matching" Trong TIKTOOL PRO V4 (`BB_RB.py`)
* **Vấn đề đã giải quyết**: Khi người dùng mua 10 chứng chỉ cá nhân lẻ, hệ thống sinh ra 10 file IPA riêng biệt. Ở bản cũ, nếu chọn cả 10 file và bấm cài đặt hàng loạt, mỗi máy sẽ cố cài cả 10 file (gây lỗi 9 lần do sai Team ID/UDID).
* **Giải pháp thông minh**:
  * Tại hàm `_install_ipa_worker`, trước khi tiến hành cài đặt, hệ thống tự động kiểm tra:
    ```python
    udid_clean = udid.lower().replace("-", "")
    matched_ipas = [
        p for p in ipa_paths
        if udid.lower() in os.path.basename(p).lower()
        or udid_clean in os.path.basename(p).lower().replace("-", "")
    ]
    if matched_ipas:
        target_ipas = matched_ipas
    else:
        target_ipas = ipa_paths
    ```
  * **Kết quả**: Khi người dùng tích chọn toàn bộ 10 file IPA rồi bấm **CÀI IPA HÀNG LOẠT (ALL)**:
    * Máy 1 tự động chọn đúng file IPA mang UDID máy 1 để cài.
    * Máy 2 tự động chọn đúng file IPA mang UDID máy 2 để cài.
    * Cả 10 máy chạy song song, tự gỡ app cũ và nạp app mới trơn tru 100%.

---

### 3. Sửa Lỗi Gỡ App Cũ Khi Tên File IPA Chứa Dấu Gạch Dưới
* **Nguyên nhân bug**: Khi file IPA có tên dạng `TikTok_Lite_xxx.ipa` (chứa dấu `_`), điều kiện `if "tiktok.lite" in fn_lower` bị trượt (vì tìm dấu `.`). Kết quả nhảy vào nhánh gỡ TikTok thường ➔ gỡ trượt TikTok Lite ➔ cài đè bị Apple chặn lỗi `MismatchedApplicationIdentifierEntitlement`.
* **Khắc phục**:
  * Chuẩn hóa ký tự: `fn_norm = fn_lower.replace("_", ".").replace("-", ".").replace(" ", ".")`.
  * Bổ sung hàm dự phòng `_extract_bundle_id_from_ipa()` đọc trực tiếp `CFBundleIdentifier` từ `Info.plist` bên trong file IPA nén zip.

---

### 4. Cơ Chế Developer Mode (Chế Độ Nhà Phát Triển) Trên iOS 16+
* **Quy chuẩn Apple**: Bất kỳ app nào cài ngoài App Store bằng chứng chỉ cá nhân/doanh nghiệp trên iOS 16, 17, 18 bắt buộc phải bật Developer Mode 1 lần duy nhất trên máy.
* **Hướng dẫn cho iPhone tiếng Nhật**:
  1. Vào **Cài đặt** (設定).
  2. Chọn **Quyền riêng tư & Bảo mật** (プライバシーとセキュリティ).
  3. Cuộn xuống dưới cùng chọn **Chế độ nhà phát triển** (デベロッパモード) ➔ Bật ON.
  4. Chọn **Khởi động lại** (再起動).
  5. Mở khóa máy, bấm **Bật** (有効にする) và nhập Passcode màn hình.
* **Lưu ý đặc biệt**: Sau khi làm phôi xong, khi restore phôi sang các máy khác (đã có sẵn app TikTok Lite tải từ App Store) thì **KHÔNG cần bật Developer Mode và KHÔNG cần mua thêm chứng chỉ**, máy đích nhận phôi 100%.

---

## 🗂️ DANH MỤC FILE DỰ ÁN LIÊN QUAN

| Đường dẫn file | Vai trò |
|---|---|
| [`TIK_SIGNER.py`](file:///c:/TIKTOOL%20PRO%20V4/TIK_SIGNER.py) | Mã nguồn ứng dụng Ký IPA Hàng Loạt (ttkbootstrap) |
| [`CHAY_SIGNER.bat`](file:///c:/TIKTOOL%20PRO%20V4/CHAY_SIGNER.bat) | File chạy 1-click cho TIK SIGNER PRO |
| [`certs/README_CERTS.txt`](file:///c:/TIKTOOL%20PRO%20V4/certs/README_CERTS.txt) | Hướng dẫn cấu trúc thư mục chứa chứng chỉ |
| [`BB_RB.py`](file:///c:/TIKTOOL%20PRO%20V4/BB_RB.py) | Ứng dụng chính TIKTOOL PRO V4 (Đã tích hợp Smart UDID Matching) |
| [`CHANGELOG.md`](file:///c:/TIKTOOL%20PRO%20V4/CHANGELOG.md) | Nhật ký thay đổi phiên bản v4.8.9 |
| [`.brain/session.json`](file:///c:/TIKTOOL%20PRO%20V4/.brain/session.json) | Bộ nhớ tiến trình làm việc |
| [`.brain/brain.json`](file:///c:/TIKTOOL%20PRO%20V4/.brain/brain.json) | Bộ nhớ tri thức kiến trúc và gotchas |

---

## 🧪 KẾT QUẢ KIỂM THỬ
* **Cú pháp Python (`py_compile`)**:
  * `TIK_SIGNER.py`: Clean ✅
  * `BB_RB.py`: Clean ✅
* **Kiểm thử tự động (`unittest discover -s tests`)**:
  * **54/54 unit tests PASS (100%)** trong 0.292 giây.
