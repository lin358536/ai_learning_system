# 智途校园 - AI服务封装（通义千问）
"""
统一AI调用层，切换模型只改此文件。
支持同步返回和SSE流式输出。
"""

import json
import re
import httpx
from typing import AsyncGenerator

from app.core.config import get_settings

settings = get_settings()


def strip_think_tags(text: str) -> str:
    """剥离 qwen3.5 思考模型的 <thinkable>...</thinkable> 标签"""
    text = re.sub(r"<thinkable>.*?</thinkable>", "", text, flags=re.DOTALL)
    text = re.sub(r"</?thinkable>", "", text)
    return text.strip()


def extract_json_from_response(text: str) -> dict | None:
    """从AI响应中提取JSON（支持代码块和纯JSON两种格式）"""
    text = strip_think_tags(text)

    # 尝试从 markdown 代码块中提取
    code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取 {} 块
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    return None


class AiService:
    """通义千问 API 封装"""

    def __init__(self):
        self.api_key = settings.QWEN_API_KEY
        self.base_url = settings.QWEN_BASE_URL
        self.model = settings.QWEN_MODEL

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_messages(self, system_prompt: str, history: list[dict],
                        user_message: str) -> list[dict]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    async def chat(self, system_prompt: str, history: list[dict],
                   user_message: str, temperature: float = 0.7) -> str:
        """同步调用AI，返回完整文本"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._build_headers(),
                json={
                    "model": self.model,
                    "messages": self._build_messages(system_prompt, history, user_message),
                    "temperature": temperature,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return strip_think_tags(content)

    async def chat_json(self, system_prompt: str, history: list[dict],
                        user_message: str) -> dict | None:
        """调用AI并提取JSON响应"""
        text = await self.chat(
            system_prompt=system_prompt,
            history=history,
            user_message=user_message,
            temperature=0.3,  # JSON生成用更低温度
        )
        return extract_json_from_response(text)

    async def chat_stream(self, system_prompt: str, history: list[dict],
                          user_message: str,
                          temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """SSE流式调用AI，逐块 yield 文本片段"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._build_headers(),
                json={
                    "model": self.model,
                    "messages": self._build_messages(system_prompt, history, user_message),
                    "temperature": temperature,
                    "max_tokens": 4096,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                buffer = ""
                think_buffer = ""
                in_think = False

                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if not content:
                            continue
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

                    # 处理思考标签
                    for char in content:
                        if in_think:
                            think_buffer += char
                            if "</thinkable>" in think_buffer:
                                in_think = False
                                think_buffer = ""
                        elif "<thinkable>" in (buffer + char):
                            in_think = True
                            buffer = ""
                        else:
                            buffer += char
                            if len(buffer) >= 2:  # 累积2个字符再yield，减少碎片
                                yield buffer
                                buffer = ""

                # yield剩余buffer
                if buffer.strip():
                    yield buffer.strip()
