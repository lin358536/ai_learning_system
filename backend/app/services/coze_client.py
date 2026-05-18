# 智途校园 - 扣子(Coze)智能体客户端（真正异步流式）
import asyncio
import queue
import threading
from typing import AsyncGenerator

from cozepy import (
    Coze, TokenAuth, COZE_CN_BASE_URL,
    Message, ChatEventType,
)

# ── 配置 ────────────────────────────────────────────────────────
COZE_PAT = "pat_d9cbf6pcfz1w73edxytlByjfO6dCgUy5TtAb8Gg3N0xVWqDu7RqXaq36i0EqVQM2"
COZE_BOT_ID = "7628977381587992619"

# 全局 Coze 客户端（懒加载）
_client: Coze | None = None

# 每个用户当前的 conversation_id（首次对话不传，扣子创建后缓存）
_user_conversations: dict[int, str] = {}


def _get_coze_client() -> Coze:
    """获取/创建 Coze 客户端"""
    global _client
    if _client is None:
        _client = Coze(auth=TokenAuth(token=COZE_PAT), base_url=COZE_CN_BASE_URL)
    return _client


def build_context_message(
    user_message: str,
    user_name: str | None,
    profile: dict | None,
    history: list[dict] | None = None,
) -> str:
    """
    将用户画像和历史对话拼接到消息中作为上下文，让小途了解用户信息和对话脉络。
    profile 为 None 时原样返回用户消息。
    history: [{"role": "user"/"assistant", "content": "..."}, ...]
    """
    # 收集有值的字段
    parts = []
    if user_name:
        parts.append(f"姓名：{user_name}")

    # 基础信息
    if profile:
        if profile.get("education") and profile["education"] not in ("专科", ""):
            parts.append(f"学历：{profile['education']}")
        if profile.get("major"):
            parts.append(f"专业：{profile['major']}")
        if profile.get("grade"):
            parts.append(f"年级：{profile['grade']}")
        if profile.get("upgrade_intent"):
            parts.append("升学意愿：有")

        # 职业方向
        if profile.get("target_industry"):
            parts.append(f"意向行业：{profile['target_industry']}")
        if profile.get("target_job"):
            parts.append(f"目标岗位：{profile['target_job']}")
        if profile.get("job_style") and profile["job_style"] not in ("", "未确定"):
            parts.append(f"求职倾向：{profile['job_style']}")

        # 能力画像
        if profile.get("skills"):
            skills_str = "、".join(profile["skills"])
            parts.append(f"技能：{skills_str}")
        if profile.get("certificates"):
            certs_str = "、".join(profile["certificates"])
            parts.append(f"证书：{certs_str}")

    # 构建上下文
    context_lines = []
    if parts:
        context_lines.append("[系统上下文 - 用户画像]")
        context_lines.extend(parts)

    # 拼接历史对话
    if history:
        context_lines.append("\n[对话历史]")
        for msg in history[-10:]:  # 最多取最近10轮
            role_label = "用户" if msg["role"] == "user" else "小途"
            # 截取过长内容
            content = msg["content"]
            if len(content) > 200:
                content = content[:200] + "..."
            context_lines.append(f"{role_label}：{content}")

    if not context_lines:
        return user_message

    context = "\n".join(context_lines)
    return (
        f"{context}\n"
        f"\n[当前用户消息]\n"
        f"{user_message}"
    )


