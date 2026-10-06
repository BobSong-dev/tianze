"""M14 · 事件规则加载器（ExecutableRule domain=event）。"""

from __future__ import annotations

import json
import os
from functools import lru_cache

__all__ = ["load_event_rules", "EVENT_RULES_PATH"]

EVENT_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "knowledge", "rules", "event", "rules.json",
)


@lru_cache(maxsize=1)
def load_event_rules() -> list[dict]:
    if not os.path.exists(EVENT_RULES_PATH):
        return []
    payload = json.load(open(EVENT_RULES_PATH, encoding="utf-8"))
    return payload["rules"]
