"""
View quản trị tuần 1: Thực đơn, Bàn, Phí dịch vụ.

- Phân quyền chặn ở is_accessible() (cả khi gõ URL trực tiếp), không chỉ ẩn menu.
- Dùng current_user/role của Thái (auth.py), không có hệ login riêng.
- KHÔNG có view cho Order/OrderItem: sửa đơn/thu tiền đi qua trang của Thái.
"""
from decimal import Decimal, InvalidOperation

from flask import abort, flash, redirect, request, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.sqla.validators import Unique
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import BooleanField, DecimalField, IntegerField, validators
from wtforms.fields.core import UnboundField

from ..constants import FEE_PERCENT, ROLE_ADMIN

# Giới hạn kỹ thuật theo cột Money = Numeric(12, 0) trong models.py
MAX_VND = 999_999_999_999
DEFAULT_FEE_PERCENT = 5


def _is_admin():
    return current_user.is_authenticated and current_user.role == ROLE_ADMIN


def _deny():
    """Guest -> trang đăng nhập (kèm next); sai role -> 403."""
    if not current_user.is_authenticated:
        flash("Vui lòng đăng nhập bằng tài khoản quản lý.", "warning")
        return redirect(url_for("auth.login", next=request.full_path))
    abort(403)


# ---------------------------------------------------------------------------
# Field nhập liệu thân thiện tiếng Việt
# ---------------------------------------------------------------------------

class VndField(IntegerField):
    """Tiền VND nguyên; chấp nhận '25000', '25.000', '25,000', '25 000'."""

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        raw = (valuelist[0] or "").strip()
        for sep in (".", ",", " ", "₫"):
            raw = raw.replace(sep, "")
        if raw == "":
            self.data = None
            return
        if not raw.isdigit():
            self.data = None
            raise ValueError("Giá phải là số nguyên VND, không âm, không có phần lẻ (vd: 25000).")
        self.data = int(raw)


class PercentField(DecimalField):
    """Phần trăm 0–100, chấp nhận dấu phẩy thập phân (vd: 5 hoặc 7,5)."""

    def process_formdata(self, valuelist):
        if not valuelist:
            return
        raw = (valuelist[0] or "").strip().replace("%", "").replace(",", ".")
        if raw == "":
            self.data = None
            return
        try:
            self.data = Decimal(raw)
        except InvalidOperation:
            self.data = None
            raise ValueError("Phí phải là số từ 0 đến 100 (vd: 5 hoặc 7,5).")
        if not self.data.is_finite():
            self.data = None
            raise ValueError("Phí phải là số từ 0 đến 100 (vd: 5 hoặc 7,5).")


def _vnd(value):
    return "—" if value is None else f"{int(value):,} ₫".replace(",", ".")


def _yes_no(value):
    return "Có" if value else "Không"


# ---------------------------------------------------------------------------
# Base view
# ---------------------------------------------------------------------------

class AdminHomeView(AdminIndexView):
    """Trang /admin/ — cũng kiểm quyền."""

    def is_accessible(self):
        return _is_admin()

    def inaccessible_callback(self, name, **kwargs):
        return _deny()

    @expose("/")
    def index(self):
        return self.render("admin/index.html")


class AdminForm(FlaskForm):
    """
    FlaskForm (có csrf_token khớp CSRFProtect toàn cục) + giữ `_obj` như BaseForm
    của Flask-Admin, để validator Unique không báo trùng chính bản ghi đang sửa.
    """

    def __init__(self, formdata=None, obj=None, prefix="", **kwargs):
        self._obj = obj
        super().__init__(formdata=formdata, obj=obj, prefix=prefix, **kwargs)


class AdminModelView(ModelView):
    """ModelView gốc: chỉ ROLE_ADMIN, form có CSRF của Flask-WTF."""

    # CSRFProtect toàn cục của Long chặn POST không có token -> dùng FlaskForm
    form_base_class = AdminForm
    # Không có nút xóa hàng loạt (bỏ qua kiểm tra lịch sử)
    action_disallowed_list = ["delete"]
    can_view_details = False
    can_export = False
    page_size = 50
    unique_message = "Giá trị này đã tồn tại."

    def is_accessible(self):
        return _is_admin()

    def inaccessible_callback(self, name, **kwargs):
        return _deny()

    def scaffold_form(self):
        """Việt hóa thông báo trùng lặp do Flask-Admin tự sinh."""
        form_class = super().scaffold_form()
        for attr in dir(form_class):
            field = getattr(form_class, attr, None)
            if isinstance(field, UnboundField):
                for v in field.kwargs.get("validators") or []:
                    if isinstance(v, Unique):
                        v.message = self.unique_message
        return form_class


