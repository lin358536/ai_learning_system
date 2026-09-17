# 智途校园 - Agent 重构验证：AGENT_BACKEND=coze 回退演练
"""覆盖 T05 验收：.env 切 AGENT_BACKEND=coze 后旧路径可达。

预期：Coze PAT 已失效（任务书附录 C.7，改造前即失效），平台返回 4101，
API 层必须将其包装为 SSE error 事件而非 500。

夹具**不修改真实 .env**，改为在启动子进程时显式注入 AGENT_BACKEND=coze。

说明：app/services/coze_client.py（零改动文件）在 import 时执行 load_dotenv()，
把 .env 注入 os.environ；而 conftest._clean_env() 继承 os.environ 启动子进程。
pydantic-settings 中环境变量优先于 .env 文件，故只有显式向子进程 env 注入
AGENT_BACKEND=coze（覆盖继承来的 langgraph），才能确保子进程真正走 Coze 通道。
"""
import json

import pytest

from conftest import start_server, stop_server


@pytest.fixture(scope="module")
def coze_server():
    handle = start_server(8124, extra_env={"AGENT_BACKEND": "coze"})
    yield handle
    stop_server(handle)


def _sse_events(response) -> list[dict]:
    events = []
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            events.append(json.loads(line[len("data:"):].strip()))
    return events


def test_coze_fallback_error_event_not_500(http_session, coze_server, auth_token):
    r = http_session.post(
        f"{coze_server.base_url}/api/chat",
        json={"message": "你好"},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=60,
    )
    assert r.status_code == 200, f"Coze 通道失效也应返回 SSE（200），实际 {r.status_code}"
    events = _sse_events(r)
    assert events, "SSE 流应至少包含一个事件"
    error_events = [e for e in events if e.get("type") == "error"]
    assert error_events, f"Coze PAT 失效应包装为 error 事件，实际: {events}"
    assert set(error_events[0].keys()) == {"type", "message"}


def test_coze_channel_health(http_session, coze_server):
    r = http_session.get(f"{coze_server.base_url}/api/health", timeout=5)
    assert r.status_code == 200
