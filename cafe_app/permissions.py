from functools import wraps

from flask import abort
from flask_login import current_user

from .constants import ROLE_ADMIN


def role_required(*roles):
    allowed = set(roles) | {ROLE_ADMIN}

    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in allowed:
                abort(403)
            return fn(*a, **kw)
        return wrapper
    return deco