"""M41-hotfix2 · .env 加载回归（dev_start 提示「复制 .env.example 为 .env」曾无任何代码兑现）。"""

from __future__ import annotations

import os


def test_load_env_file_populates_without_override(tmp_path, monkeypatch):
    from apps.api.config import load_env_file

    f = tmp_path / ".env"
    f.write_text(
        "# 注释\n"
        "TIANZE_LLM_API_KEY=from-file\n"
        "\n"
        'QUOTED="qq"\n'
        "EXISTING=from-file-too\n",
        encoding="utf-8")
    monkeypatch.delenv("TIANZE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("QUOTED", raising=False)
    monkeypatch.setenv("EXISTING", "keep-me")

    loaded = load_env_file(f)

    assert set(loaded) == {"TIANZE_LLM_API_KEY", "QUOTED"}
    assert os.environ["TIANZE_LLM_API_KEY"] == "from-file"
    assert os.environ["QUOTED"] == "qq"          # 引号被剥除
    assert os.environ["EXISTING"] == "keep-me"   # 已有环境变量不覆盖


def test_load_env_file_missing_and_repo_root(monkeypatch, tmp_path):
    from apps.api.config import load_env_file
    assert load_env_file(tmp_path / "nope.env") == {}
    # 默认路径为仓库根 .env；仓库不应携带 .env（密钥纪律）
    root_env = __file__.split("apps")[0] + ".env"
    import os
    assert not os.path.exists(root_env) or "# 测试环境" in open(root_env, encoding="utf-8").read(200)
