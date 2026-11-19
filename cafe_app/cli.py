import click
from flask.cli import AppGroup

from . import constants as C
from .extensions import db
from .models import (DiningTable, Fee, Ingredient, MenuIngredientUsage,
                     MenuItem, User)

SEED_TABLES = [("B01", "Bàn 1"), ("B02", "Bàn 2"), ("B03", "Bàn 3"), ("B04", "Bàn 4")]

SEED_MENU = [
    ("Cà phê đen", "Cà phê", "ly", 25000),
    ("Cà phê sữa", "Cà phê", "ly", 30000),
    ("Bạc xỉu", "Cà phê", "ly", 35000),
    ("Trà đào", "Trà", "ly", 40000),
    ("Bánh flan", "Bánh", "cái", 20000),
]

SEED_FEES = [("SERVICE", "Phí dịch vụ", C.FEE_PERCENT, 5)]

SEED_INGREDIENTS = [
    ("Cà phê hạt", "g", 5000, 1000),
    ("Sữa đặc", "ml", 3000, 500),
    ("Đường", "g", 2000, 300),
]

SEED_USAGE = [
    ("Cà phê đen", "Cà phê hạt", 20),
    ("Cà phê sữa", "Cà phê hạt", 20),
    ("Cà phê sữa", "Sữa đặc", 30),
]


def seed_data():
    for code, name in SEED_TABLES:
        if not DiningTable.query.filter_by(code=code).first():
            db.session.add(DiningTable(code=code, name=name))

    for i, (name, category, unit, price) in enumerate(SEED_MENU):
        if not MenuItem.query.filter_by(name=name).first():
            db.session.add(MenuItem(name=name, category=category, unit=unit,
                                    price=price, sort_order=i))

    for code, name, kind, value in SEED_FEES:
        if not Fee.query.filter_by(code=code).first():
            db.session.add(Fee(code=code, name=name, kind=kind, value=value))

    for name, unit, stock, minimum in SEED_INGREDIENTS:
        if not Ingredient.query.filter_by(name=name).first():
            db.session.add(Ingredient(name=name, unit=unit,
                                      stock_qty=stock, min_qty=minimum))

    db.session.flush()

    for menu_name, ing_name, qty in SEED_USAGE:
        menu = MenuItem.query.filter_by(name=menu_name).first()
        ing = Ingredient.query.filter_by(name=ing_name).first()
        if menu and ing:
            exists = MenuIngredientUsage.query.filter_by(
                menu_item_id=menu.id, ingredient_id=ing.id).first()
            if not exists:
                db.session.add(MenuIngredientUsage(
                    menu_item_id=menu.id, ingredient_id=ing.id,
                    quantity_per_unit=qty))

    db.session.commit()


cafe = AppGroup("cafe")


@cafe.command("init-db")
def init_db():
    db.create_all()
    click.echo("Đã tạo bảng.")


@cafe.command("seed")
def seed():
    seed_data()
    click.echo("Đã seed xong.")


@cafe.command("create-user")
@click.option("--username", prompt=True)
@click.option("--full-name", prompt=True)
@click.option("--role", type=click.Choice(C.ROLES), prompt=True)
@click.password_option()
def create_user(username, full_name, role, password):
    if User.query.filter_by(username=username).first():
        raise click.ClickException("Username đã tồn tại.")
    if len(password) < 8:
        raise click.ClickException("Mật khẩu tối thiểu 8 ký tự.")
    user = User(username=username, full_name=full_name, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Đã tạo {username} ({role}).")


def register_cli(app):
    app.cli.add_command(cafe)