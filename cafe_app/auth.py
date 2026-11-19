from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db, login_manager
from .models import User
from .cli import register_cli
from .staff import staff_bp

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def get_next(target):
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("staff.orders")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("staff.orders"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.is_active and user.check_password(password):
            login_user(user)
            return redirect(get_next(request.args.get("next")))
        flash("Sai tên đăng nhập hoặc mật khẩu.", "error")
    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def init_auth(app):


    login_manager.login_view = "auth.login"
    app.register_blueprint(auth_bp)
    app.register_blueprint(staff_bp)
    register_cli(app)