"""Đọc cấu hình riêng CNPM, không để mật khẩu hoặc secret trong source."""
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config():
    load_dotenv(PROJECT_ROOT / ".env", override=False, encoding="utf-8-sig")
    return {
        "SECRET_KEY": os.environ.get("CNPM_SECRET_KEY", ""),
        "SQLALCHEMY_DATABASE_URI": os.environ.get("CNPM_DATABASE_URL", ""),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "pool_pre_ping": True,
            "pool_recycle": 280,
        },
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
    }