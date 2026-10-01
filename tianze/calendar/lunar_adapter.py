"""L1 历法适配层：lunar-python 的薄包装。

排盘事实全部来自 lunar-python；本模块只负责名称归一化（ERRATA-07）、
节气边界警告（R4）与 Solar/Lunar 对象的快捷构造。派盘组装在 pipeline.py。
"""

from __future__ import annotations

import datetime as dt

from lunar_python import Solar

# 节气表 key 的拼音/中文混用归一化（ERRATA-07）
_PINYIN_TO_CN: dict[str, str] = {
    "DA_XUE": "大雪", "DONG_ZHI": "冬至", "XIAO_HAN": "小寒", "DA_HAN": "大寒",
    "LI_CHUN": "立春", "YU_SHUI": "雨水", "JING_ZHE": "惊蛰", "CHUN_FEN": "春分",
    "QING_MING": "清明", "GU_YU": "谷雨", "LI_XIA": "立夏", "XIAO_MAN": "小满",
    "MANG_ZHONG": "芒种", "XIA_ZHI": "夏至", "XIAO_SHU": "小暑", "DA_SHU": "大暑",
    "LI_QIU": "立秋", "CHU_SHU": "处暑", "BAI_LU": "白露", "QIU_FEN": "秋分",
    "HAN_LU": "寒露", "SHUANG_JIANG": "霜降", "LI_DONG": "立冬", "XIAO_XUE": "小雪",
}

# 十二"节"（R4：月柱只认节，不认中气）
JIE_NAMES: frozenset[str] = frozenset(
    {"立春", "惊蛰", "清明", "立夏", "芒种", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"}
)

BOUNDARY_THRESHOLD = dt.timedelta(minutes=30)  # R4：交界 ±30 分钟提示


def to_solar(moment: dt.datetime) -> Solar:
    return Solar.fromYmdHms(moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second)


def solar_to_datetime(solar: Solar) -> dt.datetime:
    return dt.datetime(solar.getYear(), solar.getMonth(), solar.getDay(), solar.getHour(), solar.getMinute(), solar.getSecond())


def normalize_jieqi_name(name: str) -> str:
    return _PINYIN_TO_CN.get(name, name)


def jie_moments(beijing_moment: dt.datetime) -> list[tuple[str, dt.datetime]]:
    """以北京时刻所在农历年的节气表，返回其中全部十二节（名, 北京时刻），按时间排序。"""
    lunar = to_solar(beijing_moment).getLunar()
    out: list[tuple[str, dt.datetime]] = []
    for raw_name, solar in lunar.getJieQiTable().items():
        cn = normalize_jieqi_name(raw_name)
        if cn in JIE_NAMES:
            out.append((cn, solar_to_datetime(solar)))
    out.sort(key=lambda item: item[1])
    return out


def nearest_jie(beijing_moment: dt.datetime) -> tuple[tuple[str, dt.datetime] | None, tuple[str, dt.datetime] | None]:
    """返回（上一个节, 下一个节）。"""
    prev_jie: tuple[str, dt.datetime] | None = None
    next_jie: tuple[str, dt.datetime] | None = None
    for name, moment in jie_moments(beijing_moment):
        if moment <= beijing_moment:
            if prev_jie is None or moment > prev_jie[1]:
                prev_jie = (name, moment)
        elif next_jie is None or moment < next_jie[1]:
            next_jie = (name, moment)
    return prev_jie, next_jie


def boundary_warnings(beijing_moment: dt.datetime, pillar_dt: dt.datetime, time_known: bool, sect: int) -> list[str]:
    warnings: list[str] = []
    prev_jie, next_jie = nearest_jie(beijing_moment)
    for label, item in (("上", prev_jie), ("下", next_jie)):
        if item is None:
            continue
        name, moment = item
        gap = abs(beijing_moment - moment)
        if gap <= BOUNDARY_THRESHOLD:
            kind = "年柱/月柱" if name == "立春" else "月柱"
            warnings.append(
                f"距{label}一个节【{name}】仅 {int(gap.total_seconds() // 60)} 分钟：{kind}临界（R4）"
            )
    if time_known:
        if pillar_dt.hour == 23:
            warnings.append(f"晚子时（23:00-23:59）：日柱归属依赖流派 sect={sect}（R1）")
        elif pillar_dt.hour == 0:
            warnings.append("早子时（00:00-00:59）")
    return warnings