# ---------------------------------------------------------------------------
# Thực đơn
# ---------------------------------------------------------------------------

class MenuItemView(AdminModelView):
    """
    CRUD món. Món đã có trong đơn (hoặc có công thức kho) không được xóa;
    dùng "Đang bán" = Không để ngừng bán. Đổi giá chỉ ảnh hưởng đơn mới vì
    OrderItem lưu item_name/unit_price snapshot.
    """

    unique_message = "Tên món đã tồn tại."

    column_list = ["name", "category", "unit", "price", "is_active", "sort_order"]
    column_labels = {
        "name": "Tên món",
        "category": "Nhóm",
        "unit": "Đơn vị",
        "price": "Giá (VND)",
        "is_active": "Đang bán",
        "sort_order": "Thứ tự",
    }
    column_searchable_list = ["name", "category"]
    column_filters = ["is_active", "category"]
    column_sortable_list = ["name", "category", "price", "sort_order", "is_active"]
    column_default_sort = [("sort_order", False), ("name", False)]
    column_formatters = {
        "price": lambda v, c, m, p: _vnd(m.price),
        "is_active": lambda v, c, m, p: _yes_no(m.is_active),
    }

    form_columns = ["name", "category", "unit", "price", "is_active", "sort_order"]
    form_overrides = {"price": VndField, "is_active": BooleanField}
    form_args = {
        "name": {
            "label": "Tên món",
            "filters": [lambda s: s.strip() if isinstance(s, str) else s],
            "validators": [
                validators.InputRequired(message="Vui lòng nhập tên món."),
                validators.Length(max=100, message="Tên món tối đa 100 ký tự."),
            ],
        },
        "category": {
            "label": "Nhóm (vd: Cà phê, Trà)",
            "filters": [lambda s: (s or "").strip()],
            "validators": [validators.Length(max=50, message="Nhóm tối đa 50 ký tự.")],
        },
        "unit": {
            "label": "Đơn vị (vd: ly, phần, chai)",
            "default": "ly",
            "filters": [lambda s: s.strip() if isinstance(s, str) else s],
            "validators": [
                validators.InputRequired(message="Vui lòng nhập đơn vị."),
                validators.Length(max=20, message="Đơn vị tối đa 20 ký tự."),
            ],
        },
        "price": {
            "label": "Giá (VND, số nguyên)",
            "validators": [
                validators.InputRequired(message="Vui lòng nhập giá."),
                validators.NumberRange(min=0, max=MAX_VND,
                                       message="Giá phải từ 0 đến 999.999.999.999 VND."),
            ],
        },
        "is_active": {"label": "Đang bán", "default": True},
        "sort_order": {
            "label": "Thứ tự hiển thị (số nhỏ lên trước)",
            "default": 0,
            "validators": [
                validators.Optional(),
                validators.NumberRange(min=0, max=100000,
                                       message="Thứ tự phải từ 0 đến 100000."),
            ],
        },
    }

    def on_model_change(self, form, model, is_created):
        if not model.name:
            raise validators.ValidationError("Vui lòng nhập tên món.")
        if not model.unit:
            raise validators.ValidationError("Vui lòng nhập đơn vị.")
        if model.sort_order is None:
            model.sort_order = 0

    def on_model_delete(self, model):
        from ..models import MenuIngredientUsage, OrderItem

        if OrderItem.query.filter_by(menu_item_id=model.id).first():
            raise validators.ValidationError(
                f"Món '{model.name}' đã có trong đơn hàng nên không thể xóa "
                "(để giữ lịch sử). Hãy sửa món và bỏ chọn 'Đang bán'."
            )
        if MenuIngredientUsage.query.filter_by(menu_item_id=model.id).first():
            raise validators.ValidationError(
                f"Món '{model.name}' đang có công thức nguyên liệu nên không thể xóa. "
                "Hãy bỏ chọn 'Đang bán'."
            )


# ---------------------------------------------------------------------------
# Bàn
# ---------------------------------------------------------------------------

