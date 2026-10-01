"""排盘管线：BirthInfo → BaziChart（M1/M2 范围：L0-L2 事实 + 关系）。

事实来源：lunar-python（历法/四柱/藏干对账基准/纳音/十二长生/旬空/胎元/大运）
+ Tianze 自有十神推导与关系扫描。分析层（旺衰/格局/调候）在后续里程碑接入。
"""

from __future__ import annotations

from importlib.metadata import version as _pkg_version

import tianze
from tianze.analysis import count_elements, collect_roots, compute_month_command, analyze_visibility
from tianze.calendar import lunar_adapter as LA
from tianze.calendar.time_resolution import resolve_time
from tianze.domain import models as M
from tianze.ganzhi import tables as G
from tianze.relation.relations import analyze_relations

_LUNAR_PYTHON_VERSION = _pkg_version("lunar_python")

_PILLAR_PREFIX = {"year": "Year", "month": "Month", "day": "Day", "hour": "Time"}

_CONVENTIONS = {
    "lateZiSect": "R1",
    "timeAlgorithm": "R2",
    "dualTrack": "R3",
    "jieqiBoundary": "R4",
    "changShengSchool": "R5",
    "startLuck": "R7",
    "hiddenStemTable": "R8",
    "punishmentNaming": "R9",
    "halfCombination": "R10",
    "unknownTime": "R11",
    "timezoneDst": "R12",
    "transformCandidateOnly": "R13",
    "stemOpposition": "R14",
    "rootDepth": "R15",
    "elementStats": "R16",
    "monthCommandStates": "R17",
    "stemVisibility": "R18",
}


def _build_pillar(
    position: M.Position,
    ganzhi: str,
    day_master: str,
    ec,  # lunar_python EightChar（该柱所属轨道）
    with_hour_meta: bool,
) -> M.Pillar:
    stem, branch = ganzhi[0], ganzhi[1]
    prefix = _PILLAR_PREFIX[position]
    hidden = [
        M.HiddenStem(
            stem=s,
            role=M.HiddenStemRole(role),
            element=G.STEM_ELEMENT[s],
            yin_yang=G.stem_yin_yang(s),
            ten_god=G.ten_god(day_master, s),
        )
        for s, role in G.HIDDEN_STEMS[branch]
    ]
    return M.Pillar(
        position=position,
        stem=stem,
        branch=branch,
        stem_element=G.STEM_ELEMENT[stem],
        stem_yin_yang=G.stem_yin_yang(stem),
        branch_element=G.BRANCH_ELEMENT[branch],
        branch_yin_yang=G.branch_yin_yang(branch),
        hidden_stems=hidden,
        ten_god=None if position == "day" else G.ten_god(day_master, stem),
        na_yin=getattr(ec, f"get{prefix}NaYin")(),
        chang_sheng=getattr(ec, f"get{prefix}DiShi")(),
        xun_kong=getattr(ec, f"get{prefix}XunKong")() if with_hour_meta or position != "hour" else None,
    )


def _build_luck(birth: M.BirthInfo, ec_bj) -> tuple[M.LuckInfo | None, list[str]]:
    fallbacks: list[str] = []
    if not birth.time_known:
        fallbacks.append("时辰未知：大运/流年缺席（R11）")
        return None, fallbacks
    if birth.gender in (M.Gender.UNKNOWN, None):
        fallbacks.append("性别未知：大运顺逆不可判定，大运缺席（R7/R11）")
        return None, fallbacks
    gender_code = 1 if birth.gender == M.Gender.MALE else 0
    yun = ec_bj.getYun(gender_code)  # R7：sect=1 折算口径（lunar 默认）
    entries = [
        M.DaYunEntry(
            index=i,
            start_year=d.getStartYear(),
            end_year=d.getEndYear(),
            start_age=d.getStartAge(),
            end_age=d.getEndAge(),
            gan_zhi=d.getGanZhi(),
        )
        for i, d in enumerate(yun.getDaYun(10))
    ]
    luck = M.LuckInfo(
        forward=yun.isForward(),
        start_years=yun.getStartYear(),
        start_months=yun.getStartMonth(),
        start_days=yun.getStartDay(),
        start_hours=yun.getStartHour(),
        da_yun=entries,
    )
    return luck, fallbacks


