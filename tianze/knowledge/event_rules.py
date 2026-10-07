"""M14 · 事件规则加载器（ExecutableRule domain=event）。"""

from __future__ import annotations

import json
import os
from functools import lru_cache

__all__ = ["load_event_rules", "EVENT_RULES_PATH"]

def _rules_path() -> str:
    from tianze.paths import data_root
    return str(data_root() / "rules" / "event" / "rules.json")


EVENT_RULES_PATH = _rules_path()


@lru_cache(maxsize=1)
def load_event_rules() -> list[dict]:
    path = _rules_path()
    if not os.path.exists(path):
        return []
    payload = json.load(open(path, encoding="utf-8"))
    return payload["rules"]
