"""Điểm nạp ứng dụng cho máy chủ WSGI khi triển khai."""
from cafe_app import create_app


application = create_app()