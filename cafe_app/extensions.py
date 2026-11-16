"""Khai báo extension dùng chung, chưa gắn vào app khi import module."""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect


db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Vui lòng đăng nhập bằng tài khoản nhân viên."
login_manager.login_message_category = "warning"