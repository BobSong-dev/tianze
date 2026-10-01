"""M4.2 fuyi（扶抑）旺衰分析器（R21）——规则级联 + 信号计票，与 weighted 不同路径。

与 weighted 的本质差异：
- weighted 在"逐字单位"层做连续加权求和再取 ratio；
- fuyi 只消费**派生特征**（得令？根几处？印比几透？食伤财官几透？月令是否克日？），
  按**公开的计票规则 + 首中即停的级联**给出五级 verdict，允许 UNCERTAIN（证据冲突时不强行下结论）。
- 计票制本身是工程化 heuristic（ADR-023），规则表随结果输出、全部可复核。
"""

from __future__ import annotations

from tianze.analysis.strength.base import StrengthFacts
from tianze.domain.models import Provenance, RuleLevel, StrengthMethodResult, TenGod
from tianze.ganzhi.tables import ten_god

_HELPFUL: frozenset[TenGod] = frozenset({
    TenGod.BI_JIAN, TenGod.JIE_CAI, TenGod.PIAN_YIN, TenGod.ZHENG_YIN,
})
_POS_CN = {"year": "年", "month": "月", "day": "日", "hour": "时"}


class FuyiStrengthAnalyzer:
    analyzer_id = "fuyi-v1"
    name = "fuyi"

    # 级联规则表（首中即停，公开于 R21 / docs/STRENGTH.md）
    RULES: tuple[tuple[str, str, str], ...] = (
        ("R21-1", "极强", "high"),      # 得令 + 多根 + 多印比
        ("R21-2", "极弱", "high"),      # 失令 + 无根 + 无印比 + 月令克日
        ("R21-3", "极弱", "medium"),    # 失令 + 无根 + 无印比
        ("R21-4", "UNCERTAIN", "high"),  # 得令但虚浮无依（信号冲突）
        ("R21-5", "偏强", "medium"),    # 支持票领先 ≥3
        ("R21-6", "偏弱", "medium"),    # 克泄票领先 ≥3
        ("R21-7", "偏强", "low"),       # 支持票领先 ≥1
        ("R21-8", "偏弱", "low"),       # 克泄票领先 ≥1
        ("R21-9", "中和", "low"),       # 票数均衡
    )

    def _provenance(self) -> list[Provenance]:
        return [
            Provenance(level=RuleLevel.PROJECT_REFERENCE, project="Horosa/OBE/jiwenxu",
                       concept="扶抑派分析路径（月令→通根→印比帮扶 vs 克泄耗）",
                       note="仅参考分析路径顺序，未复制任何一家的权重或阈值"),
            Provenance(level=RuleLevel.ENGINEERING_HEURISTIC, project="Tianze",
                       concept="计票级联规则表 R21-1~9（作者口径，无古籍量化依据）"),
        ]

    def analyze(self, facts: StrengthFacts) -> StrengthMethodResult:
        rel = facts.month_command.relation_to_day_master
        state = rel.state.value
        root_count = len(facts.day_master_roots)

        helpers: list[str] = []
        drains: list[str] = []
        for stem, position in facts.other_stems:
            god = ten_god(facts.day_master, stem)
            label = f"{_POS_CN[position]}干{stem}（{god.value}）"
            (helpers if god in _HELPFUL else drains).append(label)
        helper_count = len(helpers)
        drain_count = len(drains)
        month_attacks = state in ("囚", "死")

        support_votes = 0
        support_evidence: list[str] = []
        if rel.in_command:
            support_votes += 1
            support_evidence.append("得令（月令状态旺）+1")
        elif state == "相":
            support_votes += 1
            support_evidence.append("月令生日主（相）+1")
        if root_count >= 1:
            support_votes += 1
            support_evidence.append(f"日主有根（{root_count} 处）+1")
        if root_count >= 2:
            support_votes += 1
            support_evidence.append(f"多根（{root_count} 处）+1")
        if helper_count >= 1:
            support_votes += 1
            support_evidence.append(f"印比透干 {helper_count} 处 +1")
        if helper_count >= 2:
            support_votes += 1
            support_evidence.append(f"印比透干 ≥2（{helper_count} 处）+1")

        drain_votes = 0
        drain_evidence: list[str] = []
        if state == "休":
            drain_votes += 1
            drain_evidence.append("日主生月令（休）+1")
        if month_attacks:
            drain_votes += 2
            drain_evidence.append(f"月令克日主（{state}）+2")
        if drain_count >= 1:
            drain_votes += 1
            drain_evidence.append(f"食伤财官透干 {drain_count} 处 +1")
        if drain_count >= 2:
            drain_votes += 1
            drain_evidence.append(f"食伤财官透干 ≥2（{drain_count} 处）+1")
        if root_count == 0:
            drain_votes += 1
            drain_evidence.append("日主无根（虚浮）+1")
        if helper_count == 0:
            drain_votes += 1
            drain_evidence.append("无印比透干 +1")

        diff = support_votes - drain_votes
        context = {
            "inCommand": rel.in_command,
            "monthState": state,
            "rootCount": root_count,
            "helperCount": helper_count,
            "drainCount": drain_count,
            "monthAttacks": month_attacks,
            "supportVotes": support_votes,
            "drainVotes": drain_votes,
        }

        verdict: str | None = None
        confidence: str | None = None
        rule_id: str | None = None
        for rid, v, conf in self.RULES:
            if rid == "R21-1":
                hit = rel.in_command and root_count >= 2 and helper_count >= 2
            elif rid == "R21-2":
                hit = (not rel.in_command) and root_count == 0 and helper_count == 0 and month_attacks
            elif rid == "R21-3":
                hit = (not rel.in_command) and root_count == 0 and helper_count == 0
            elif rid == "R21-4":
                hit = rel.in_command and root_count == 0 and helper_count == 0
            elif rid == "R21-5":
                hit = diff >= 3
            elif rid == "R21-6":
                hit = diff <= -3
            elif rid == "R21-7":
                hit = diff >= 1
            elif rid == "R21-8":
                hit = diff <= -1
            else:
                hit = True  # R21-9 兜底
            if hit:
                rule_id, verdict, confidence = rid, v, conf
                break

        reason = [
            f"命中规则 {rule_id}（级联首中即停，规则表见 R21/docs/STRENGTH.md）",
            f"支持票 {support_votes} vs 克泄票 {drain_votes}（差值 {diff:+d}）",
        ]
        conflicts: list[str] = []
        if rel.in_command and root_count == 0 and helper_count == 0:
            conflicts.append("信号冲突：月令得令但日主虚浮无根、无印比——判 UNCERTAIN，不强行下结论")
        if support_votes >= 3 and drain_votes >= 3:
            conflicts.append("信号冲突：帮扶与克泄票数均 ≥3，verdict 置信度受限")
        reason.extend(conflicts)
        note = "规则级联为工程化 heuristic（ADR-023）；UNCERTAIN 表示证据冲突或不足。"
        if conflicts:
            note += "存在信号冲突：" + "；".join(conflicts)

        return StrengthMethodResult(
            analyzer_id=self.analyzer_id,
            name=self.name,
            verdict=verdict,
            confidence=confidence,
            support_evidence=support_evidence,
            drain_evidence=drain_evidence,
            provenance=self._provenance(),
            evidence=reason,
            note=note,
        )
