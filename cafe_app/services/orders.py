from decimal import ROUND_HALF_UP, Decimal

from .. import constants as C
from ..models import DiningTable, Fee, MenuItem


class OrderError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def get_menu_items():
    rows = (MenuItem.query.filter_by(is_active=True)
            .order_by(MenuItem.sort_order, MenuItem.name).all())
    return [{"id": m.id, "name": m.name, "category": m.category,
             "unit": m.unit, "price": int(m.price)} for m in rows]


def get_active_tables():
    rows = DiningTable.query.filter_by(is_active=True).order_by(DiningTable.code).all()
    return [{"id": t.id, "code": t.code, "name": t.name} for t in rows]


def _calc_fee(fee, subtotal):
    value = Decimal(fee.value)
    if fee.kind == C.FEE_PERCENT:
        amt = (Decimal(subtotal) * value / Decimal(100)).quantize(
            Decimal(1), rounding=ROUND_HALF_UP)
    else:
        amt = value.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(amt)


def quote_cart(items):
    if not isinstance(items, (list, tuple)) or not items:
        raise OrderError("EMPTY_CART", "Giỏ hàng trống.")
    if len(items) > C.MAX_CART_ITEMS:
        raise OrderError("TOO_MANY_ITEMS",
                         f"Tối đa {C.MAX_CART_ITEMS} loại món mỗi đơn.")
    qty_by_id = {}
    for it in items:
        try:
            mid, qty = it["menu_item_id"], it["quantity"]
        except (TypeError, KeyError):
            raise OrderError("BAD_ITEM", "Dòng món không hợp lệ.")
        if isinstance(mid, bool) or not isinstance(mid, int):
            raise OrderError("BAD_ITEM", "menu_item_id không hợp lệ.")
        if isinstance(qty, bool) or not isinstance(qty, int) \
                or not C.MIN_QTY <= qty <= C.MAX_QTY:
            raise OrderError("BAD_QUANTITY",
                             f"Số lượng phải từ {C.MIN_QTY} đến {C.MAX_QTY}.")
        if mid in qty_by_id:
            raise OrderError("DUPLICATE_ITEM", "Món bị trùng trong giỏ.")
        qty_by_id[mid] = qty

    menus = {m.id: m for m in MenuItem.query
             .filter(MenuItem.id.in_(list(qty_by_id)), MenuItem.is_active.is_(True))}
    lines, subtotal = [], 0
    for mid, qty in qty_by_id.items():
        m = menus.get(mid)
        if m is None:
            raise OrderError("ITEM_UNAVAILABLE", f"Món #{mid} không tồn tại hoặc ngừng bán.")
        price = int(m.price)
        lines.append({"menu_item_id": m.id, "name": m.name, "unit": m.unit,
                      "unit_price": price, "quantity": qty,
                      "line_total": price * qty})
        subtotal += price * qty

    fees, fee_total = [], 0
    for f in Fee.query.filter_by(is_active=True).order_by(Fee.code):
        amt = _calc_fee(f, subtotal)
        fees.append({"code": f.code, "name": f.name, "kind": f.kind,
                     "value": str(f.value), "amount": amt})
        fee_total += amt
    return {"lines": lines, "subtotal": subtotal, "fees": fees,
            "fee_amount": fee_total, "total": subtotal + fee_total}

