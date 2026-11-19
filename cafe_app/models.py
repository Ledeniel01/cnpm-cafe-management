from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

from .constants import (
    MONEY_PRECISION, MONEY_SCALE, QTY_PRECISION, QTY_SCALE,
    ROLE_STAFF, STATUS_NEW, ORDER_DINE_IN,
)
from .extensions import db

Money = db.Numeric(MONEY_PRECISION, MONEY_SCALE)
Qty = db.Numeric(QTY_PRECISION, QTY_SCALE)


class TimestampMixin:
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow,
                           onupdate=datetime.utcnow)


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    full_name = db.Column(db.String(100), nullable=False, default="")
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_STAFF)
    is_active_flag = db.Column("is_active", db.Boolean, nullable=False, default=True)

    @property
    def is_active(self):
        return bool(self.is_active_flag)

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


class DiningTable(TimestampMixin, db.Model):
    __tablename__ = "dining_tables"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class MenuItem(TimestampMixin, db.Model):
    __tablename__ = "menu_items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=False, default="")
    unit = db.Column(db.String(20), nullable=False, default="ly")
    price = db.Column(Money, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    __table_args__ = (CheckConstraint("price >= 0", name="ck_menu_price_nonneg"),)


class Fee(TimestampMixin, db.Model):
    __tablename__ = "fees"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    kind = db.Column(db.String(10), nullable=False)
    value = db.Column(db.Numeric(12, 2), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class Order(TimestampMixin, db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    order_type = db.Column(db.String(20), nullable=False, default=ORDER_DINE_IN)
    table_id = db.Column(db.Integer, db.ForeignKey("dining_tables.id"), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False, default="")
    customer_phone = db.Column(db.String(20), nullable=False, index=True)
    note = db.Column(db.String(255), nullable=False, default="")

    status = db.Column(db.String(20), nullable=False, default=STATUS_NEW, index=True)
    subtotal = db.Column(Money, nullable=False, default=0)
    fee_amount = db.Column(Money, nullable=False, default=0)
    total = db.Column(Money, nullable=False, default=0)
    fee_snapshot = db.Column(db.Text, nullable=True)

    confirmed_at = db.Column(db.DateTime, nullable=True)
    confirmed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    paid_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    cancel_reason = db.Column(db.String(255), nullable=True)
    edit_reason = db.Column(db.String(255), nullable=True)
    version = db.Column(db.Integer, nullable=False, default=1)

    table = db.relationship("DiningTable")
    items = db.relationship("OrderItem", back_populates="order",
                            cascade="all, delete-orphan", order_by="OrderItem.id")
    confirmed_by = db.relationship("User", foreign_keys=[confirmed_by_id])
    paid_by = db.relationship("User", foreign_keys=[paid_by_id])
    cancelled_by = db.relationship("User", foreign_keys=[cancelled_by_id])

    __mapper_args__ = {"version_id_col": version}
    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_order_total_nonneg"),
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    unit_price = db.Column(Money, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    line_total = db.Column(Money, nullable=False)

    order = db.relationship("Order", back_populates="items")
    menu_item = db.relationship("MenuItem")
    __table_args__ = (
        UniqueConstraint("order_id", "menu_item_id", name="uq_order_menu_item"),
        CheckConstraint("quantity > 0", name="ck_orderitem_qty_pos"),
    )


class Ingredient(TimestampMixin, db.Model):
    __tablename__ = "ingredients"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    unit = db.Column(db.String(20), nullable=False)
    stock_qty = db.Column(Qty, nullable=False, default=0)
    min_qty = db.Column(Qty, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class StockReceipt(TimestampMixin, db.Model):
    __tablename__ = "stock_receipts"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    supplier = db.Column(db.String(100), nullable=False, default="")
    received_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    note = db.Column(db.String(255), nullable=False, default="")
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_by = db.relationship("User")
    lines = db.relationship("StockReceiptLine", back_populates="receipt",
                            cascade="all, delete-orphan")


class StockReceiptLine(db.Model):
    __tablename__ = "stock_receipt_lines"
    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey("stock_receipts.id"), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("ingredients.id"), nullable=False)
    quantity = db.Column(Qty, nullable=False)
    unit_cost = db.Column(Money, nullable=False, default=0)

    receipt = db.relationship("StockReceipt", back_populates="lines")
    ingredient = db.relationship("Ingredient")
    __table_args__ = (
        UniqueConstraint("receipt_id", "ingredient_id", name="uq_receipt_ingredient"),
        CheckConstraint("quantity > 0", name="ck_receiptline_qty_pos"),
    )


class MenuIngredientUsage(db.Model):
    __tablename__ = "menu_ingredient_usages"
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey("ingredients.id"), nullable=False)
    quantity_per_unit = db.Column(Qty, nullable=False)

    menu_item = db.relationship("MenuItem")
    ingredient = db.relationship("Ingredient")
    __table_args__ = (
        UniqueConstraint("menu_item_id", "ingredient_id", name="uq_menu_ingredient"),
        CheckConstraint("quantity_per_unit > 0", name="ck_usage_qty_pos"),
    )