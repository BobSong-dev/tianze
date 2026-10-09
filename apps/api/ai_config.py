"""M41 · AI Provider 用户配置系统（后端）。

安全设计：
- API Key 只保存在**后端进程内存**（单用户本地模式的合理默认），不落盘、
  不进日志、不回显明文（状态接口只返回 masked 尾 4 位）；
- Base URL SSRF 防护：仅允许 http(s)，拒绝 localhost/内网/链路本地地址
  （本地模型例外需显式 allow_local=True）；
- 环境变量优先级高于 UI 配置（不破坏现有部署方式）；
- 公网部署提示：配置为全局单例，匿名用户可改——公网必须加鉴权
  （见接口 docstring）。

提供 OpenAI-compatible 预设（OpenAI/DeepSeek/通义千问/智谱 GLM/本地服务）。
预设仅为便利填充，未经实际验证的提供商不标记“已验证”。
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/ai-config", tags=["ai-config"])

# ---- 预设（OpenAI-compatible；标注是否经过项目实际验证） ----
PRESETS: list[dict] = [
    {"id": "openai", "name": "OpenAI", "baseUrl": "https://api.openai.com/v1",
     "model": "gpt-4o-mini", "verified": False},
    {"id": "deepseek", "name": "DeepSeek", "baseUrl": "https://api.deepseek.com/v1",
     "model": "deepseek-chat", "verified": False},
    {"id": "qwen", "name": "通义千问（DashScope 兼容模式）",
     "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "model": "qwen-plus", "verified": False},
    {"id": "zhipu", "name": "智谱 GLM", "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
     "model": "glm-4-flash", "verified": False},
    {"id": "local", "name": "本地模型（Ollama/LM Studio 等 OpenAI 兼容端点）",
     "baseUrl": "http://127.0.0.1:11434/v1", "model": "qwen2.5:7b",
     "verified": False, "allowLocal": True},
    {"id": "custom", "name": "自定义 OpenAI 兼容服务", "baseUrl": "", "model": "",
     "verified": False},
]


class _Config:
    """进程内单例配置（本地单用户模式；重启即清）。"""

    def __init__(self) -> None:
        self.api_key: str | None = None
        self.base_url: str | None = None
        self.model: str | None = None
        self.preset: str | None = None

    def clear(self) -> None:
        self.api_key = self.base_url = self.model = self.preset = None


_STORE = _Config()


def _resolve_effective() -> dict:
    """环境变量优先；UI 配置次之。"""
    import os
    env_key = os.environ.get("TIANZE_LLM_API_KEY")
    if env_key:
        return {
            "source": "env",
            "baseUrl": os.environ.get("TIANZE_LLM_BASE_URL", "https://api.openai.com/v1"),
            "model": os.environ.get("TIANZE_LLM_MODEL", "gpt-4o-mini"),
            "keyMasked": f"···{env_key[-4:]}" if len(env_key) >= 4 else "···",
        }
    if _STORE.api_key:
        return {
            "source": "ui",
            "baseUrl": _STORE.base_url, "model": _STORE.model,
            "keyMasked": f"···{_STORE.api_key[-4:]}" if len(_STORE.api_key) >= 4 else "···",
            "preset": _STORE.preset,
        }
    return {"source": "none"}


def _ssrf_check(url: str, allow_local: bool = False) -> tuple[bool, str]:
    """Base URL 防护：仅 http(s)；非 allow_local 时拒绝内网/环回/链路本地。"""
    try:
        p = urlparse(url)
    except Exception:
        return False, "URL 无法解析"
    if p.scheme not in ("http", "https") or not p.hostname:
        return False, "仅支持 http(s) URL"
    if allow_local:
        return True, ""
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except Exception:
        return False, "主机名无法解析"
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast):
            return False, f"禁止内网/本地地址（{ip}）；本地模型请选择「本地模型」预设"
    return True, ""


class SetConfigBody(BaseModel):
    apiKey: str
    baseUrl: str
    model: str
    preset: str = "custom"


@router.get("/status")
async def status():
    eff = _resolve_effective()
    return {"configured": eff["source"] != "none", **eff,
            "storage": "进程内存（重启后清除；环境变量配置不受影响）",
            "publicDeployWarning": "公网部署须在反向代理层加鉴权，否则匿名用户可修改全局 AI 配置"}


@router.get("/presets")
async def presets():
    return {"presets": PRESETS}


@router.post("/set")
async def set_config(body: SetConfigBody):
    if not body.apiKey or not body.apiKey.strip():
        return {"ok": False, "error": "API Key 不能为空"}
    if not body.model.strip():
        return {"ok": False, "error": "模型名不能为空"}
    allow_local = any(pr["id"] == body.preset and pr.get("allowLocal")
                      for pr in PRESETS)
    ok, err = _ssrf_check(body.baseUrl, allow_local=allow_local)
    if not ok:
        return {"ok": False, "error": err}
    _STORE.api_key = body.apiKey.strip()
    _STORE.base_url = body.baseUrl.strip().rstrip("/")
    _STORE.model = body.model.strip()
    _STORE.preset = body.preset
    eff = _resolve_effective()
    return {"ok": True, **eff}


@router.post("/test")
async def test_connection():
    """真实连接测试：向配置端点发 1-token 请求，返回真实成败与原因。"""
    eff = _resolve_effective()
    if eff["source"] == "none":
        return {"ok": False, "error": "尚未配置 AI 服务"}
    import os
    if eff["source"] == "env":
        key = os.environ["TIANZE_LLM_API_KEY"]
    else:
        key = _STORE.api_key
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                f"{eff['baseUrl']}/chat/completions",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json={"model": eff["model"],
                      "messages": [{"role": "user", "content": "ping"}],
                      "max_tokens": 1})
        if r.status_code == 200:
            return {"ok": True, "httpStatus": 200,
                    "provider": eff["baseUrl"]}
        detail = ""
        try:
            detail = (r.json().get("error", {}) or {}).get("message", "")[:120]
        except Exception:
            detail = r.text[:120]
        return {"ok": False, "httpStatus": r.status_code,
                "error": f"服务返回 {r.status_code}{('：' + detail) if detail else ''}"}
    except httpx.HTTPError as e:
        return {"ok": False, "error": f"连接失败：{type(e).__name__}：{str(e)[:120]}"}


@router.post("/clear")
async def clear_config():
    _STORE.clear()
    return {"ok": True, "note": "UI 配置已清除（环境变量配置不受影响）"}


def get_ui_provider():
    """供 /interpret 使用：返回 UI 配置的 Provider（无则 None）。"""
    if _STORE.api_key:
        from tianze.ai.interpret import OpenAICompatibleProvider
        return OpenAICompatibleProvider(api_key=_STORE.api_key,
                                        base_url=_STORE.base_url,
                                        model=_STORE.model)
    return None
