import click
from flask.cli import with_appcontext

from .constants import ROLES, ROLE_STAFF
from .extensions import db
from .models import User


@click.command("create-user")
@click.option("--username", prompt=True)
@click.option("--full-name", default="")
@click.option("--role", type=click.Choice(ROLES), default=ROLE_STAFF, show_default=True)
@click.password_option(confirmation_prompt=True)  # nhập ẩn, không lưu vào Git
@with_appcontext
def create_user(username, full_name, role, password):
    if User.query.filter_by(username=username).first():
        raise click.ClickException(f"User '{username}' đã tồn tại.")
    u = User(username=username, full_name=full_name, role=role)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    click.echo(f"Đã tạo {username} ({role}).")


def init_cli(app):
    app.cli.add_command(create_user)
    