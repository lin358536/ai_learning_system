# 智途校园 - Agent 重构验证：API 集成（langgraph 通道，真实服务）
"""覆盖 T01/T05 验收：空 key 下 /chat 返回 SSE error 事件而非 500；
未授权端点 401/403；SSE 三事件格式逐字节校验。

服务由 conftest.live_server 启动真实 uvicorn（端口 8123，剥离代理）。
"""
import json

import pytest

pytestmark = pytest.mark.usefixtures("live_server")


def _sse_events(response) -> list[dict]:
    events = []
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            events.append(json.loads(payload))
    return events


@pytest.fixture()
def base_url(live_server):
    return live_server.base_url


@pytest.fixture()
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


class TestHealth:
    def test_health_ok(self, http_session, base_url):
        r = http_session.get(f"{base_url}/api/health", timeout=5)
        assert r.status_code == 200
        assert r.json()["success"] is True


class TestAuth:
    def test_chat_without_token_rejected(self, http_session, base_url):
        r = http_session.post(f"{base_url}/api/chat", json={"message": "你好"}, timeout=5)
        assert r.status_code in (401, 403), f"未授权应 401/403，实际 {r.status_code}"
        assert r.status_code != 500

    def test_chat_bad_token_401(self, http_session, base_url):
        r = http_session.post(
            f"{base_url}/api/chat",
            json={"message": "你好"},
            headers={"Authorization": "Bearer invalid.token.here"},
            timeout=5,
        )
        assert r.status_code == 401

    def test_conversations_without_token_rejected(self, http_session, base_url):
        r = http_session.get(f"{base_url}/api/chat/conversations", timeout=5)
        assert r.status_code in (401, 403)

    def test_save_plan_without_token_rejected(self, http_session, base_url):
        r = http_session.post(
            f"{base_url}/api/chat/save-plan", json={"content": "x"}, timeout=5
        )
        assert r.status_code in (401, 403)

    def test_save_resume_without_token_rejected(self, http_session, base_url):
        r = http_session.post(
            f"{base_url}/api/chat/save-resume", json={"content": "x"}, timeout=5
        )
        assert r.status_code in (401, 403)


class TestChatEmptyKey:
    """T01/T05 验收：DEEPSEEK_API_KEY 为空 → SSE error 事件，绝不 500。

    本类使用 empty_key_server（子进程 env 显式注入空 key），前置条件不依赖
    真实 .env 的状态。
    """

    @pytest.fixture()
    def base_url(self, empty_key_server):
        return empty_key_server.base_url

    def test_chat_returns_error_event_not_500(self, http_session, base_url, headers):
        r = http_session.post(
            f"{base_url}/api/chat",
            json={"message": "你好"},
            headers=headers,
            timeout=30,
        )
        assert r.status_code == 200, f"应返回 SSE 流（200），实际 {r.status_code}"
        assert "text/event-stream" in r.headers.get("Content-Type", "")
        events = _sse_events(r)
        assert events, "SSE 流应至少包含一个事件"
        error_events = [e for e in events if e.get("type") == "error"]
        assert error_events, f"空 key 下应返回 error 事件，实际事件: {events}"
        # SSE 三事件铁律：error 事件字段逐字节 {"type","message"}
        assert set(error_events[0].keys()) == {"type", "message"}
        assert "DEEPSEEK_API_KEY" in error_events[0]["message"]

    def test_chat_empty_message_error_event(self, http_session, base_url, headers):
        """边界：空消息（schema 允许空串）→ error 事件而非 500。"""
        r = http_session.post(
            f"{base_url}/api/chat",
            json={"message": ""},
            headers=headers,
            timeout=30,
        )
        assert r.status_code == 200
        events = _sse_events(r)
        assert any(e.get("type") == "error" for e in events)

    def test_chat_oversized_message_422(self, http_session, base_url, headers):
        """边界：超长消息（>1000 字符）→ 422 参数校验。"""
        r = http_session.post(
            f"{base_url}/api/chat",
            json={"message": "长" * 1001},
            headers=headers,
            timeout=10,
        )
        assert r.status_code == 422

    def test_chat_with_explicit_conversation_id(self, http_session, base_url, headers):
        """边界：空 conversation 历史 + 显式 conversation_id。"""
        r = http_session.post(
            f"{base_url}/api/chat",
            json={"message": "首轮", "conversation_id": "qa-test-conv-empty-key"},
            headers=headers,
            timeout=30,
        )
        assert r.status_code == 200
        assert any(e.get("type") == "error" for e in _sse_events(r))


class TestConversations:
    def test_conversations_with_token(self, http_session, base_url, headers):
        r = http_session.get(
            f"{base_url}/api/chat/conversations", headers=headers, timeout=10
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert isinstance(body["data"]["conversations"], list)
        for conv in body["data"]["conversations"]:
            assert set(conv.keys()) == {
                "conversation_id",
                "title",
                "last_message_at",
                "message_count",
                "icon",
            }
            assert conv["icon"] in ("📋", "📄", "💬")

    def test_save_plan_parse_fail_graceful(self, http_session, base_url, headers):
        """save-plan 端点存活且解析失败时优雅返回（不 500）。"""
        r = http_session.post(
            f"{base_url}/api/chat/save-plan",
            json={"content": "完全没有结构的闲聊内容"},
            headers=headers,
            timeout=10,
        )
        assert r.status_code == 200
        body = r.json()
        # 无结构内容：PARSE_FAIL 或兜底保存成功均可接受，但不允许 500
        assert "success" in body
