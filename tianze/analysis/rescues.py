"""M16 · 救应 / 例外条件化推理（rescue & exception applicability）。

原则：
- 不另造旺衰/格局算法——所有条件谓词复用现有 Engine 事实
  （StrengthReport 的 weighted verdict、命/岁十神分布、Temporal relations）
- 谓词透明：每个谓词 id 对应一个纯函数，依据与边界随结果输出
- 声明驱动：knowledge/rules/event/rescues.json 声明「谁救谁、什么条件、什么效果」；
  conflicts.json 的 specificCondition 引用同一谓词 id → SPECIFIC_EXCEPTION 只在
  救应条件成立时启用（上下文相关优先级，不是全局 A>B）
- 谓词的 ENGINEERING 映射（如「财为喜神」≈ weighted verdict ∈ {偏强, 极强}）
  显式标注，不冒充古籍明文
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

__all__ = ["evaluate_rescues", "RESCUES_PATH", "get_rescue_declarations"]

RESCUES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "knowledge", "rules", "event", "rescues.json",
)


def _ten_god(dm: str, s: str) -> str:
    from tianze.ganzhi.tables import ten_god as _tg
    return _tg(dm, s).value


def _temporal_stems(ectx):
    for u in ectx.temporal_units:
        if u.get("stem"):
            yield u["layer"], u["stem"]


def _natal_stems(ectx):
    for s in ectx.natal_stems:
        if s:
            yield s


def _has_god(ectx, gods: set[str]) -> list[str]:
    """命/岁中某十神是否可见（返回证据列表）。"""
    ev = []
    for s in _natal_stems(ectx):
        if _ten_god(ectx.day_master, s) in gods:
            ev.append(f"原局天干{s}（{_ten_god(ectx.day_master, s)}）")
    for _l, s in _temporal_stems(ectx):
        if _ten_god(ectx.day_master, s) in gods:
            ev.append(f"岁运天干{s}（{_ten_god(ectx.day_master, s)}）")
    return ev


# ---- 谓词注册表：id → (ectx) -> (active, evidence, note) ----
# 全部复用现有 Engine 事实；ENGINEERING 映射显式标注。

def _p_yin_present(ectx):
    """印星可见（印制伤护官，DTZ-43：以印制伤护官）。"""
    ev = _has_god(ectx, {"正印", "偏印"})
    return bool(ev), ev, "印星可见（CLASSICAL：DTZ-43 以印制伤护官）"


def _p_cai_present(ectx):
    """财星可见（财化伤生官，DTZ-39：伤官有财皆可见官）。"""
    ev = _has_god(ectx, {"正财", "偏财"})
    return bool(ev), ev, "财星可见（CLASSICAL：DTZ-39 以财化伤生官）"


def _strength_readings(ectx) -> list[tuple[str, str]]:
    """收集全部可用的旺衰判定（weighted/fuyi/dimension 三维）——复用 Engine 输出。"""
    readings: list[tuple[str, str]] = []
    if getattr(ectx, "strength_verdict", None):
        readings.append(("weighted", ectx.strength_verdict))
    if getattr(ectx, "fuyi_verdict", None) and ectx.fuyi_verdict != "UNCERTAIN":
        readings.append(("fuyi", ectx.fuyi_verdict))
    if getattr(ectx, "dimension_de_shi", None) is not None:
        readings.append(("dimension 得势", "偏强向" if ectx.dimension_de_shi else "偏弱向"))
    if getattr(ectx, "dimension_de_ling", None) is not None:
        readings.append(("dimension 得令", "偏强向" if ectx.dimension_de_ling else "偏弱向"))
    if getattr(ectx, "dimension_de_di", None) is not None:
        readings.append(("dimension 得地", "偏强向" if ectx.dimension_de_di else "偏弱向"))
    return readings


def _p_wealth_favorable(ectx):
    """财为喜神方向（SS-R10 前提）——多方法一致才启用，禁止单一布尔量。

    ENGINEERING 映射（显式标注）：
    - weighted ∈ {偏强, 极强} → 喜神方向读数
    - fuyi ∈ {偏强, 极强} → 喜神方向读数
    - dimension 得势=True → 喜神方向读数
    多方法读数不一致 → 谓词不启用（口径分歧，救应不激活），分歧如实记录。
    """
    readings = _strength_readings(ectx)
    strong = {"偏强", "极强", "偏强向"}
    weak = {"偏弱", "极弱", "偏弱向"}
    votes = [1 if (v in strong) else 0 if (v in weak) else None for _n, v in readings]
    ev = [f"{n}：{v}" for n, v in readings]
    known = [x for x in votes if x is not None]
    if not known:
        return False, ev + ["无可用旺衰读数"], "财为喜神方向（证据不足，不启用）"
    if all(x == 1 for x in known):
        return True, ev + ["ENGINEERING 映射：多方法一致偏强 → 财为喜神方向（SS-R10 前提）"],             "财为喜神方向（ENGINEERING：多方法一致偏强）"
    if all(x == 0 for x in known):
        return False, ev + ["多方法一致偏弱 → 财为忌神方向"],             "财为忌神方向（ENGINEERING：多方法一致偏弱）"
    return False, ev + ["旺衰读数分歧 → 口径不一致，救应不激活（不裁决）"],         "强度口径分歧（ENGINEERING：多方法不一致，救应不启用）"


def _p_wealth_unfavorable(ectx):
    """财为忌神方向（SS-R10：「如财为忌神，诚如是论」——身弱见财反主负担）。

    与 wealth_favorable 同一套多方法读数，方向相反；两者互斥。
    """
    active, ev, note = _p_wealth_favorable(ectx)
    if "一致偏强" in note:
        return False, ev, "财为喜神方向成立 → 忌神方向不启用"
    if "一致偏弱" in note:
        return True, ev, "财为忌神方向（ENGINEERING：多方法一致偏弱，SS-R10 前提）"
    return False, ev, note


def _p_guan_sha_has_control(ectx):
    """官杀有制化（DTZ-33：偏官无单用者，必与食、印、财相连也）。"""
    control = _has_god(ectx, {"食神", "伤官", "正印", "偏印"})
    guan = _has_god(ectx, {"正官", "七杀"})
    ev = guan + control
    active = bool(guan) and bool(control)
    return active, ev + ["CLASSICAL：DTZ-33「偏官无单用者，必与食、印、财相连也」"],         "官杀有制化相连（食伤/印并见）"


def _p_guan_bridges_cai_yin(ectx):
    """官星通关（财印并见 + 官星亦见：财生官、官生印，贪生忘克）。"""
    cai = _has_god(ectx, {"正财", "偏财"})
    yin = _has_god(ectx, {"正印", "偏印"})
    guan = _has_god(ectx, {"正官", "七杀"})
    ev = cai + yin + guan
    active = bool(cai and yin and guan)
    note = "财生官、官生印：官星通关（概念出处 jiwenxu 贪生忘克，PROJECT_REFERENCE）"
    return active, ev, note


def _p_sha_weak_body_strong(ectx):
    """身强煞浅（SS-R05：身强煞弱→煞化为官，假煞为权不可制）。

    ENGINEERING 映射：weighted ∈ {偏强, 极强} 视为身强。
    """
    v = getattr(ectx, "strength_verdict", None)
    active = v in ("偏强", "极强")
    ev = ([f"weighted 旺衰判定：{v}"] if v else []) + \
        ["ENGINEERING 映射：偏强/极强 → 身强煞浅方向（SS-R05 前提）"]
    return active, ev, "身强煞浅（ENGINEERING：weighted ∈ {偏强, 极强}）"


RESCUE_PREDICATES = {
    "yin_present": _p_yin_present,
    "cai_present": _p_cai_present,
    "wealth_favorable": _p_wealth_favorable,
    "wealth_unfavorable": _p_wealth_unfavorable,
    "guan_bridges_cai_yin": _p_guan_bridges_cai_yin,
    "sha_weak_body_strong": _p_sha_weak_body_strong,
    "guan_sha_has_control": _p_guan_sha_has_control,
}


@lru_cache(maxsize=1)
def get_rescue_declarations() -> list[dict]:
    """救应声明：{id, target: ruleId, predicate: id, effect: weaken|flip-to-support, note}。"""
    if not os.path.exists(RESCUES_PATH):
        return []
    payload = json.load(open(RESCUES_PATH, encoding="utf-8"))
    return payload.get("rescues", [])


def evaluate_rescues(ectx) -> dict[str, dict]:
    """评估全部谓词一次 → {predicate_id: {active, evidence, note}}。

    谓词与具体规则解耦：一次评估，多处引用（rescues.json 与 conflicts.json）。
    """
    out: dict[str, dict] = {}
    for pid, fn in RESCUE_PREDICATES.items():
        try:
            active, evidence, note = fn(ectx)
        except Exception as exc:  # 谓词崩溃必须显式暴露，不静默
            raise RuntimeError(f"救应谓词 {pid} 评估失败: {exc}") from exc
        out[pid] = {"active": bool(active), "evidence": evidence, "note": note}
    return out
