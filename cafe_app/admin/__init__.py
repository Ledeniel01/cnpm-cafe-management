"""
Module quản trị (Huy).

Hook cho factory (Long), gọi SAU init_auth(app) của Thái:
    from .admin import init_admin
    init_admin(app)

Chỉ đăng ký Thực đơn, Bàn, Phí dịch vụ.
KHÔNG đăng ký Order/OrderItem: sửa đơn và thu tiền đi qua trang/hàm của Thái.
"""
from flask_admin import Admin
from flask_admin.theme import Bootstrap4Theme

from .views import AdminHomeView, DiningTableView, FeeView, MenuItemView


def init_admin(app):
    """Gắn Flask-Admin vào app tại /admin và trả về đối tượng Admin."""
    # Import trong hàm để tránh vòng import khi create_app() nạp module.
    from ..extensions import db
    from ..models import DiningTable, Fee, MenuItem

    admin = Admin(
        app,
        name="Quản trị quán cafe",
        theme=Bootstrap4Theme(base_template="admin/cafe_base.html"),
        index_view=AdminHomeView(name="Tổng quan", url="/admin"),
    )

    admin.add_view(MenuItemView(MenuItem, db.session,
                                name="Thực đơn", endpoint="admin_menu"))
    admin.add_view(DiningTableView(DiningTable, db.session,
                                   name="Bàn", endpoint="admin_table"))
    admin.add_view(FeeView(Fee, db.session,
                           name="Phí dịch vụ", endpoint="admin_fee"))

    return admin
