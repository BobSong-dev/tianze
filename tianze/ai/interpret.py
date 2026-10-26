"""M11.3 · Provider abstraction + Grounding Validator + interpret() 入口。"""

from __future__ import annotations

import abc
import json
import os
from typing import Any

from tianze.ai.models import (
    InterpretationSection,
    GroundingIssue,
    GroundingIssueType,
    InterpretationContext,
    InterpretationMetadata,
    InterpretationResult,
    INTERPRETATION_SCHEMA_VERSION,
    PROMPT_VERSION,
)
from tianze.ai.prompt_builder import build_prompts


class InterpretationProvider(abc.ABC):
    """LLM Provider 统一接口。"""

    @abc.abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
        """返回 (raw_text, usage_metadata)。"""
        ...

    @property
    @abc.abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abc.abstractmethod
    def model_name(self) -> str: ...


class MockInterpretationProvider(InterpretationProvider):
    """测试用 Mock：返回固定结构化解释。"""

    async def complete(self, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
        result = json.dumps({
            "summary": "此命局结构分析基于 Tianze 引擎确定性结果。",
            "sections": [
                {"type": "strength", "title": "旺衰分析", "content": "多方法并列分析。",
                 "evidenceIds": [], "sourceIds": []},
            ],
            "disagreements": [],
            "uncertainties": [],
            "sourceReferences": [],
        }, ensure_ascii=False)
        return result, {"prompt_tokens": len(system_prompt + user_prompt) // 4, "completion_tokens": 50}

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-v1"


class OpenAICompatibleProvider(InterpretationProvider):
    """OpenAI-compatible ChatCompletion API（也兼容大多数国产模型 API）。"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
        """带 latency/token/网络重试遥测（usage dict；不含任何请求体/密钥）。"""
        import time

        import httpx
        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_prompt}],
            "temperature": 0.3,
        }
        started = time.perf_counter()
        retries = 0
        error_category = None
        data = None
        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(3):   # 最多 3 次（网络/5xx 指数退避）
                try:
                    r = await client.post(url, json=payload, headers=headers)
                    if r.status_code >= 500 and attempt < 2:
                        retries += 1
                        error_category = "http_5xx"
                        await __import__("asyncio").sleep(0.5 * (attempt + 1))
                        continue
                    r.raise_for_status()
                    data = r.json()
                    error_category = None
                    break
                except httpx.TransportError:
                    retries += 1
                    error_category = "network"
                    if attempt == 2:
                        raise
                    await __import__("asyncio").sleep(0.5 * (attempt + 1))
        latency_ms = int((time.perf_counter() - started) * 1000)
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "latency_ms": latency_ms,
            "retries": retries,
            "error_category": error_category or "none",
        }

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def model_name(self) -> str:
        return self.model


class AnthropicMessagesProvider(InterpretationProvider):
    """Anthropic Messages API（/v1/messages；兼容官方及第三方 Anthropic 兼容端点）。

    鉴权同时携带 x-api-key 与 Authorization Bearer（官方两者皆收，
    第三方兼容层通常至少实现其一）；anthropic-version 采用兼容面最广的
    2023-06-01。响应 content[].text 拼接为输出文本。
    """

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
        import time

        import httpx
        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": 0.3,
        }
        started = time.perf_counter()
        retries = 0
        error_category = None
        data = None
        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(3):
                try:
                    r = await client.post(url, json=payload, headers=headers)
                    if r.status_code >= 500 and attempt < 2:
                        retries += 1
                        error_category = "http_5xx"
                        await __import__("asyncio").sleep(0.5 * (attempt + 1))
                        continue
                    r.raise_for_status()
                    data = r.json()
                    error_category = None
                    break
                except httpx.TransportError:
                    retries += 1
                    error_category = "network"
                    if attempt == 2:
                        raise
                    await __import__("asyncio").sleep(0.5 * (attempt + 1))
        latency_ms = int((time.perf_counter() - started) * 1000)
        text = "".join(block.get("text", "") for block in data.get("content", [])
                       if block.get("type") == "text")
        usage = data.get("usage", {})
        return text, {
            "prompt_tokens": usage.get("input_tokens"),
            "completion_tokens": usage.get("output_tokens"),
            "total_tokens": (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0) or None,
            "latency_ms": latency_ms,
            "retries": retries,
            "error_category": error_category or "none",
        }

    @property
    def provider_name(self) -> str:
        return "anthropic_compatible"

    @property
    def model_name(self) -> str:
        return self.model


def create_provider_from_env() -> InterpretationProvider | None:
    api_key = os.environ.get("TIANZE_LLM_API_KEY")
    if not api_key:
        return None
    base_url = os.environ.get("TIANZE_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("TIANZE_LLM_MODEL", "chat-latest")
    protocol = os.environ.get("TIANZE_LLM_PROTOCOL", "openai").strip().lower()
    if protocol == "anthropic":
        return AnthropicMessagesProvider(api_key=api_key, base_url=base_url, model=model)
    return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)


# ---- Grounding Validator ----

def _sev(t: GroundingIssueType) -> GroundingSeverity:
    FATAL = {GroundingIssueType.FABRICATED_CLASSICAL_SOURCE,
             GroundingIssueType.UNRESOLVED_ASSERTED,
             GroundingIssueType.VERIFICATION_MISREPRESENTATION,
             GroundingIssueType.UNSUPPORTED_PATTERN}
    return GroundingSeverity.FATAL if t in FATAL else GroundingSeverity.ERROR

def validate_grounding(
    result: InterpretationResult,
    ctx: InterpretationContext,
) -> list[GroundingIssue]:
    """程序化检查 AI 输出是否有不存在的 ID / 越界判断 / 伪造来源。"""
    issues: list[GroundingIssue] = []
    valid_fact_keys = {f.key for f in ctx.chart_facts + ctx.relations + ctx.structure}
    valid_source_ids = {s.source_id for s in ctx.sources}

    # Check evidenceIds / sourceIds
    for section in result.sections:
        for eid in section.evidence_ids:
            if eid not in valid_fact_keys:
                issues.append(GroundingIssue(
                    type=GroundingIssueType.UNKNOWN_EVIDENCE_ID,
                    detail=f"Section '{section.title}' 引用不存在的 evidenceId '{eid}'",
                    claimed=eid,
                ))
        for sid in section.source_ids:
            if sid not in valid_source_ids:
                issues.append(GroundingIssue(
                    type=GroundingIssueType.UNKNOWN_SOURCE_ID,
                    detail=f"Section '{section.title}' 引用不存在的 sourceId '{sid}'",
                    claimed=sid,
                ))
    for sid in result.source_references:
        if sid not in valid_source_ids:
            issues.append(GroundingIssue(
                type=GroundingIssueType.UNKNOWN_SOURCE_ID,
                detail=f"sourceReferences 引用不存在的 sourceId '{sid}'",
                claimed=sid,
            ))

    # Check pattern names
    valid_patterns = {c.get("name", "") for c in ctx.pattern_candidates}
    for section in result.sections:
        if section.type == "pattern":
            for p in valid_patterns:
                if p and p in section.content:
                    break
            else:
                if valid_patterns and ("格" in section.content):
                    # 正文提到某格，但不是 Tianze 的候选
                    import re
                    mentioned = set(re.findall(r"([\u4e00-\u9fff]{1,3}格)", section.content))
                    invalid = mentioned - valid_patterns - {"格局"}
                    if invalid:
                        issues.append(GroundingIssue(
                            type=GroundingIssueType.UNSUPPORTED_PATTERN,
                            detail=f"Section '{section.title}' 提及不在候选中的格局: {invalid}",
                            claimed=",".join(invalid),
                            actual=",".join(valid_patterns),
                        ))

    # Check fabricated classical sources
    for section in result.sections:
        import re
        books_mentioned = set(re.findall(r"《(.+?)》", section.content))
        valid_books = {s.book for s in ctx.sources}
        for book in books_mentioned:
            if book not in valid_books:
                issues.append(GroundingIssue(
                    type=GroundingIssueType.FABRICATED_CLASSICAL_SOURCE,
                    detail=f"Section '{section.title}' 引用了 Context 中不存在的古籍《{book}》",
                    claimed=book,
                ))

    # Check verification misrepresentation
    for section in result.sections:
        for phrase in ("专家核验", "已验证无误", "权威认证", "人工核验"):
            if phrase in section.content:
                # Check if any source is actually HUMAN_VERIFIED
                has_human = any(s.verification_status.startswith("HUMAN") for s in ctx.sources)
                if not has_human:
                    issues.append(GroundingIssue(
                        type=GroundingIssueType.VERIFICATION_MISREPRESENTATION,
                        detail=f"Section '{section.title}' 包含 '{phrase}' 但 Context 中无 HUMAN_VERIFIED 来源",
                        claimed=phrase,
                    ))

    # Check temporal sections for life-event predictions (M13)
    _TEMPORAL_BANNED = ("一定", "必然", "必定", "肯定会", "必将", "注定",
                        "发财", "升职", "结婚", "离婚", "大病", "横祸", "有灾")
    for section in result.sections:
        if section.type == "temporal":
            hits = [w for w in _TEMPORAL_BANNED if w in section.content]
            if hits:
                issues.append(GroundingIssue(
                    type=GroundingIssueType.TEMPORAL_PREDICTION,
                    detail=f"Section '{section.title}' 含具体事件预测语言: {hits}（岁运只允许结构描述）",
                    claimed=",".join(hits),
                ))

    # Check event theme sections for life-event assertions (M14)
    _EVENT_BANNED = ("一定会", "必然会", "必定会", "肯定会", "必将", "注定",
                     "会发财", "会升职", "会结婚", "会离婚", "会生病", "有灾",
                     "发财", "升职", "结婚", "离婚", "婚期", "横祸", "暴富",
                     "% 的概率", "％的概率", "概率为")
    for section in result.sections:
        if section.type == "event_themes":
            hits = [w for w in _EVENT_BANNED if w in section.content]
            if hits:
                issues.append(GroundingIssue(
                    type=GroundingIssueType.EVENT_PREDICTION,
                    detail=f"Section '{section.title}' 含事件断言/伪概率语言: {hits}"
                           "（Event Theme 只允许结构描述与状态词汇）",
                    claimed=",".join(hits),
                ))

    # Check UNRESOLVED asserted as definitive
    for section in result.sections:
        for u in ctx.unresolved:
            keyword = u.split()[0] if u.split() else u[:4]
            if keyword in section.content and any(
                phrase in section.content for phrase in ("确定为", "就是", "必定是")
            ):
                issues.append(GroundingIssue(
                    type=GroundingIssueType.UNRESOLVED_ASSERTED,
                    detail=f"Section '{section.title}' 将 UNRESOLVED 项 '{keyword}' 描述为确定性结论",
                    claimed=keyword,
                ))

    return issues


# ---- interpret() 入口 ----

async def interpret(
    ctx: InterpretationContext,
    provider: InterpretationProvider,
    engine_version: str = "",
    knowledge_version: str = "",
    analysis_schema_version: str = "",
) -> tuple[InterpretationResult, InterpretationMetadata]:
    """运行 AI 解释 + Grounding 校验。失败时 retry 一次。"""
    system_prompt, user_prompt = build_prompts(ctx)
    raw, usage = await provider.complete(system_prompt, user_prompt)

    # Parse structured output
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Try stripping markdown code fence
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(f"Provider returned non-JSON output: {raw[:200]}") from None

    result = InterpretationResult(
        summary=parsed.get("summary", ""),
        sections=[s for s in (InterpretationSection.model_validate(sec) for sec in parsed.get("sections", []))],
        disagreements=parsed.get("disagreements", []),
        uncertainties=parsed.get("uncertainties", []),
        source_references=parsed.get("sourceReferences", []),
    )

    # Grounding validation
    issues = validate_grounding(result, ctx)
    result.grounding_issues = issues
    result.grounding_passed = len(issues) == 0

    metadata = InterpretationMetadata(
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=PROMPT_VERSION,
        interpretation_schema_version=INTERPRETATION_SCHEMA_VERSION,
        engine_version=engine_version,
        knowledge_schema_version=knowledge_version,
        analysis_schema_version=analysis_schema_version,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
        latency_ms=usage.get("latency_ms"),
        retry_count=usage.get("retries", 0),
        error_category=usage.get("error_category", "none"),
    )
    return result, metadata
