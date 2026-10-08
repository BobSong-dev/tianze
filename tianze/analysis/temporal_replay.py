"""M30 · 统一岁运状态机：大运→流年→流月→流日 逐层推演回放。

设计（目标：每层独立快照 + 迁移原因；不因计算顺序产生矛盾）：
- 层序固定为 大运→流年→流月→流日（与 TemporalContext.temporal_units 同序），
  逐层把该层干支并入上下文、复用 analyze_temporal 统一引擎重算（不重复实现）；
- 每层输出：
    snapshot  —— 该层累计的虚神事件集合（kind:label）与关系计数
    added     —— 相对上一层新出现的事件（迁移原因 = 该层加入的干支）
    removed   —— 上一层有、本层消失的事件（如岁运字变化后冲关系不再成立）
- 保证：
    * natal 步（第 0 步）恒无岁运事件；
    * 同一 (kind,label) 事件归属唯一层（其触发干支所在层）；
    * 回放可复现（纯函数，同输入同输出）。

不输出吉凶；只做状态迁移的结构回放，供 Web 时间轴与命例研究使用。
"""

from __future__ import annotations

from typing import Any

from tianze.analysis.temporal import analyze_temporal
from tianze.domain.models import CamelizeModel

__all__ = ["ReplayStep", "TemporalReplay", "replay_temporal",
           "TEMPORAL_REPLAY_SCHEMA_VERSION"]

TEMPORAL_REPLAY_SCHEMA_VERSION = "1.0.0"

_XUSHI_KINDS = ("arch", "arch_fill", "arch_broken", "arch_unfill", "hidden_combination")

_LAYER_CN = {"luck": "大运", "annual": "流年", "monthly": "流月", "daily": "流日"}


class ReplayStep(CamelizeModel):
    layer: str                        # natal / luck / annual / monthly / daily
    ganzhi: str = ""                  # 该层加入的干支（natal 为空）
    added: list[dict[str, str]] = []  # 新出现事件 [{kind, label, refId}]
    removed: list[dict[str, str]] = []
    snapshotKeys: list[str] = []      # 该层累计事件键（kind:label）
    relationCount: int = 0
    note: str = ""


class TemporalReplay(CamelizeModel):
    natalStems: list[str | None] = []
    natalBranches: list[str | None] = []
    steps: list[ReplayStep] = []
    replaySchemaVersion: str = TEMPORAL_REPLAY_SCHEMA_VERSION
    warnings: list[str] = []


def _event_keys(relations: list) -> dict[str, dict]:
    return {f"{r.kind}:{r.label}": {"kind": r.kind, "label": r.label,
                                    "refId": f"replay:{r.kind}:{r.label}"}
            for r in relations if r.kind in _XUSHI_KINDS}


def replay_temporal(
    natal_stems: list[str | None],
    natal_branches: list[str | None],
    day_master: str,
    luck: tuple[str | None, str | None] | None = None,
    annual: tuple[str | None, str | None] | None = None,
    monthly: tuple[str | None, str | None] | None = None,
    daily: tuple[str | None, str | None] | None = None,
) -> TemporalReplay:
    """逐层推演：natal → luck → annual → monthly → daily（固定层序）。

    每层复用 analyze_temporal（统一引擎）重算并 diff 虚神事件集合。
    """
    layers: list[tuple[str, tuple[str | None, str | None] | None]] = [
        ("luck", luck), ("annual", annual),
        ("monthly", monthly), ("daily", daily),
    ]
    steps: list[ReplayStep] = []
    prev_keys: dict[str, dict] = {}

    def _run(ctx_layers: list[tuple[str, tuple[str | None, str | None] | None]]) -> tuple[dict, int]:
        kw: dict[str, Any] = dict(natal_stems=list(natal_stems),
                                  natal_branches=list(natal_branches),
                                  day_master=day_master)
        for name, pair in ctx_layers:
            if pair and (pair[0] or pair[1]):
                kw[f"{name}_stem"], kw[f"{name}_branch"] = pair[0], pair[1]
        ta = analyze_temporal(**kw)
        return _event_keys(ta.relations), len(ta.relations)

    # 第 0 步：natal
    keys0, cnt0 = _run([])
    steps.append(ReplayStep(
        layer="natal", ganzhi="", added=[], removed=[],
        snapshotKeys=sorted(keys0), relationCount=cnt0,
        note="原局基线（无岁运事件）" if not keys0 else "原局基线",
    ))
    prev_keys = keys0

    active: list[tuple[str, tuple[str | None, str | None] | None]] = []
    for name, pair in layers:
        if not (pair and (pair[0] or pair[1])):
            continue
        active = active + [(name, pair)]
        keys, cnt = _run(active)
        added = [keys[k] for k in sorted(set(keys) - set(prev_keys))]
        removed = [prev_keys[k] for k in sorted(set(prev_keys) - set(keys))]
        gz = (pair[0] or "") + (pair[1] or "")
        steps.append(ReplayStep(
            layer=name, ganzhi=gz, added=added, removed=removed,
            snapshotKeys=sorted(keys), relationCount=cnt,
            note=f"加入{_LAYER_CN[name]}{gz}：+{len(added)}/-{len(removed)} 虚神事件",
        ))
        prev_keys = keys

    return TemporalReplay(
        natalStems=list(natal_stems), natalBranches=list(natal_branches),
        steps=steps,
        warnings=["状态回放仅描述虚神候选事件的结构迁移，不构成吉凶或事件预测。",
                  "层序固定为 大运→流年→流月→流日；每层事件归属其触发干支所在层。"],
    )
