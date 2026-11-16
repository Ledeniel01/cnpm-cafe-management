"""Tạo ứng dụng và nối các thành phần nền; không chứa nghiệp vụ đơn."""
from flask import Flask, render_template

from .config import load_config
from .extensions import csrf, db
from .public import bp as public_bp


ERROR_CONTENT = {
    400: ("Yêu cầu chưa hợp lệ", "Vui lòng tải lại trang và thử lại thao tác."),
    403: ("Không có quyền truy cập", "Bạn không có quyền thực hiện thao tác này."),
    404: ("Không tìm thấy trang", "Trang bạn tìm không tồn tại hoặc đã được thay đổi."),
    500: ("Chưa thể xử lý yêu cầu", "Hệ thống đang gặp lỗi. Vui lòng thử lại sau."),
}

def create_app(config_override=None):
    app = Flask(__name__)
    app.config.from_mapping(load_config())
    if config_override:
        app.config.update(config_override)

    secret = app.config.get("SECRET_KEY")
    if not isinstance(secret, str) or len(secret) < 32:
        raise RuntimeError("CNPM_SECRET_KEY cần ít nhất 32 ký tự trong .env hoặc môi trường.")
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("Chưa thiết lập CNPM_DATABASE_URL cho CSDL riêng CNPM.")

    db.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(public_bp)

    def render_http_error(error):
        code = error.code
        title, message = ERROR_CONTENT[code]
        return render_template(
            "errors/error.html", code=code, title=title, message=message
        ), code

    for code in ERROR_CONTENT:
        app.register_error_handler(code, render_http_error)

    return app