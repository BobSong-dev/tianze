"""知识规则加载器：knowledge/rules/**/*.json → ExecutableRule（Pydantic 校验）。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from tianze.knowledge.models import ExecutableRule

_REPO = Path(__file__).resolve().parents[2]


def knowledge_root() -> Path:
    return _REPO / "knowledge"


@lru_cache(maxsize=8)
def load_rules(rel_path: str) -> tuple[ExecutableRule, ...]:
    """加载并校验规则文件（路径相对 knowledge/）。缓存按路径。"""
    path = knowledge_root() / rel_path
    data = json.loads(path.read_text(encoding="utf-8"))
    return tuple(ExecutableRule.model_validate(r) for r in data["rules"])


@lru_cache(maxsize=8)
def load_json(rel_path: str) -> dict:
    return json.loads((knowledge_root() / rel_path).read_text(encoding="utf-8"))


def load_tiaohou_rules() -> tuple[ExecutableRule, ...]:
    return load_rules("rules/tiaohou/rules.json")


def load_tiaohou_conflicts() -> list[dict]:
    return load_json("rules/tiaohou/conflicts.json").get("conflicts", [])
