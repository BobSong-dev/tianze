"""M20 · Tianze CLI（复用 SDK，不复制业务逻辑）。

命令：
    tianze analyze  --date D --time T --gender G [--sect N] [--tz X]
                    [--year Y] [--month M] [--day D] [--event-themes]
                    [--explanations] [--format json|md|html] [--out FILE]
    tianze timeline --date D --time T --gender G [--luck-index N] [--year Y]
                    [--month M] [--format json]
    tianze export   --date D --time T --gender G --format md|html --out FILE
    tianze validate                  （知识库校验；开发模式）
    tianze version

错误：TianzeError → stderr `code: message`，退出码 1；用法错误退出码 2。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys


def _birth_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--date", required=True, help="出生日期 YYYY-MM-DD")
    p.add_argument("--time", default=None, help="出生时间 HH:MM（缺省=未知时辰）")
    p.add_argument("--gender", choices=["male", "female"], default=None)
    p.add_argument("--sect", type=int, default=2, choices=[1, 2], help="晚子时流派（R1）")
    p.add_argument("--tz", type=float, default=8.0, help="标准时区偏移（东八=8）")
    p.add_argument("--longitude", type=float, default=None)


def _temporal_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--luck-index", type=int, default=None)
    p.add_argument("--year", type=int, default=None, help="流年")
    p.add_argument("--month", type=int, default=None, help="流月序（1=寅月）")
    p.add_argument("--day", default=None, help="流日 YYYY-MM-DD")


def _build_birth(a) -> dict:
    return {
        "date": a.date, "time": a.time, "gender": a.gender,
        "timezoneOffset": a.tz, "sect": a.sect,
        "longitude": a.longitude,
    }


def _emit(payload: dict, fmt: str, out: str | None) -> int:
    if fmt == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=1)
    elif fmt == "html":
        from tianze.export_html import to_html
        text = to_html(payload)
    else:
        from tianze.export import to_markdown
        text = to_markdown(payload)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"已写出 {out}")
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
    return 0


def cmd_analyze(a) -> int:
    from tianze import AnalysisOptions, analyze
    options = AnalysisOptions(
        include_temporal=bool(a.year or a.luck_index is not None or a.month or a.day),
        target_luck_index=a.luck_index, target_year=a.year,
        target_month=a.month, target_day=a.day,
        include_event_themes=a.event_themes,
        include_temporal_delta=a.event_themes or a.explanations,
        include_explanations=a.explanations,
    )
    result = analyze(_build_birth(a), options)
    payload = result.model_dump()
    if a.format in ("md", "html"):
        payload["temporal"] = result.temporal and json.loads(
            json.dumps(result.temporal, ensure_ascii=False))
    return _emit(payload, a.format, a.out)


def cmd_timeline(a) -> int:
    from tianze import AnalysisOptions, analyze
    options = AnalysisOptions(
        include_temporal=True, target_luck_index=a.luck_index, target_year=a.year,
        target_month=a.month, target_day=a.day,
        include_event_themes=a.event_themes,
        include_temporal_delta=True, include_explanations=a.explanations,
    )
    result = analyze(_build_birth(a), options)
    return _emit(result.model_dump(), a.format, a.out)


def cmd_export(a) -> int:
    from tianze import analyze
    result = analyze(_build_birth(a))
    return _emit(result.model_dump(), a.format, a.out)


def cmd_validate(_a) -> int:
    """知识库校验（开发模式：数据在 repo knowledge/；安装模式提示）。"""
    from tianze.paths import data_root
    root = str(data_root())
    if "_data" in root.replace("\\", "/"):
        print("安装模式：数据为构建副本（manifest 自检通过即一致）；"
              "完整校验请在仓库运行 `python -m pytest tests -k validator` 或 tianze validate（开发模式）")
        return 0
    r = subprocess_run_validate()
    return r


def subprocess_run_validate() -> int:
    from tianze.paths import repo_root
    script = os.path.join(repo_root(), "tools", "validate_knowledge.py")
    if not os.path.exists(script):
        print("开发工具不在当前安装中（repo-only）")
        return 0
    import subprocess
    return subprocess.run([sys.executable, script], cwd=str(repo_root())).returncode


def cmd_version(_a) -> int:
    import tianze
    from tianze.knowledge.models import KNOWLEDGE_SCHEMA_VERSION
    from tianze.ai.models import INTERPRETATION_SCHEMA_VERSION, PROMPT_VERSION
    from tianze.analysis.temporal_delta import DELTA_SCHEMA_VERSION
    from tianze.analysis.event_themes import EVENT_THEME_SCHEMA_VERSION
    print(json.dumps({
        "engine": tianze.__version__,
        "knowledge": KNOWLEDGE_SCHEMA_VERSION,
        "delta": DELTA_SCHEMA_VERSION,
        "event": EVENT_THEME_SCHEMA_VERSION,
        "interpretation": INTERPRETATION_SCHEMA_VERSION,
        "prompt": PROMPT_VERSION,
    }, ensure_ascii=False, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tianze",
                                description="Tianze 天泽 —— 可解释八字结构分析引擎")
    sub = p.add_subparsers(dest="command", required=True)

    pa = sub.add_parser("analyze", help="原局分析（可附岁运/事件主题）")
    _birth_args(pa); _temporal_args(pa)
    pa.add_argument("--event-themes", action="store_true")
    pa.add_argument("--explanations", action="store_true")
    pa.add_argument("--format", choices=["json", "md", "html"], default="json")
    pa.add_argument("--out", default=None)
    pa.set_defaults(func=cmd_analyze)

    pt = sub.add_parser("timeline", help="聚焦岁运分析（大运→年→月→日）")
    _birth_args(pt); _temporal_args(pt)
    pt.add_argument("--event-themes", action="store_true")
    pt.add_argument("--explanations", action="store_true")
    pt.add_argument("--format", choices=["json", "md", "html"], default="json")
    pt.add_argument("--out", default=None)
    pt.set_defaults(func=cmd_timeline)

    pe = sub.add_parser("export", help="导出 Markdown/HTML 报告")
    _birth_args(pe)
    pe.add_argument("--format", choices=["md", "html"], default="md")
    pe.add_argument("--out", required=True)
    pe.set_defaults(func=cmd_export)

    pv = sub.add_parser("validate", help="知识库校验（开发模式）")
    pv.set_defaults(func=cmd_validate)

    pver = sub.add_parser("version", help="版本信息")
    pver.set_defaults(func=cmd_version)

    a = p.parse_args(argv)
    try:
        return a.func(a)
    except Exception as exc:
        code = getattr(exc, "code", None)
        if code:  # TianzeError
            print(f"{code}: {exc}", file=sys.stderr)
            return 1
        print(f"INTERNAL_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
