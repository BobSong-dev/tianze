"""Tianze 一键启动（本地开发/试用）：API :8000 + Web :5173。

用法（仓库根目录）：
    python scripts/dev_start.py          # 前台启动（Ctrl+C 全停）
    python scripts/dev_start.py --build  # 先做一次生产构建再启动

不引入任何新基础设施——只是把 README 的三条命令封装为一个入口。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _venv_python() -> str:
    for cand in (os.path.join(ROOT, ".venv", "Scripts", "python.exe"),
                 os.path.join(ROOT, ".venv", "bin", "python")):
        if os.path.exists(cand):
            return cand
    return sys.executable


def main() -> int:
    py = _venv_python()
    if "--build" in sys.argv:
        subprocess.run(["npm", "run", "build"], cwd=os.path.join(ROOT, "apps", "web"), check=True)

    print("[Tianze] 启动 API（127.0.0.1:8000，单用户本地模式）…")
    api = subprocess.Popen([py, "-m", "uvicorn", "apps.api.main:app",
                            "--host", "127.0.0.1", "--port", "8000"],
                           cwd=ROOT)
    time.sleep(1.5)
    print("[Tianze] 启动 Web 开发服务器（:5173）…")
    web = subprocess.Popen(["npm", "run", "dev"], cwd=os.path.join(ROOT, "apps", "web"),
                           shell=(os.name == "nt"))
    print("[Tianze] 就绪：Web http://localhost:5173 · API http://localhost:8000/docs")
    print("[Tianze] Ctrl+C 停止全部服务。AI 解读可选：复制 .env.example 为 .env 填 Key。")
    try:
        web.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for p in (web, api):
            if p.poll() is None:
                p.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
