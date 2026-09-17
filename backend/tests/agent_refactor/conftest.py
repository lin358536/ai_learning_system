# 智途校园 - Agent 重构独立验证测试（QA: Edward）
"""公共夹具：sys.path、JWT token、DB 会话、真实服务子进程。

注意：
- 必须以 backend/ 为工作目录运行 pytest（.env 相对路径解析依赖 cwd）；
- shell 注入了 HTTP_PROXY/HTTPS_PROXY（127.0.0.1:64025），所有本机 HTTP
  请求必须绕过代理（requests.Session(trust_env=False) / 清理子进程环境）；
- 不使用 start.bat/stop.bat：stop.bat 会 taskkill 全机 python.exe（含 pytest
  自身），改为由测试直接管理 uvicorn 子进程生命周期。
"""
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

# Windows 下 aiomysql/uvicorn 使用 Selector 事件循环更稳
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 本机含测试数据最多的用户（points/plans/resumes/profile 均有数据）
TEST_USER_ID = 3

ENV_PATH = BACKEND_DIR / ".env"


def _clean_env() -> dict:
    """子进程环境：剥离代理变量，避免本机请求被 127.0.0.1:64025 拦截。"""
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        env.pop(k, None)
    return env


@pytest.fixture(scope="session")
def auth_token() -> str:
    """用应用自身密钥签发合法 JWT（与 auth_service 登录产物同构）。"""
    from app.core.security import create_access_token

    return create_access_token({"sub": str(TEST_USER_ID)})


@pytest.fixture()
def http_session():
    """绕过代理的本机 HTTP 会话。"""
    import requests

    s = requests.Session()
    s.trust_env = False  # 忽略 HTTP_PROXY 等环境变量
    yield s
    s.close()


class ServerHandle:
    def __init__(self, proc: subprocess.Popen, base_url: str, log_path: Path):
        self.proc = proc
        self.base_url = base_url
        self.log_path = log_path


def start_server(
    port: int, timeout: float = 40.0, extra_env: dict | None = None
) -> ServerHandle:
    """启动真实 uvicorn 服务（剥离代理环境），等待 /api/health 就绪。

    extra_env: 显式覆盖子进程环境变量。pydantic-settings 中**环境变量优先于 .env
    文件**，因此可用它构造「与真实 .env 无关」的前置条件（如 DEEPSEEK_API_KEY=""
    或 AGENT_BACKEND=coze），避免用例依赖真实 .env 的状态。
    """
    log_path = BACKEND_DIR / "tests" / "agent_refactor" / f"server_{port}.log"
    log_f = open(log_path, "w", encoding="utf-8", errors="replace")
    env = _clean_env()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.Popen(
        [
            str(BACKEND_DIR / "venv" / "Scripts" / "python.exe"),
            "-m", "uvicorn", "main:app",
            "--host", "127.0.0.1", "--port", str(port),
        ],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + timeout
    import requests

    while time.monotonic() < deadline:
        if proc.poll() is not None:
            log_f.flush()
            raise RuntimeError(
                f"服务进程提前退出（code={proc.returncode}），日志：{log_path}"
            )
        try:
            r = requests.get(f"{base_url}/api/health", timeout=2, proxies={"http": None, "https": None})
            if r.status_code == 200:
                return ServerHandle(proc, base_url, log_path)
        except Exception:
            pass
        time.sleep(0.5)
    proc.kill()
    raise RuntimeError(f"服务启动超时（{timeout}s），日志：{log_path}")


def stop_server(handle: ServerHandle) -> None:
    """精准终止本测试启动的 uvicorn 进程（不使用 stop.bat）。"""
    proc = handle.proc
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


@pytest.fixture(scope="module")
def live_server():
    """langgraph 通道（.env 现状）真实服务。"""
    handle = start_server(8123)
    yield handle
    stop_server(handle)


@pytest.fixture()
def empty_key_env(monkeypatch):
    """显式构造「DEEPSEEK_API_KEY 为空」的前置条件（进程内，不依赖真实 .env）。

    环境变量优先于 .env 文件：setenv("DEEPSEEK_API_KEY", "") 后清空 settings
    缓存，get_settings().DEEPSEEK_API_KEY 必为空；用例结束清缓存并重置 LLM 单例，
    避免污染其它用例。
    """
    from app.core.config import get_settings
    from app.llm.llm_provider import reset_llm

    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    get_settings.cache_clear()
    reset_llm()
    try:
        yield
    finally:
        get_settings.cache_clear()
        reset_llm()


@pytest.fixture(scope="module")
def empty_key_server():
    """显式注入空 DEEPSEEK_API_KEY 的 langgraph 真实服务（不依赖真实 .env 状态）。

    环境变量优先于 .env 文件，故子进程内 DEEPSEEK_API_KEY="" 一定生效，
    无需改动真实 .env。
    """
    handle = start_server(8125, extra_env={"DEEPSEEK_API_KEY": ""})
    yield handle
    stop_server(handle)
