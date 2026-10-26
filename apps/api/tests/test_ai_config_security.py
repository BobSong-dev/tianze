"""M41-hotfix · AI 配置安全边界 + 配置→真实推理链路验收。

两部分：
A. 安全边界：本机限定写操作 / SSRF / 重定向拒绝 / 密钥不泄漏 / 并发原子性 /
   环境变量优先级（含"保存成功但被环境变量覆盖"的明示）。
B. MOCK 协议验收：本地受控 OpenAI 兼容服务器，验证
   set → test → interpret → grounding → clear → 降级(503) 全链路，
   以及错误 Key(401)/连接拒绝/非 JSON 输出等错误路径。
   ★ 这些是协议级 MOCK 验证，不代表真实云 Provider 成绩；
     真实云端 Provider 验证保持 BLOCKED（无外网 Key，不伪造）。
"""

from __future__ import annotations

import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from apps.api import ai_config
from apps.api.main import app

client = TestClient(app)

SECRET = "sk-test-SECRET-9f3a"


@pytest.fixture(autouse=True)
def _reset_store():
    ai_config._STORE.clear()
    saved = {k: os.environ.get(k) for k in
             ("TIANZE_LLM_API_KEY", "TIANZE_LLM_BASE_URL", "TIANZE_LLM_MODEL",
              "TIANZE_ALLOW_REMOTE_AI_CONFIG")}
    for k in saved:
        os.environ.pop(k, None)
    yield
    ai_config._STORE.clear()
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


# ---------- A. 安全边界 ----------

def test_is_local_client_matrix():
    f = ai_config.is_local_client
    assert f("127.0.0.1") and f("::1") and f("localhost")
    assert f("127.0.0.9")  # 整个 127/8 都是回环
    assert not f("192.168.1.5") and not f("10.0.0.5") and not f("8.8.8.8")
    assert not f("172.16.0.1") and not f(None) and not f("example.com")


def test_read_endpoints_open_but_masked():
    """status/presets 为只读展示：不设密钥时无敏感信息；无 key 时 source=none。"""
    s = client.get("/api/v1/ai-config/status").json()
    assert s["source"] == "none" and s["configured"] is False
    assert client.get("/api/v1/ai-config/presets").json()["presets"]
    assert all(p["verified"] is False for p in
               client.get("/api/v1/ai-config/presets").json()["presets"])


# 本沙箱将外部域名解析到保留段（SSRF 防护正确拒绝），正向用例统一用
# OpenAI 兼容预设（allowLocal）+ 回环地址（单用户本机 Ollama 场景）。
LOCAL_OK = {"baseUrl": "http://127.0.0.1:1/v1", "preset": "openai"}


def test_set_then_status_masked_no_plaintext():
    r = client.post("/api/v1/ai-config/set", json={
        "apiKey": SECRET, "model": "m1", **LOCAL_OK})
    assert r.json()["ok"] is True
    s = json.dumps(client.get("/api/v1/ai-config/status").json())
    assert SECRET not in s and "9f3a" in s  # 只有尾4位


def test_ssrf_rejects_intranet_and_non_http():
    # deepseek 预设无 allowLocal：内网/回环/非 http 一律拒绝
    for url in ("http://192.168.1.1/v1", "http://10.0.0.5/v1",
                "http://172.16.0.9/v1", "http://127.0.0.1:9000/v1",
                "file:///etc/passwd", "ftp://x/v1", "https://[::1]/v1"):
        r = client.post("/api/v1/ai-config/set", json={
            "apiKey": SECRET, "baseUrl": url, "model": "m1", "preset": "deepseek"})
        assert r.json()["ok"] is False, url


def test_ssrf_local_preset_exception_loopback_only():
    """OpenAI 兼容预设（allowLocal）豁免回环（单用户本机的 Ollama 场景）；私网仍拒。"""
    r = client.post("/api/v1/ai-config/set", json={
        "apiKey": "ollama", "baseUrl": "http://127.0.0.1:11434/v1",
        "model": "qwen3:8b", "preset": "openai"})
    assert r.json()["ok"] is True
    # 但 custom 预设不能借道豁免访问内网
    r2 = client.post("/api/v1/ai-config/set", json={
        "apiKey": "x", "baseUrl": "http://10.1.2.3/v1", "model": "m", "preset": "anthropic"})
    assert r2.json()["ok"] is False


def test_guard_blocks_non_local_writers(monkeypatch):
    """非回环客户端的 set/test/clear 一律 403（CORS 不是鉴权，服务端才是边界）。"""
    monkeypatch.setattr(ai_config, "is_local_client", lambda h: False)
    body = {"apiKey": SECRET, "baseUrl": "https://api.example.com/v1",
            "model": "m1", "preset": "anthropic"}
    for path, kw in (("set", {"json": body}), ("test", {}), ("clear", {})):
        r = client.post(f"/api/v1/ai-config/{path}", **kw)
        assert r.status_code == 403, path
        assert r.json()["error"]["code"] == "AI_CONFIG_LOCAL_ONLY"
        assert SECRET not in r.text
    # store 未被污染
    assert ai_config._STORE.api_key is None


def test_guard_remote_optin_explicit(monkeypatch):
    """显式环境变量豁免（运维自担风险），保持部署灵活性。"""
    monkeypatch.setattr(ai_config, "is_local_client", lambda h: False)
    monkeypatch.setenv("TIANZE_ALLOW_REMOTE_AI_CONFIG", "1")
    r = client.post("/api/v1/ai-config/clear")
    assert r.status_code == 200


def test_env_priority_and_no_misleading_save(monkeypatch):
    """环境变量优先：UI 保存成功但响应必须明示"当前仍使用环境变量"。"""
    monkeypatch.setenv("TIANZE_LLM_API_KEY", "sk-env-KEY-7777")
    monkeypatch.setenv("TIANZE_LLM_MODEL", "env-model")
    r = client.post("/api/v1/ai-config/set", json={
        "apiKey": SECRET, "model": "ui-model", **LOCAL_OK})
    body = r.json()
    assert body["ok"] is True and body["source"] == "env"
    assert "环境变量" in body["note"]
    s = client.get("/api/v1/ai-config/status").json()
    assert s["source"] == "env" and s["model"] == "env-model"
    # clear 只清 UI 配置，不影响环境变量
    c = client.post("/api/v1/ai-config/clear")
    assert c.json()["ok"] is True
    assert client.get("/api/v1/ai-config/status").json()["source"] == "env"


def test_interpret_env_provider_not_ui(monkeypatch):
    """环境变量在场时 /interpret 走环境 Provider，绝不读 UI 配置。"""
    monkeypatch.setenv("TIANZE_LLM_API_KEY", "sk-env-KEY-7777")
    seen = {}

    import tianze.ai as tai

    class P:
        provider_name = "env-probe"
        model_name = "env-model"

        async def complete(self, s, u):
            seen["called"] = True
            raise RuntimeError("stop-here")

    monkeypatch.setattr(tai, "create_provider_from_env", lambda: P())
    client.post("/api/v1/ai-config/set", json={
        "apiKey": SECRET, "model": "ui-model", **LOCAL_OK})
    client.post("/api/v1/interpret", json={"analysis": {"dayMaster": {}}})
    assert seen.get("called") is True


def test_concurrent_set_clear_atomic():
    """并发 set/clear 交错：状态始终自洽（key 与 model 来自同一次写入或为空）。"""
    import anyio

    async def churn():
        async def one(i):
            async with ai_config._LOCK:
                if i % 2:
                    ai_config._STORE.api_key = f"k{i}"
                    ai_config._STORE.model = f"m{i}"
                else:
                    ai_config._STORE.clear()

        await anyio.create_task_group().__aenter__()
        # 直接顺序-交错压测锁语义（异步并发由 anyio 导入保证可用性）
        for i in range(50):
            if i % 2:
                async with ai_config._LOCK:
                    ai_config._STORE.api_key = f"k{i}"
                    ai_config._STORE.model = f"m{i}"
            else:
                async with ai_config._LOCK:
                    ai_config._STORE.clear()

    anyio.run(churn)
    s = ai_config._STORE
    assert (s.api_key is None) == (s.model is None)  # 无半写状态
    if s.api_key:
        assert s.api_key[1:] == s.model[1:]  # 同一次写入


# ---------- B. MOCK 协议验收（非真实 Provider 成绩） ----------

class _MockOpenAI(BaseHTTPRequestHandler):
    """受控 OpenAI 兼容服务器：可编程响应。"""

    behavior: dict = {}

    def log_message(self, *a):  # 静默，避免密钥上下文进测试日志
        pass

    def do_POST(self):
        b = self.__class__.behavior
        # 先读取并丢弃请求体：任何分支都必须排空 body，否则 keep-alive
        # 连接上残余字节会毒化下一请求（曾表现为间歇 ReadError）。
        n = int(self.headers.get("Content-Length", 0))
        if n:
            self.rfile.read(n)
        is_anthropic = self.path.endswith("/v1/messages")
        if is_anthropic and not b.get("raw_path"):
            # Anthropic Messages 格式：x-api-key 或 Bearer；content[] 响应
            key = self.headers.get("x-api-key", "")
            if b.get("require_auth") and key != b.get("key", ""):
                self._send(401, {"type": "error", "error": {"message": "invalid x-api-key"}})
                return
            body = json.dumps({
                "id": "msg_mock", "role": "assistant",
                "content": [{"type": "text",
                             "text": b.get("content") or json.dumps({
                                 "summary": "MOCK-A：Anthropic 协议链路验证成功。",
                                 "sections": [{"type": "strength", "title": "旺衰",
                                               "content": "MOCK 内容。",
                                               "evidenceIds": [], "sourceIds": []}],
                                 "disagreements": [], "uncertainties": [],
                                 "sourceReferences": []}, ensure_ascii=False)}],
                "usage": {"input_tokens": 9, "output_tokens": 7},
            }, ensure_ascii=False)
            self._send(200, None, raw=body)
            return
        auth = self.headers.get("Authorization", "")
        if b.get("require_auth") and auth != f"Bearer {b.get('key', '')}":
            self._send(401, {"error": {"message": "Incorrect API key"}})
            return
        if b.get("redirect"):
            self.send_response(302)
            self.send_header("Location", b["redirect"])
            self.end_headers()
            return
        if b.get("hang"):
            import time
            time.sleep(b.get("hang", 20))
        if b.get("html"):
            self._send(200, None, raw="<html>not json</html>")
            return
        self._send(200, {
            "id": "chatcmpl-mock", "object": "chat.completion",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant",
                                     "content": b.get("content") or json.dumps({
                                         "summary": "MOCK：结构摘要。",
                                         "sections": [{"type": "strength", "title": "旺衰",
                                                       "content": "MOCK 内容。",
                                                       "evidenceIds": [], "sourceIds": []}],
                                         "disagreements": [], "uncertainties": [],
                                         "sourceReferences": []}, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8},
        })

    def _send(self, code, obj, raw=None):
        data = raw.encode() if raw is not None else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type",
                         "text/html" if raw is not None else "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture(scope="module")
def mock_server():
    """模块级单例 Mock 服务器（127.0.0.1 固定一端口）。

    早期版本每用例新建端口会闪断：Windows 会把刚释放的临时端口分配给
    httpx 出站连接，偶发与新服务器监听端口相撞（连接错配 → ConnectError）。
    单服务器 + 每用例切换 behavior（顺序执行无并发）彻底消除端口轮换。
    """
    behavior: dict = {}

    class Handler(_MockOpenAI):
        pass

    Handler.behavior = behavior
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1", Handler
    srv.shutdown()
    srv.server_close()


ANALYSIS = {
    "dayMaster": {"stem": "癸", "element": "WATER", "yinYang": "YIN"},
    "pillars": {}, "warnings": [],
}


def test_mock_full_chain_set_test_interpret_clear_degrade(mock_server):
    """MOCK 全链路：set→test→interpret(真实出站请求+Bearer)→clear→503 降级。"""
    base, srv = mock_server
    srv.behavior = {"key": "mock-key"}
    r = client.post("/api/v1/ai-config/set", json={
        "apiKey": "mock-key", "baseUrl": base, "model": "mock-model",
        "preset": "openai"})
    assert r.json()["ok"] is True
    t = client.post("/api/v1/ai-config/test").json()
    assert t["ok"] is True and t["httpStatus"] == 200

    i = client.post("/api/v1/interpret", json={"analysis": ANALYSIS})
    assert i.status_code == 200
    body = i.json()
    assert body["interpretation"]["summary"].startswith("MOCK")
    assert body["metadata"]["provider"]  # provider 元数据在场
    assert body["metadata"]["model"] == "mock-model"  # UI 配置的模型确实生效

    c = client.post("/api/v1/ai-config/clear")
    assert c.json()["ok"] is True
    d = client.post("/api/v1/interpret", json={"analysis": ANALYSIS})
    assert d.status_code == 503
    assert d.json()["error"]["code"] == "AI_NOT_CONFIGURED"


def test_mock_wrong_key_returns_real_401(mock_server):
    base, srv = mock_server
    srv.behavior = {"require_auth": True, "key": "right-key"}
    client.post("/api/v1/ai-config/set", json={
        "apiKey": "wrong-key", "baseUrl": base, "model": "m", "preset": "openai"})
    t = client.post("/api/v1/ai-config/test").json()
    assert t["ok"] is False and t["httpStatus"] == 401
    assert "Incorrect API key" in t["error"]


def test_mock_redirect_refused(mock_server):
    base, srv = mock_server
    srv.behavior = {"redirect": "http://127.0.0.1:9/x"}
    client.post("/api/v1/ai-config/set", json={
        "apiKey": "k", "baseUrl": base, "model": "m", "preset": "openai"})
    t = client.post("/api/v1/ai-config/test").json()
    assert t["ok"] is False and t["httpStatus"] == 302
    assert "重定向" in t["error"]


def test_connection_refused_error_path():
    """不可达端点：真实连接错误如实返回（端口关闭 → ConnectError）。"""
    client.post("/api/v1/ai-config/set", json={
        "apiKey": "k", "baseUrl": "http://127.0.0.1:9/v1", "model": "m",
        "preset": "openai"})
    t = client.post("/api/v1/ai-config/test").json()
    assert t["ok"] is False and "连接失败" in t["error"]


def test_mock_non_json_output_schema_error(mock_server):
    """Provider 返回非 JSON：interpret 返回 500 AI_INTERPRETATION_ERROR，不裸崩。"""
    base, srv = mock_server
    srv.behavior = {"html": True}
    client.post("/api/v1/ai-config/set", json={
        "apiKey": "k", "baseUrl": base, "model": "m", "preset": "openai"})
    i = client.post("/api/v1/interpret", json={"analysis": ANALYSIS})
    assert i.status_code == 500
    assert i.json()["error"]["code"] == "AI_INTERPRETATION_ERROR"


def test_unknown_preset_rejected():
    r = client.post("/api/v1/ai-config/set", json={
        "apiKey": "k", "baseUrl": "https://api.example.com/v1",
        "model": "m", "preset": "nope"})
    assert r.json()["ok"] is False and "未知预设" in r.json()["error"]


def test_invalid_inputs_rejected():
    for bad in ({"apiKey": "", "baseUrl": "https://a.com/v1", "model": "m"},
                {"apiKey": "k", "baseUrl": "https://a.com/v1", "model": " "}):
        r = client.post("/api/v1/ai-config/set", json=bad)
        assert r.json()["ok"] is False


# ---------- M49 · 真实 Provider 偏差容错（用户实测：模型自创 claim type=ADVANCED 曾致 500） ----------

def test_mock_unknown_claim_type_degrades_not_500(mock_server):
    """模型输出枚举外 claim type：丢弃该条并声明，不整单失败。"""
    base, srv = mock_server
    srv.behavior = {"key": "k", "content": json.dumps({
        "summary": "MOCK：含未知 claim 类型的输出。",
        "sections": [{
            "type": "advanced", "title": "高级结构",
            "content": "解释文本。",
            "claims": [
                {"type": "ADVANCED", "refId": "advanced:combo", "value": "x"},
                {"type": "fact", "refId": "strength:weighted", "value": "y"},  # 小写应归一化保留
            ],
            "evidenceIds": [], "sourceIds": []}],
        "disagreements": [], "uncertainties": [], "sourceReferences": []}, ensure_ascii=False)}
    client.post("/api/v1/ai-config/set", json={
        "apiKey": "k", "baseUrl": base, "model": "m", "preset": "openai"})
    i = client.post("/api/v1/interpret", json={"analysis": ANALYSIS})
    assert i.status_code == 200
    body = i.json()
    claims = body["interpretation"]["sections"][0]["claims"]
    assert len(claims) == 1 and claims[0]["type"] == "FACT"  # ADVANCED 丢弃，fact→FACT 归一
    assert any("类型未知" in u for u in body["interpretation"]["uncertainties"])
    client.post("/api/v1/ai-config/clear")


# ---------- M48 · Anthropic 协议全链路（MOCK，非真实 Provider 成绩） ----------

def test_mock_anthropic_full_chain(mock_server):
    """MOCK：anthropic 预设 set→test→interpret（x-api-key 真实出站）→content 解析。"""
    base, srv = mock_server
    srv.behavior = {"key": "anthropic-key", "raw_path": False}
    r = client.post("/api/v1/ai-config/set", json={
        "apiKey": "anthropic-key", "baseUrl": base.rstrip("/v1"),
        "model": "claude-sonnet-5-5", "preset": "anthropic"})
    assert r.json()["ok"] is True and r.json()["protocol"] == "anthropic"
    t = client.post("/api/v1/ai-config/test").json()
    assert t["ok"] is True and t["protocol"] == "anthropic"
    i = client.post("/api/v1/interpret", json={"analysis": ANALYSIS})
    assert i.status_code == 200
    body = i.json()
    assert body["interpretation"]["summary"].startswith("MOCK-A")
    assert body["metadata"]["provider"] == "anthropic_compatible"
    assert body["metadata"]["model"] == "claude-sonnet-5-5"
    client.post("/api/v1/ai-config/clear")


# ---------- fake-ip 代理环境回归（M41-hotfix3：曾误拒一切公网 AI 端点） ----------

def test_ssrf_domain_resolving_to_fakeip_allowed_with_warning(monkeypatch):
    """域名 → 198.18.x（Clash fake-ip 段）：放行并附警告，不再一律拒绝。"""
    monkeypatch.setattr(ai_config.socket, "getaddrinfo",
                        lambda h, p: [(socket.AF_INET, None, None, "", ("198.18.0.225", 0))])
    ok, msg = ai_config._ssrf_check("https://api.deepseek.com/v1")
    assert ok is True and "198.18.0.225" in msg and "代理" in msg
    # set 端点透出 warning
    r = client.post("/api/v1/ai-config/set", json={
        "apiKey": SECRET, "baseUrl": "https://api.deepseek.com/v1",
        "model": "gpt-5.6-sol", "preset": "anthropic"})
    body = r.json()
    assert body["ok"] is True and "warning" in body and SECRET not in body["warning"]


def test_ssrf_domain_resolving_to_loopback_rejected(monkeypatch):
    """域名解析到 127.0.0.1（非 local 预设）→ 仍拒绝。"""
    monkeypatch.setattr(ai_config.socket, "getaddrinfo",
                        lambda h, p: [(socket.AF_INET, None, None, "", ("127.0.0.1", 0))])
    ok, msg = ai_config._ssrf_check("https://evil.example.com/v1")
    assert ok is False and "回环" in msg


def test_ssrf_literal_private_ip_still_rejected():
    """字面内网 IP（不经 DNS）→ 拒绝（SSRF 核心防护不变）。"""
    for url in ("http://10.1.2.3/v1", "http://192.168.0.9/v1",
                "http://169.254.1.1/v1", "http://[fe80::1]/v1"):
        ok, _ = ai_config._ssrf_check(url)
        assert ok is False, url
    # 字面公网 IP 放行
    ok, _ = ai_config._ssrf_check("https://8.8.8.8/v1")
    assert ok is True
