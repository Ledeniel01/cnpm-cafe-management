from flask import Blueprint

from .constants import ROLE_CASHIER, ROLE_STAFF
from .permissions import role_required

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


@staff_bp.route("/")
@role_required(ROLE_STAFF, ROLE_CASHIER)
def index():
    # TODO(PR2): danh sách đơn
    return "Staff area (PR2: danh sách đơn)", 200