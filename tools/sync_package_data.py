"""M20 · 包内数据同步：knowledge/rules → tianze/_data/knowledge（安装副本）。

安装模式的 SDK/CLI 需要 rules/**（tiaohou/temporal/event + conflicts/rescues/graph）；
normalized cases 与 raw 体积大且安装模式不需要，不同步。
每次构建/发布前运行；test_package_data.py 校验副本与源一致。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SRC = os.path.join("knowledge", "rules")
DST = os.path.join("tianze", "_data", "knowledge")


def _hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     ensure_ascii=False).encode()).hexdigest()[:12]


def main() -> int:
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    for root, _dirs, files in os.walk(SRC):
        rel = os.path.relpath(root, SRC)
        dst_dir = os.path.join(DST, rel) if rel != "." else DST
        os.makedirs(dst_dir, exist_ok=True)
        for fn in files:
            shutil.copy2(os.path.join(root, fn), os.path.join(dst_dir, fn))
    # manifest（哈希清单，供安装模式自检）
    manifest = {}
    for root, _dirs, files in os.walk(DST):
        for fn in files:
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, DST)
            payload = json.load(open(p, encoding="utf-8"))
            manifest[rel.replace("\\", "/")] = _hash(payload)
    with open(os.path.join(DST, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"schemaVersion": "1.0.0", "files": manifest}, f,
                  ensure_ascii=False, indent=1, sort_keys=True)
    print(f"包内数据同步完成：{len(manifest)} 个文件 → {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
