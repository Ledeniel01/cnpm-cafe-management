from functools import wraps

from flask import abort
from flask_login import current_user, login_required

from . import constants as C

PERM_VIEW = set(C.ROLES)
PERM_CONFIRM = {C.ROLE_STAFF, C.ROLE_ADMIN}
PERM_PAY = {C.ROLE_CASHIER, C.ROLE_ADMIN}


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator