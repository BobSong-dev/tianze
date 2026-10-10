"""M41 · AI Provider 用户配置系统（后端）——M41-hotfix 安全加固版。

安全边界（单用户本地应用，不引入账户系统）：
- **配置变更/使用操作（set/test/clear）仅允许本机回环客户端**。这是服务端
  检查（scope["client"] 由服务器从 socket 写入，不可经请求头伪造）；
  CORS 不是鉴权，仅是浏览器侧附带约束。公网/局域网部署默认被拒绝，
  须显式设置 TIANZE_ALLOW_REMOTE_AI_CONFIG=1 并自行在反向代理层加鉴权。
- API Key 只保存在**后端进程内存**（单用户本地模式的合理默认），不落盘、
  不进日志、不回显明文（状态接口只返回 masked 尾 4 位）；
- Base URL SSRF 防护：仅允许 http(s)，拒绝 localhost/内网/链路本地地址
  （本地模型例外需显式 allow_local=True，即「本地模型」预设）；
  set 与 test 双重校验（防 set→test 之间配置漂移）。已知残余风险：
  校验与实际请求各自解析 DNS，存在理论 TOCTOU（DNS rebinding）窗口，
  本地单用户模式下接受并在 known-limitations 如实记录。
- 连接测试不跟随重定向（httpx follow_redirects=False），3xx 一律判失败，
  防止经重定向跳转到内网地址。
- 环境变量优先级高于 UI 配置（不破坏现有部署方式）；环境变量 URL 视为
  运维方可信配置，不做 SSRF 校验。
- 并发安全：set/clear/test 在 asyncio.Lock 内原子执行，无半写状态。

提供 OpenAI-compatible 预设（OpenAI/DeepSeek/通义千问/智谱 GLM/本地服务）。
预设仅为便利填充，未经实际验证的提供商不标记“已验证”。
"""

from __future__ import annotations

import asyncio
import ipaddress
import os
import socket
from urllib.parse import urlparse

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
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

_LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
# Starlette TestClient 的进程内哨兵值：由测试传输写入 scope，远程客户端
# 无法通过网络伪造（真实请求的 scope["client"] 是 socket 对端地址）。
_TESTCLIENT_HOST = "testclient"


def is_local_client(host: str | None) -> bool:
    """配置操作的可信判定：仅回环地址（或进程内测试传输）。"""
    if host is None:
        return False
    if host in _LOCAL_HOSTS or host == _TESTCLIENT_HOST:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _remote_forbidden() -> JSONResponse:
    return JSONResponse(status_code=403, content={
        "error": {"code": "AI_CONFIG_LOCAL_ONLY",
                  "message": "AI 配置操作仅允许本机访问（单用户本地模式安全边界）。"
                             "公网/局域网部署须由运维显式设置 TIANZE_ALLOW_REMOTE_AI_CONFIG=1，"
                             "并在反向代理层完成鉴权与身份隔离；CORS 不构成鉴权。",
                  "details": {}}})


def _guard(request: Request) -> JSONResponse | None:
    """写/用操作守卫。显式环境变量视为运维自担风险的豁免。"""
    if os.environ.get("TIANZE_ALLOW_REMOTE_AI_CONFIG") == "1":
        return None
    client = request.client.host if request.client else None
    if is_local_client(client):
        return None
    return _remote_forbidden()


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
_LOCK = asyncio.Lock()


def _resolve_effective() -> dict:
    """环境变量优先；UI 配置次之。"""
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
async def set_config(body: SetConfigBody, request: Request):
    denied = _guard(request)
    if denied:
        return denied
    if not body.apiKey or not body.apiKey.strip():
        return {"ok": False, "error": "API Key 不能为空"}
    if not body.model.strip():
        return {"ok": False, "error": "模型名不能为空"}
    allow_local = any(pr["id"] == body.preset and pr.get("allowLocal")
                      for pr in PRESETS)
    ok, err = _ssrf_check(body.baseUrl, allow_local=allow_local)
    if not ok:
        return {"ok": False, "error": err}
    async with _LOCK:
        _STORE.api_key = body.apiKey.strip()
        _STORE.base_url = body.baseUrl.strip().rstrip("/")
        _STORE.model = body.model.strip()
        _STORE.preset = body.preset
    eff = _resolve_effective()
    # 环境变量在场时 source=env：明确告知"已保存但当前被环境变量覆盖"，
    # 避免保存成功却不生效的误导。
    note = None
    if eff["source"] == "env":
        note = "已保存，但当前检测到 TIANZE_LLM_API_KEY 环境变量——实际调用仍使用环境变量配置。"
    return {"ok": True, **eff, **({"note": note} if note else {})}


@router.post("/test")
async def test_connection(request: Request):
    """真实连接测试：向配置端点发 1-token 请求，返回真实成败与原因。

    幂等只读外部服务，但会携带真实密钥出站，故同样受本机守卫保护；
    不跟随重定向（3xx 判失败）；UI 来源时复验 SSRF。
    """
    denied = _guard(request)
    if denied:
        return denied
    async with _LOCK:
        eff = _resolve_effective()
        if eff["source"] == "ui":
            allow_local = any(pr["id"] == _STORE.preset and pr.get("allowLocal")
                              for pr in PRESETS)
            ok, err = _ssrf_check(_STORE.base_url or "", allow_local=allow_local)
            if not ok:
                return {"ok": False, "error": f"配置的 Base URL 未通过安全校验：{err}"}
        if eff["source"] == "none":
            return {"ok": False, "error": "尚未配置 AI 服务"}
        if eff["source"] == "env":
            key = os.environ["TIANZE_LLM_API_KEY"]
        else:
            key = _STORE.api_key
        base_url, model = eff["baseUrl"], eff["model"]
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            r = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "user", "content": "ping"}],
                      "max_tokens": 1})
        if r.status_code in (301, 302, 303, 307, 308):
            return {"ok": False, "httpStatus": r.status_code,
                    "error": f"端点返回重定向（{r.headers.get('location', '')[:80]}）——已拒绝跟随，"
                             "请直接填写最终端点地址"}
        if r.status_code == 200:
            return {"ok": True, "httpStatus": 200, "provider": base_url}
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
async def clear_config(request: Request):
    denied = _guard(request)
    if denied:
        return denied
    async with _LOCK:
        _STORE.clear()
    return {"ok": True, "note": "UI 配置已清除（环境变量配置不受影响）"}


def get_ui_provider():
    """供 /interpret 使用：返回 UI 配置的 Provider（无则 None）。

    base_url 已在 /set 时通过 SSRF 校验（内存单例仅经 /set 写入）。
    """
    if _STORE.api_key:
        from tianze.ai.interpret import OpenAICompatibleProvider
        return OpenAICompatibleProvider(api_key=_STORE.api_key,
                                        base_url=_STORE.base_url,
                                        model=_STORE.model)
    return None
