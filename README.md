Bài tập lớn Flask + MySQL, thực hiện 16/11-06/12/2026.

## Phân công

- Long: giao diện/đặt món, khung Flask, review và tích hợp.
- Thái: CSDL, nghiệp vụ đơn, tài khoản/quyền, thu ngân.
- Huy: quản trị, kho và báo cáo.

## Bản nền hiện tại

Có app factory, blueprint public, trang chủ/CSS, trang lỗi, cấu hình riêng,
extension SQLAlchemy và CSRF. Trang chủ không truy vấn hoặc xác nhận kết nối DB.
Chưa có đặt món/giỏ, model, tạo bảng, seed, login, Admin, kho hoặc báo cáo.

login_manager đã khai báo trong extensions.py nhưng chưa init vào app.
Thái bổ sung init_auth(app) trong auth.py để init manager, user_loader và
đăng ký auth/staff blueprint; Long nối lời gọi rõ ràng sau PR.
Huy cung cấp init_admin(app); Long nối sau PR. Không dùng try/except import
để che module chưa hoàn thành hoặc mở Admin chưa có kiểm quyền.

## Môi trường

Tạo .venv riêng, không dùng môi trường hoặc DB travel-app.
Cài requirements.txt khi dựng lần đầu. Khi Long đã thử bản nền và tạo
requirements-lock.txt, các thành viên cài bằng file lock để dùng cùng phiên bản.

.env dùng hai biến riêng CNPM_SECRET_KEY và CNPM_DATABASE_URL.
File .env.example chỉ là mẫu. URI CHANGE_ME chưa chứng minh MySQL đã kết nối.
SECRET_KEY là cấu hình Flask nhận từ CNPM_SECRET_KEY; SQLALCHEMY_DATABASE_URI
nhận từ CNPM_DATABASE_URL. Không commit .env hoặc chia sẻ secret lên Issue.

## Chạy local

Từ gốc repo, sau khi tạo .env và cài thư viện:

```powershell
.\.venv\Scripts\python.exe -m flask --app cafe_app run --port 5001
```

Hoặc dùng .\.venv\Scripts\python.exe run.py.
Mở http://127.0.0.1:5001/ và thử một URL không tồn tại để xem trang404.
Chưa chạy create_all/seed, chưa cần kết nối DB để xem trang chủ nền.
Khi nhận model của Thái, cập nhật đúng URI MySQL riêng rồi dùng hướng dẫn DB của Thái.

## Quy định nghiệp vụ sẽ triển khai

Khách không cần tài khoản; mọi đơn bắt buộc số điện thoại, cả tại quán lẫn giao hàng.
Tại quán chọn bàn; giao hàng thêm tên/địa chỉ, trả khi nhận, không phí giao hàng.
Tối đa10loại món; phí phục vụ ban đầu5%; server tính tiền và giữ lịch sử giá/phí.

## Quy ước code và Git

Đầu file ghi sơ nhiệm vụ, không comment từng dòng. Điểm chưa hiểu ghi riêng để hỏi/học.
Tuần1 PR vào int/cnpm-w1; main nhận bản tổng vào22/11,29/11,06/12.
Báo cáo/sơ đồ được quản lý ngoài source app. Không thêm source Phát/travel-app vào đây.