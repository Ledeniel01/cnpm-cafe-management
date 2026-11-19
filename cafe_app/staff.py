import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from . import constants as C
from .models import Order
from .permissions import PERM_CONFIRM, PERM_PAY, PERM_VIEW, roles_required
from .services import orders as order_service

staff_bp = Blueprint("staff", __name__, url_prefix="/staff")


@staff_bp.route("/orders")
@roles_required(*PERM_VIEW)
def orders():
    status = request.args.get("status")
    query = Order.query
    if status in C.ORDER_STATUSES:
        query = query.filter_by(status=status)
    rows = query.order_by(Order.created_at.desc()).limit(200).all()
    return render_template("staff/orders.html", orders=rows,
                           statuses=C.ORDER_STATUSES, current=status)


@staff_bp.route("/orders/<int:order_id>")
@roles_required(*PERM_VIEW)
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    fees = json.loads(order.fee_snapshot or "[]")
    can_confirm = current_user.role in PERM_CONFIRM and order.status == C.STATUS_NEW
    can_pay = current_user.role in PERM_PAY and order.status == C.STATUS_CONFIRMED
    return render_template("staff/order_detail.html", o=order, fees=fees,
                           can_confirm=can_confirm, can_pay=can_pay)


@staff_bp.route("/orders/<int:order_id>/confirm", methods=["POST"])
@roles_required(*PERM_CONFIRM)
def confirm(order_id):
    if order_service.confirm_order(order_id, current_user):
        flash("Đã xác nhận đơn.", "ok")
    else:
        flash("Không thể xác nhận đơn này.", "error")
    return redirect(url_for("staff.order_detail", order_id=order_id))


@staff_bp.route("/orders/<int:order_id>/pay", methods=["POST"])
@roles_required(*PERM_PAY)
def pay(order_id):
    if order_service.mark_paid(order_id, current_user):
        flash("Đã thu tiền.", "ok")
    else:
        flash("Không thể thu tiền đơn này.", "error")
    return redirect(url_for("staff.order_detail", order_id=order_id))