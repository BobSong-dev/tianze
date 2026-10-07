"""M17：原文岁运 span 解析测试。"""

from __future__ import annotations

from tools.parse_raw_temporal import cn_to_int, parse_block


def test_cn_to_int():
    assert cn_to_int("三十九") == 39
    assert cn_to_int("十") == 10
    assert cn_to_int("二十") == 20
    assert cn_to_int("七") == 7
    assert cn_to_int("45") == 45


def test_parse_block_gz_spans():
    block = "QBTM-X-1\n四柱：甲午，丙寅，丁酉，丙午。\n大运/流年：辛卯运庚午年事发。\n实际事件：—"
    spans = parse_block(block)
    kinds = {(s["kind"], s["ganZhi"]) for s in spans}
    assert ("luck", "辛卯") in kinds and ("annual", "庚午") in kinds
    for s in spans:
        if s["kind"] != "unresolved":
            assert s["span"] and s["span"][0] < s["span"][1]
            assert s["confidence"] == "high"


def test_parse_block_unresolved_no_guess():
    """描述性内容（无干支）→ UNRESOLVED，不猜天干。"""
    block = "QBTM-X-2\n四柱：甲午，丙寅，丁酉，丙午。\n大运/流年：去酉之运。\n实际事件：—"
    spans = parse_block(block)
    unres = [s for s in spans if s["kind"] == "unresolved"]
    assert unres and "不猜" in unres[0]["unresolvedReason"]
    assert unres[0]["ganZhi"] is None


def test_parse_block_age_association():
    """年龄→同句干支关联（中文数字，confidence=medium）。"""
    block = "QBTM-X-3\n四柱：甲午，丙寅，丁酉，丙午。\n大运/流年：—\n实际事件：三十九岁行壬子运败业。"
    spans = parse_block(block)
    aged = [s for s in spans if s.get("age") == 39]
    assert aged and aged[0]["ganZhi"] == "壬子"
    assert aged[0]["confidence"] == "medium"
