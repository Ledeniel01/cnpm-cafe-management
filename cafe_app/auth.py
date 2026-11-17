from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user

from .extensions import db, login_manager
from .models import User
from .staff import staff_bp

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
    return user if user and user.is_active else None


def _safe_next(target):
    if target and not urlparse(target).netloc and target.startswith("/") \
            and not target.startswith("//"):
        return target
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username).first()
        if user and user.is_active and user.check_password(password):
            login_user(user)
            return redirect(_safe_next(request.args.get("next"))
                            or url_for("staff.index"))
        flash("Sai tên đăng nhập hoặc mật khẩu.", "error")
    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def init_auth(app):
    if getattr(app, "login_manager", None) is None:
        login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Vui lòng đăng nhập."

    app.register_blueprint(auth_bp)
    app.register_blueprint(staff_bp)