class DiningTableView(AdminModelView):
    """CRUD bàn. Tắt bàn chỉ ẩn khỏi đơn mới, không sửa đơn đã có."""

    unique_message = "Mã bàn đã tồn tại."

    column_list = ["code", "name", "is_active"]
    column_labels = {"code": "Mã bàn", "name": "Tên bàn", "is_active": "Đang dùng"}
    column_searchable_list = ["code", "name"]
    column_filters = ["is_active"]
    column_sortable_list = ["code", "name", "is_active"]
    column_default_sort = "code"
    column_formatters = {"is_active": lambda v, c, m, p: _yes_no(m.is_active)}

    form_columns = ["code", "name", "is_active"]
    form_overrides = {"is_active": BooleanField}
    form_args = {
        "code": {
            "label": "Mã bàn (vd: B01)",
            "filters": [lambda s: s.strip().upper() if isinstance(s, str) else s],
            "validators": [
                validators.InputRequired(message="Vui lòng nhập mã bàn."),
                validators.Length(max=20, message="Mã bàn tối đa 20 ký tự."),
            ],
        },
        "name": {
            "label": "Tên bàn (vd: Bàn 1)",
            "filters": [lambda s: s.strip() if isinstance(s, str) else s],
            "validators": [
                validators.InputRequired(message="Vui lòng nhập tên bàn."),
                validators.Length(max=50, message="Tên bàn tối đa 50 ký tự."),
            ],
        },
        "is_active": {"label": "Đang dùng", "default": True},
    }

    def on_model_change(self, form, model, is_created):
        if not model.code:
            raise validators.ValidationError("Vui lòng nhập mã bàn.")
        if not model.name:
            raise validators.ValidationError("Vui lòng nhập tên bàn.")

    def on_model_delete(self, model):
        from ..models import Order

        if Order.query.filter_by(table_id=model.id).first():
            raise validators.ValidationError(
                f"Bàn '{model.code}' đã có đơn hàng nên không thể xóa. "
                "Hãy sửa bàn và bỏ chọn 'Đang dùng'."
            )


# ---------------------------------------------------------------------------
# Phí dịch vụ
# ---------------------------------------------------------------------------

class FeeView(AdminModelView):
    """
    Phí phục vụ theo phần trăm, 0–100%, mặc định 5%.
    Không xóa (dùng 'Áp dụng' = Không). Đơn đã có giữ fee_snapshot riêng,
    nên đổi phí chỉ ảnh hưởng đơn tạo sau đó.
    """

    unique_message = "Mã phí đã tồn tại."
    can_delete = False

    column_list = ["code", "name", "value", "is_active"]
    column_labels = {
        "code": "Mã phí",
        "name": "Tên phí",
        "value": "Mức phí",
        "is_active": "Áp dụng",
    }
    column_formatters = {
        "value": lambda v, c, m, p: (
            f"{m.value.normalize():f}%" if m.kind == FEE_PERCENT
            else f"{_vnd(m.value)} (cố định — không sửa ở trang này)"
        ),
        "is_active": lambda v, c, m, p: _yes_no(m.is_active),
    }
    column_filters = ["is_active"]

    # Không cho chọn "kind": tuần 1 chỉ yêu cầu phí phần trăm
    form_columns = ["code", "name", "value", "is_active"]
    form_overrides = {"value": PercentField, "is_active": BooleanField}
    form_args = {
        "code": {
            "label": "Mã phí (vd: SERVICE)",
            "default": "SERVICE",
            "filters": [lambda s: s.strip().upper() if isinstance(s, str) else s],
            "validators": [
                validators.InputRequired(message="Vui lòng nhập mã phí."),
                validators.Length(max=30, message="Mã phí tối đa 30 ký tự."),
            ],
        },
        "name": {
            "label": "Tên phí",
            "default": "Phí phục vụ",
            "filters": [lambda s: s.strip() if isinstance(s, str) else s],
            "validators": [
                validators.InputRequired(message="Vui lòng nhập tên phí."),
                validators.Length(max=100, message="Tên phí tối đa 100 ký tự."),
            ],
        },
        "value": {
            "label": "Mức phí (%) — từ 0 đến 100",
            "default": DEFAULT_FEE_PERCENT,
            "places": 2,
            "validators": [
                validators.InputRequired(message="Vui lòng nhập mức phí."),
                validators.NumberRange(min=0, max=100,
                                       message="Phí phải nằm trong khoảng 0–100%%."),
            ],
        },
        "is_active": {"label": "Áp dụng cho đơn mới", "default": True},
    }

    def on_model_change(self, form, model, is_created):
        if model.kind and model.kind != FEE_PERCENT and not is_created:
            raise validators.ValidationError(
                "Phí này không phải loại phần trăm; trang này chỉ sửa phí phần trăm."
            )
        model.kind = FEE_PERCENT
        value = Decimal(model.value)
        if value < 0 or value > 100:
            raise validators.ValidationError("Phí phải nằm trong khoảng 0–100%.")
        model.value = value.quantize(Decimal("0.01"))
