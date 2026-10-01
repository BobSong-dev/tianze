"""中国夏令时窗口（R12）——公共事实数据，ERRATA-05：逐条核对原文前标 needs-verification。"""

from __future__ import annotations

import datetime as dt

# (年份, (开始月, 日), (结束月, 日))，钟表时刻 02:00 切换；窗口内钟表比标准时快 1 小时。
CN_DST_WINDOWS: tuple[tuple[int, tuple[int, int], tuple[int, int]], ...] = (
    (1986, (5, 4), (9, 14)),
    (1987, (4, 12), (9, 13)),
    (1988, (4, 10), (9, 11)),
    (1989, (4, 16), (9, 17)),
    (1990, (4, 15), (9, 16)),
    (1991, (4, 14), (9, 15)),
)


def cn_dst_shift_hours(local_dt: dt.datetime) -> int:
    """该钟表时刻是否处于中国夏令时窗口内（仅当 tz=+8 时由调用方使用）。"""
    for year, start, end in CN_DST_WINDOWS:
        if local_dt.year != year:
            continue
        begin = dt.datetime(year, start[0], start[1], 2, 0)
        finish = dt.datetime(year, end[0], end[1], 2, 0)
        if begin <= local_dt < finish:
            return 1
    return 0
