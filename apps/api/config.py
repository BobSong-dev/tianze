"""Tianze API 配置。"""

import os

API_VERSION = "v1"
CORS_ORIGINS = os.environ.get("TIANZE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
MAX_BODY_SIZE = 64 * 1024  # 64KB
