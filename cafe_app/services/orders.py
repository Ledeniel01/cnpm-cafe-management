import json
import re
import secrets
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import update

from .. import constants as C
from ..extensions import db
from ..models import DiningTable, Fee, MenuItem, Order, OrderItem


class OrderError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def get_menu_items():
    rows = (MenuItem.query.filter_by(is_active=True)
            .order_by(MenuItem.sort_order, MenuItem.name).all())
    result = []
    for m in rows:
        result.append({"id": m.id, "name": m.name, "category": m.category,
                       "unit": m.unit, "price": int(m.price)})
    return result


def get_active_tables():
    rows = DiningTable.query.filter_by(is_active=True).order_by(DiningTable.code).all()
    result = []
    for t in rows:
        result.append({"id": t.id, "code": t.code, "name": t.name})
    return result


def calc_fee(fee, subtotal):
    value = Decimal(fee.value)
    if fee.kind == C.FEE_PERCENT:
        amount = Decimal(subtotal) * value / Decimal(100)
    else:
        amount = value
    return int(amount.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def quote_cart(items):
    if not isinstance(items, (list, tuple)) or len(items) == 0:
        raise OrderError("EMPTY_CART", "Giỏ hàng trống.")
    if len(items) > C.MAX_CART_ITEMS:
        raise OrderError("TOO_MANY_ITEMS", f"Tối đa {C.MAX_CART_ITEMS} loại món mỗi đơn.")

    qty_by_id = {}
    for it in items:
        try:
            mid = it["menu_item_id"]
            qty = it["quantity"]
        except (TypeError, KeyError):
            raise OrderError("BAD_ITEM", "Dòng món không hợp lệ.")
        if isinstance(mid, bool) or not isinstance(mid, int):
            raise OrderError("BAD_ITEM", "menu_item_id không hợp lệ.")
        if isinstance(qty, bool) or not isinstance(qty, int):
            raise OrderError("BAD_QUANTITY", "Số lượng không hợp lệ.")
        if qty < C.MIN_QTY or qty > C.MAX_QTY:
            raise OrderError("BAD_QUANTITY", f"Số lượng phải từ {C.MIN_QTY} đến {C.MAX_QTY}.")
        if mid in qty_by_id:
            raise OrderError("DUPLICATE_ITEM", "Món bị trùng trong giỏ.")
        qty_by_id[mid] = qty

    menus = {}
    rows = MenuItem.query.filter(MenuItem.id.in_(list(qty_by_id)),
                                 MenuItem.is_active.is_(True)).all()
    for m in rows:
        menus[m.id] = m

    lines = []
    subtotal = 0
    for mid, qty in qty_by_id.items():
        m = menus.get(mid)
        if m is None:
            raise OrderError("ITEM_UNAVAILABLE", f"Món #{mid} không tồn tại hoặc ngừng bán.")
        price = int(m.price)
        line_total = price * qty
        lines.append({"menu_item_id": m.id, "name": m.name, "unit": m.unit,
                      "unit_price": price, "quantity": qty, "line_total": line_total})
        subtotal += line_total

    fees = []
    fee_total = 0
    for f in Fee.query.filter_by(is_active=True).order_by(Fee.code).all():
        amount = calc_fee(f, subtotal)
        fees.append({"code": f.code, "name": f.name, "kind": f.kind,
                     "value": str(f.value), "amount": amount})
        fee_total += amount

    return {"lines": lines, "subtotal": subtotal, "fees": fees,
            "fee_amount": fee_total, "total": subtotal + fee_total}


def normalize_phone(raw):
    if not isinstance(raw, str):
        raise OrderError("BAD_PHONE", "Số điện thoại bắt buộc và phải hợp lệ.")
    phone = re.sub(r"[\s.\-()]", "", raw)
    if phone.startswith("+84"):
        phone = "0" + phone[3:]
    if not re.match(r"^0\d{9,10}$", phone):
        raise OrderError("BAD_PHONE", "Số điện thoại bắt buộc và phải hợp lệ.")
    return phone


def create_order(order_type, customer_name, customer_phone, items, table_id=None, note=""):
    if order_type not in C.ORDER_TYPES:
        raise OrderError("BAD_TYPE", "Hình thức không hợp lệ.")

    phone = normalize_phone(customer_phone)

    if order_type == C.ORDER_DINE_IN:
        table = None
        if type(table_id) is int:
            table = db.session.get(DiningTable, table_id)
        if table is None or not table.is_active:
            raise OrderError("BAD_TABLE", "Bàn không hợp lệ.")
    else:
        table_id = None

    quote = quote_cart(items)

    try:
        code = "DH" + datetime.utcnow().strftime("%y%m%d") + secrets.token_hex(4).upper()
        order = Order(
            code=code,
            order_type=order_type,
            table_id=table_id,
            customer_name=(customer_name or "").strip()[:100],
            customer_phone=phone,
            note=(note or "").strip()[:255],
            status=C.STATUS_NEW,
            subtotal=quote["subtotal"],
            fee_amount=quote["fee_amount"],
            total=quote["total"],
            fee_snapshot=json.dumps(quote["fees"], ensure_ascii=False),
        )
        for l in quote["lines"]:
            order.items.append(OrderItem(
                menu_item_id=l["menu_item_id"],
                item_name=l["name"],
                unit=l["unit"],
                unit_price=l["unit_price"],
                quantity=l["quantity"],
                line_total=l["line_total"],
            ))
        db.session.add(order)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise OrderError("SAVE_FAILED", "Không lưu được đơn, vui lòng thử lại.") from e

    return {"id": order.id, "code": order.code, "status": order.status,
            "subtotal": quote["subtotal"], "fee_amount": quote["fee_amount"],
            "total": quote["total"]}


def change_status(order_id, from_status, to_status, **cols):
    result = db.session.execute(
        update(Order)
        .where(Order.id == order_id, Order.status == from_status)
        .values(status=to_status, version=Order.version + 1,
                updated_at=datetime.utcnow(), **cols))
    db.session.commit()
    return result.rowcount == 1


def confirm_order(order_id, user):
    return change_status(order_id, C.STATUS_NEW, C.STATUS_CONFIRMED,
                         confirmed_at=datetime.utcnow(), confirmed_by_id=user.id)


def mark_paid(order_id, user):
    return change_status(order_id, C.STATUS_CONFIRMED, C.STATUS_PAID,
                         paid_at=datetime.utcnow(), paid_by_id=user.id)

def is_locked(order):
    return order.status in (C.STATUS_PAID, C.STATUS_CANCELLED)