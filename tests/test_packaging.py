"""M20：Packaging / CLI / 数据路径测试。"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from tianze.paths import data_root


def test_data_root_dev_mode():
    """开发模式：data_root = repo knowledge/。"""
    root = data_root()
    assert (root / "rules" / "event" / "rules.json").exists()


def test_package_data_synced():
    """包内 _data 副本与源 knowledge/rules 一致（manifest 哈希）。"""
    import hashlib
    manifest = json.load(open("tianze/_data/knowledge/manifest.json", encoding="utf-8"))
    for rel, h in manifest["files"].items():
        payload = json.load(open(os.path.join("tianze/_data/knowledge", rel),
                                 encoding="utf-8"))
        got = hashlib.sha256(json.dumps(payload, sort_keys=True,
                                        ensure_ascii=False).encode()).hexdigest()[:12]
        assert got == h, rel


def test_version_single_source():
    """pyproject dynamic version = tianze.__version__（单一事实源）。"""
    import tianze
    txt = open("pyproject.toml", encoding="utf-8").read()
    assert 'dynamic = ["version"]' in txt
    assert 'version = { attr = "tianze.__version__" }' in txt
    assert tianze.__version__ == "0.3.0"


def test_cli_version_and_analyze():
    py = sys.executable
    r = subprocess.run([py, "-m", "tianze.cli", "version"], capture_output=True,
                       encoding="utf-8", errors="replace",
                       cwd=os.path.dirname(os.path.abspath(__file__)) + "/..")
    assert r.returncode == 0
    d = json.loads(r.stdout)
    assert d["engine"] == "0.3.0"
    r2 = subprocess.run([py, "-m", "tianze.cli", "analyze", "--date", "2003-08-18",
                         "--time", "14:30", "--gender", "male", "--format", "json"],
                        capture_output=True, encoding="utf-8", errors="replace",
                        cwd=os.path.dirname(os.path.abspath(__file__)) + "/..")
    assert r2.returncode == 0
    out = json.loads(r2.stdout)
    assert out["pillars"]["day"]["stem"] == "癸"


def test_cli_error_codes():
    py = sys.executable
    root = os.path.dirname(os.path.abspath(__file__)) + "/.."
    r = subprocess.run([py, "-m", "tianze.cli", "analyze", "--date", "bad-date"],
                       capture_output=True, encoding="utf-8", errors="replace", cwd=root)
    assert r.returncode == 1
    assert "INVALID_BIRTH_INFO" in r.stderr


def test_cli_export_html(tmp_path):
    py = sys.executable
    root = os.path.dirname(os.path.abspath(__file__)) + "/.."
    out = tmp_path / "report.html"
    r = subprocess.run([py, "-m", "tianze.cli", "export", "--date", "1984-02-05",
                        "--time", "10:30", "--gender", "male",
                        "--format", "html", "--out", str(out)],
                       capture_output=True, encoding="utf-8", errors="replace", cwd=root)
    assert r.returncode == 0 and out.exists()
    assert "<!DOCTYPE html>" in out.read_text(encoding="utf-8")
