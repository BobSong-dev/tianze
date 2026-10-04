#!/usr/bin/env python3
"""Tianze 开发启动与测试脚本（跨平台 Python launcher）。

用法：
    python scripts/dev.py              # 启动 API + Web（并行）
    python scripts/dev.py test-all     # 运行全部测试
    python scripts/dev.py build        # 生产构建
"""
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
if not Path(VENV_PY).exists():
    VENV_PY = str(ROOT / ".venv" / "bin" / "python3")

def run(cmd: str, cwd: Path | None = None, blocking: bool = True):
    print(f"[dev] $ {cmd}")
    p = subprocess.Popen(cmd, shell=True, cwd=cwd or ROOT)
    if blocking:
        p.wait()
        return p.returncode
    return p

def start_dev():
    procs = []
    api_cmd = f'"{VENV_PY}" -m uvicorn apps.api.main:app --reload --port 8000'
    web_cmd = "npm run dev"
    print("[dev] Starting API on :8000 and Web on :5173")
    procs.append(run(api_cmd, blocking=False))
    time.sleep(2)
    procs.append(run(web_cmd, cwd=ROOT / "apps" / "web", blocking=False))
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()

def test_all():
    steps = [
        ("Python Core", f'"{VENV_PY}" -m pytest tests/ -q'),
        ("API Contract", f'"{VENV_PY}" -m pytest apps/api/tests/ -q'),
        ("Knowledge Validator", f'"{VENV_PY}" tools/validate_knowledge.py'),
        ("Case Validator", f'"{VENV_PY}" tools/validate_cases.py'),
        ("Case Regression", f'"{VENV_PY}" tools/case_regression.py compare'),
        ("Frontend Unit", "npx vitest run", ROOT / "apps" / "web"),
    ]
    failures = []
    for item in steps:
        name = item[0]
        cmd = item[1]
        cwd = item[2] if len(item) > 2 else None
        print(f"\n=== {name} ===")
        rc = run(cmd, cwd=cwd)
        if rc != 0:
            failures.append(name)
    if failures:
        print(f"\nFAILED: {failures}")
        sys.exit(1)
    print("\nAll tests passed.")

def build():
    rc1 = run("npm run build", cwd=ROOT / "apps" / "web")
    sys.exit(rc1)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dev"
    if cmd == "dev":
        start_dev()
    elif cmd == "test-all":
        test_all()
    elif cmd == "build":
        build()
    else:
        print(f"Usage: python scripts/dev.py [dev|test-all|build]")
        sys.exit(1)
