"""Route giao diện khách; nền hiện tại chưa truy vấn món hoặc tạo đơn."""
from flask import Blueprint, render_template


bp = Blueprint("public", __name__)


@bp.get("/")
def index():
    return render_template("public/index.html")