def build_chart(birth: M.BirthInfo) -> M.BaziChart:
    tr, time_warnings = resolve_time(birth)  # R3/R12

    # 双轨道（R3）：年/月柱走绝对时刻（北京时间），日/时柱走出生地标准时钟
    solar_bj = LA.to_solar(tr.beijing_dt)
    lunar_bj = solar_bj.getLunar()
    ec_bj = lunar_bj.getEightChar()

    solar_loc = LA.to_solar(tr.pillar_dt)
    lunar_loc = solar_loc.getLunar()
    ec_loc = lunar_loc.getEightChar()
    ec_loc.setSect(birth.sect)  # R1

    year_gz = ec_bj.getYear()
    month_gz = ec_bj.getMonth()
    day_gz = ec_loc.getDay()
    hour_gz = ec_loc.getTime() if birth.time_known else None

    day_master = day_gz[0]

    pillar_year = _build_pillar("year", year_gz, day_master, ec_bj, with_hour_meta=False)
    pillar_month = _build_pillar("month", month_gz, day_master, ec_bj, with_hour_meta=False)
    pillar_day = _build_pillar("day", day_gz, day_master, ec_loc, with_hour_meta=False)
    pillar_hour = (
        _build_pillar("hour", hour_gz, day_master, ec_loc, with_hour_meta=True)
        if hour_gz is not None
        else None
    )

    fallbacks: list[str] = []
    special = M.SpecialPoints(
        tai_yuan=ec_loc.getTaiYuan(),  # 胎元只依赖月柱，未知时辰照常输出（R11）
        ming_gong=ec_loc.getMingGong() if birth.time_known else None,
        shen_gong=ec_loc.getShenGong() if birth.time_known else None,
    )
    if not birth.time_known:
        fallbacks.append("时辰未知：命宫/身宫缺席，胎元照常输出（R11）")

    luck, luck_fallbacks = _build_luck(birth, ec_bj)
    fallbacks.extend(luck_fallbacks)

    # 关系（M2）：未知时辰时仅在三柱内扫描
    stems: list[str | None] = [pillar_year.stem, pillar_month.stem, pillar_day.stem,
                               pillar_hour.stem if pillar_hour else None]
    branches: list[str | None] = [pillar_year.branch, pillar_month.branch, pillar_day.branch,
                                  pillar_hour.branch if pillar_hour else None]
    positions: list[M.Position] = ["year", "month", "day", "hour"]
    relations = analyze_relations(stems, branches, positions)

    # 结构事实（M3）：月令 / 通根 / 透干 / 五行统计（不加权，R15-R18）
    month_command = compute_month_command(month_gz[1], day_master, stems)
    roots = collect_roots(stems, branches, positions, day_master)
    visibility = analyze_visibility(stems, branches, positions, day_master)
    element_counts = count_elements(stems, branches)

    warnings = list(time_warnings)
    warnings.extend(
        LA.boundary_warnings(tr.beijing_dt, tr.pillar_dt, birth.time_known, birth.sect)
    )

    lunar_month = lunar_loc.getMonth()
    return M.BaziChart(
        birth=birth,
        time=tr,
        lunar_date=M.LunarDateInfo(
            year=lunar_loc.getYear(),
            month_cn=lunar_loc.getMonthInChinese(),
            day_cn=lunar_loc.getDayInChinese(),
            is_leap_month=lunar_month < 0,
        ),
        pillars=M.Pillars(year=pillar_year, month=pillar_month, day=pillar_day, hour=pillar_hour),
        day_master=M.DayMasterInfo(
            stem=day_master,
            element=G.STEM_ELEMENT[day_master],
            yin_yang=G.stem_yin_yang(day_master),
        ),
        special_points=special,
        luck=luck,
        relations=relations,
        roots=roots,
        visibility=visibility,
        month_command=month_command,
        element_counts=element_counts,
        conventions=_CONVENTIONS,
        meta=M.ChartMeta(
            engine_version=tianze.__version__,
            engine_stage=tianze.ENGINE_STAGE,
            lunar_python_version=_LUNAR_PYTHON_VERSION,
            warnings=warnings,
            fallbacks=fallbacks,
        ),
    )