def _run_stream_sync(user_id: int, message: str, conversation_id: str | None,
                      event_queue: queue.Queue):
    """
    在后台线程中运行 Coze 同步流式调用。
    每收到一个事件就放入队列，实现真正的逐事件传递。
    """
    client = _get_coze_client()
    full_content = ""
    last_event = None

    try:
        stream = client.chat.stream(
            bot_id=COZE_BOT_ID,
            user_id=str(user_id),
            conversation_id=conversation_id,
            auto_save_history=True,
            additional_messages=[
                Message.build_user_question_text(message),
            ],
        )

        for event in stream:
            if not event:
                continue

            # 增量消息片段
            if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                content = getattr(event.message, "content", "") or ""
                if content.strip():
                    full_content += content
                    ev = {"type": "text", "content": content}
                    event_queue.put(ev)
                    last_event = ev

            # 对话完成
            elif event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                # 缓存 conversation_id
                if hasattr(event.chat, "conversation_id") and event.chat.conversation_id:
                    _user_conversations[user_id] = event.chat.conversation_id
                intent = _parse_intent(full_content)
                done_ev = {"type": "done", "intent": intent, "full_content": full_content}
                event_queue.put(done_ev)
                last_event = done_ev

            # 对话失败
            elif event.event == ChatEventType.CONVERSATION_CHAT_FAILED:
                err_msg = "扣子智能体响应失败"
                if hasattr(event.chat, "last_error"):
                    err_info = event.chat.last_error
                    if hasattr(err_info, "msg"):
                        err_msg = err_info.msg
                    elif isinstance(err_info, dict):
                        err_msg = err_info.get("msg", err_msg)
                ev = {"type": "error", "message": str(err_msg)}
                event_queue.put(ev)
                last_event = ev

    except Exception as e:
        ev = {"type": "error", "message": f"Coze 调用异常: {str(e)}"}
        event_queue.put(ev)
        last_event = ev

    # 放入结束信号
    event_queue.put(None)


async def chat_stream(
    user_id: int,
    message: str,
) -> AsyncGenerator[dict, None]:
    """
    调用扣子智能体流式对话，逐事件 yield（真正的流式）。

    Yields:
        dict: SSE 事件：
            {"type": "text", "content": "..."}     — AI 回复片段（打字机效果）
            {"type": "done", "intent": "...", "full_content": "..."}  — 对话完成
            {"type": "error", "message": "..."}    — 错误
    """
    conversation_id = _user_conversations.get(user_id)
    event_queue: queue.Queue = queue.Queue()

    # 启动后台线程运行同步 Coze 流
    thread = threading.Thread(
        target=_run_stream_sync,
        args=(user_id, message, conversation_id, event_queue),
        daemon=True,
    )
    thread.start()

    # 在异步循环中逐个从队列取出事件并 yield
    loop = asyncio.get_event_loop()
    while True:
        try:
            # 用 asyncio 的方式等待队列，不阻塞事件循环
            event = await asyncio.to_thread(event_queue.get)
            if event is None:
                break
            yield event
        except Exception:
            break


def _parse_intent(text: str) -> str:
    """
    从 AI 完整回复中解析意图。
    仅当回复内容明显包含生成的规划/简历结构时才触发，
    避免误匹配功能描述类回复。
    """
    text_lower = text.lower()

    # 规划相关 — 关键词匹配 + 结构化内容验证
    plan_keywords = [
        "学习规划", "学习计划", "学习路线", "制定规划", "制定计划",
        "成长路线", "发展路径", "学习方案", "学习路径", "成长规划",
    ]
    plan_keyword_hit = sum(1 for kw in plan_keywords if kw in text_lower)

    # 结构化内容关键词（只要有阶段+任务/目标 就判定）
    plan_structure = ["阶段", "步骤", "第", "周计划", "月计划", "目标", "时间安排", "任务清单"]
    plan_structure_hit = sum(1 for kw in plan_structure if kw in text_lower)

    # 判定条件：有关键词+至少2个结构词，或者无关键词但有3+个结构词（AI可能不用关键词但输出完整结构）
    if (plan_keyword_hit >= 1 and plan_structure_hit >= 2) or plan_structure_hit >= 3:
        return "generate_plan"

    # 简历相关 — 需要同时出现简历关键词和个人信息结构
    resume_keyword_hit = sum(1 for kw in ["简历", "求职简历", "个人简历", "我的简历"] if kw in text_lower)
    resume_structure_hit = sum(1 for kw in ["教育背景", "工作经验", "项目经历", "专业技能", "自我评价", "求职意向", "联系方式"] if kw in text_lower)
    if resume_keyword_hit >= 1 and resume_structure_hit >= 1:
        return "generate_resume"

    return "chat"
