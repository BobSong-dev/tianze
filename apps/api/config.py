"""Tianze API 配置。"""

from __future__ import annotations

import os
from pathlib import Path

API_VERSION = "v1"
CORS_ORIGINS = os.environ.get("TIANZE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
MAX_BODY_SIZE = 64 * 1024  # 64KB


def load_env_file(path: str | os.PathLike | None = None) -> dict[str, str]:
    """加载仓库根目录的 .env（仅 KEY=VALUE 行；已有环境变量不覆盖）。

    stdlib 实现，不引入 python-dotenv 依赖。dev_start.py 的启动提示
    「复制 .env.example 为 .env 填 Key」由本函数兑现——否则用户按提示
    把 Key 放进 .env 后 API 进程根本读不到（曾导致"填了 Key 仍提示
    未配置"）。返回实际加载的键集合（仅用于日志/测试，值不外泄）。
    """
    p = Path(path) if path else Path(__file__).resolve().parents[2] / ".env"
    if not p.is_file():
        return {}
    loaded: dict[str, str] = {}
    try:
        for raw in p.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val
                loaded[key] = "loaded"
    except OSError:
        return {}
    return loaded
