"""M20 · 数据路径解析：dev（repo）与安装（package data）双模式。

解析顺序：
1. 环境变量 TIANZE_DATA_DIR（显式覆盖）
2. repo 根的 knowledge/（开发/源码运行：Path(__file__).parents[2]）
3. 包内 tianze/_data/knowledge/（安装副本：tools/sync_package_data.py 同步）

CLI 与 SDK 复用本模块，不在业务代码中各自拼路径。
"""

from __future__ import annotations

import os
from pathlib import Path

_PACKAGE = Path(__file__).resolve().parent
_REPO = _PACKAGE.parent


def data_root() -> Path:
    """knowledge 数据根目录（含 rules/ normalized/ raw/）。"""
    env = os.environ.get("TIANZE_DATA_DIR")
    if env and os.path.isdir(env):
        return Path(env)
    repo_knowledge = _REPO / "knowledge"
    if repo_knowledge.is_dir():
        return repo_knowledge
    packaged = _PACKAGE / "_data" / "knowledge"
    if packaged.is_dir():
        return packaged
    raise FileNotFoundError(
        "未找到 Tianze 数据目录：设置 TIANZE_DATA_DIR，或在仓库内运行，"
        "或确认安装包含 tianze/_data/knowledge")


def repo_root() -> Path:
    """仓库根（开发模式；安装模式下返回包父目录，供工件读写回退）。"""
    return _REPO
