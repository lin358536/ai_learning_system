# 智途校园 - 对话路由（SSE流式 | Coze扣子智能体 | 自动保存规划/简历）
import json
import re
import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.coze_client import chat_stream, build_context_message
from app.models.chat import ChatMessage
from app.models.user import User
from app.services.profile_service import ProfileService
from app.services.plan_service import PlanService
from app.services.resume_service import ResumeService
from app.services.points_service import PointsService

router = APIRouter(tags=["对话"])


# ── 请求模型 ─────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=1000, description="用户消息")
    conversation_id: str | None = Field(None, description="扣子会话ID")


class SaveContentRequest(BaseModel):
    content: str = Field(..., description="AI生成的完整回复内容")


# ── SSE 流式对话 ──────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE流式对话接口 — 查用户画像拼上下文后调用扣子智能体"""
    user_id = user["user_id"]

    # 生成或复用 conversation_id
    conv_id = req.conversation_id or str(uuid_lib.uuid4())

    # 保存用户消息到本地数据库
    user_msg = ChatMessage(
        user_id=user_id,
        conversation_id=conv_id,
        role="user",
        content=req.message,
        intent=None,
    )
    db.add(user_msg)
    await db.flush()
    await db.commit()

    # 查用户画像，拼接到消息上下文
    profile_data = None
    user_name = None
    try:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user_obj = user_result.scalar_one_or_none()
        if user_obj:
            user_name = user_obj.name

        profile_service = ProfileService()
        profile_obj = await profile_service.get_profile(db, user_id)
        if profile_obj:
            profile_data = ProfileService.to_dict(profile_obj)
    except Exception:
        pass

    context_message = build_context_message(req.message, user_name, profile_data)

    full_reply = ""
    final_intent = "chat"

    async def event_stream():
        nonlocal full_reply, final_intent
        try:
            async for event in chat_stream(user_id, context_message):
                event_type = event.get("type")

                if event_type == "text":
                    full_reply += event.get("content", "")
                    # 实时转发给前端（真正的流式）
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                elif event_type == "done":
                    final_intent = event.get("intent", "chat")
                    if event.get("full_content") and not full_reply:
                        full_reply = event["full_content"]
                    # 在 done 事件中注入 conversation_id，方便前端捕获
                    event["conversation_id"] = conv_id
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                elif event_type == "error":
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 流结束后保存助手回复到本地数据库
            if full_reply.strip():
                assistant_msg = ChatMessage(
                    user_id=user_id,
                    conversation_id=conv_id,
                    role="assistant",
                    content=full_reply.strip(),
                    intent=final_intent,
                )
                db.add(assistant_msg)
                await db.flush()
                await db.commit()

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── 自动保存规划 ──────────────────────────────────────────────────

@router.post("/chat/save-plan")
async def save_plan_from_chat(
    req: SaveContentRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从对话内容中提取并保存学习规划"""
    user_id = user["user_id"]
    content_text = req.content

    # 从AI回复中提取规划标题和内容
    title = _extract_plan_title(content_text)
    plan_content = _extract_plan_content(content_text)

    if not plan_content:
        return {"success": False, "error": {"code": "PARSE_FAIL", "message": "未能从回复中提取到有效规划内容"}}

    try:
        plan_service = PlanService()
        plan = await plan_service.save_plan(db, user_id, title, plan_content)
        points_service = PointsService()
        await points_service.add_points(db, user_id, 20, "创建学习规划", "plan")
        await db.commit()
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        return {"success": False, "error": {"code": "SAVE_FAIL", "message": str(e)}}

    return {
        "success": True,
        "data": {"id": plan.id, "title": title, "message": "规划保存成功"},
    }


# ── 自动保存简历 ──────────────────────────────────────────────────

@router.post("/chat/save-resume")
async def save_resume_from_chat(
    req: SaveContentRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """从对话内容中提取并保存简历"""
    user_id = user["user_id"]
    content_text = req.content

    # 从AI回复中提取简历标题和内容
    title = _extract_resume_title(content_text)
    resume_content = _extract_resume_content(content_text)

    if not resume_content:
        return {"success": False, "error": {"code": "PARSE_FAIL", "message": "未能从回复中提取到有效简历内容"}}

    try:
        resume_service = ResumeService()
        resume = await resume_service.save_resume(db, user_id, title, resume_content)
        points_service = PointsService()
        await points_service.add_points(db, user_id, 15, "生成简历", "resume")
        await db.commit()
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        return {"success": False, "error": {"code": "SAVE_FAIL", "message": str(e)}}

    return {
        "success": True,
        "data": {"id": resume.id, "title": title, "message": "简历保存成功"},
    }


# ── 对话分组（Conversations） ──────────────────────────────────────

@router.get("/chat/conversations")
async def chat_conversations(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """获取对话列表（按 conversation_id 分组）"""
    user_id = user["user_id"]
    offset = (page - 1) * limit

    # 统计总数
    count_result = await db.execute(
        select(func.count(func.distinct(ChatMessage.conversation_id)))
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.conversation_id.isnot(None),
        )
    )
    total = count_result.scalar() or 0

    # 查询对话列表：每个 conversation 的首条用户消息（作为标题） + 最后消息时间 + 消息数
    stmt = (
        select(
            ChatMessage.conversation_id,
            func.any_value(ChatMessage.content).label("title_raw"),
            func.max(ChatMessage.created_at).label("last_message_at"),
            func.count(ChatMessage.id).label("message_count"),
        )
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.conversation_id.isnot(None),
            ChatMessage.role == "user",
        )
        .group_by(ChatMessage.conversation_id)
        .order_by(func.max(ChatMessage.created_at).desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # 批量获取每个对话的最新 intent（用 MAX(id) 取每个对话最后一条 assistant 消息）
    conv_ids = [r.conversation_id for r in rows]
    intent_map = {}
    if conv_ids:
        # 子查询：每个 conversation_id 最新消息的 id
        max_id_sub = (
            select(
                ChatMessage.conversation_id,
                func.max(ChatMessage.id).label("max_id")
            )
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.conversation_id.in_(conv_ids),
                ChatMessage.role == "assistant",
            )
            .group_by(ChatMessage.conversation_id)
            .subquery()
        )
        intent_rows = await db.execute(
            select(
                ChatMessage.conversation_id,
                ChatMessage.intent,
            )
            .join(max_id_sub, ChatMessage.id == max_id_sub.c.max_id)
            .where(ChatMessage.intent.isnot(None))
        )
        for r2 in intent_rows.all():
            intent_map[r2.conversation_id] = r2.intent

    def _get_icon(intent: str | None) -> str:
        if intent == "generate_plan":
            return "📋"
        elif intent == "generate_resume":
            return "📄"
        return "💬"

    conversations = []
    for row in rows:
        title = (row.title_raw or "")[:30]
        conversations.append({
            "conversation_id": row.conversation_id,
            "title": title,
            "last_message_at": row.last_message_at.isoformat() if row.last_message_at else None,
            "message_count": row.message_count,
            "icon": _get_icon(intent_map.get(row.conversation_id)),
        })

    return {
        "success": True,
        "data": {
            "conversations": conversations,
            "total": total,
            "page": page,
            "limit": limit,
        },
    }


@router.get("/chat/conversations/{conversation_id}")
async def chat_conversation_detail(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定对话的所有消息"""
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user["user_id"],
            ChatMessage.conversation_id == conversation_id,
        )
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    return {
        "success": True,
        "data": {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "intent": m.intent,
                    "conversation_id": m.conversation_id,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
                if not m.content.startswith("[待确认]")
            ],
        },
    }


@router.delete("/chat/history")
async def clear_chat_history(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清空当前用户的全部对话历史"""
    await db.execute(
        delete(ChatMessage).where(ChatMessage.user_id == user["user_id"])
    )
    await db.commit()
    return {"success": True, "data": {"message": "对话历史已清空"}}


@router.delete("/chat/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除指定对话"""
    await db.execute(
        delete(ChatMessage).where(
            ChatMessage.user_id == user["user_id"],
            ChatMessage.conversation_id == conversation_id,
        )
    )
    await db.commit()
    return {"success": True, "data": {"message": "对话已删除"}}


# ── 内容提取辅助函数 ──────────────────────────────────────────────

def _safe_title(raw: str, fallback: str = "AI生成", max_len: int = 200) -> str:
    """确保标题不超过数据库字段长度限制"""
    title = raw.strip().replace('#', '').replace('*', '').strip()
    if not title or len(title) > max_len:
        title = title[:max_len].rsplit(' ', 1)[0] if ' ' in title[:max_len] else title[:max_len]
        if not title:
            title = fallback
    return title


def _extract_plan_from_json(text: str) -> dict | None:
    """
    从AI回复中提取JSON格式的规划数据，自动兼容多种嵌套结构。

    支持的Coze输出格式：
    格式A（纯阶段）: {"规划标题": {"阶段一": {阶段字段}, "阶段二": {...}}}
    格式B（按天）:   {"规划标题": {"Day1": {阶段字段}, "Day2": {...}}}
    格式C（周+天）:  {"规划标题": {"第一周：标题": {"Day1": {...}}, "第二周：标题": {"Day2": {...}}}}
    格式D（周+阶段）:{"规划标题": {"第一周": {"阶段一": {...}, "阶段二": {...}}}}
    以及以上格式的任意混合变体。
    """
    # 去掉可能的 markdown 代码块包裹
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\n?\s*```\s*$', '', cleaned, flags=re.MULTILINE)

    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        # 可能JSON嵌在普通文本中，尝试提取 {...} 块
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if not json_match:
            return None
        try:
            data = json.loads(json_match.group())
        except (json.JSONDecodeError, TypeError):
            return None

    if not isinstance(data, dict):
        return None

    # ── 辅助函数 ──

    STAGE_FIELD_KEYS = ("阶段名称", "总述说明", "目标", "任务清单", "参考资料")

    def _is_stage_node(d: dict) -> bool:
        """判断字典是否是一个阶段数据节点（包含阶段字段）"""
        return isinstance(d, dict) and any(k in d for k in STAGE_FIELD_KEYS)

    def _collect_all_stages(node: dict, depth: int = 0, max_depth: int = 4) -> list[tuple[str, dict]]:
        """
        递归展平嵌套结构，收集所有 (阶段key, 阶段数据dict)。
        兼容各种嵌套层数和 key 命名方式。
        """
        if not isinstance(node, dict) or depth > max_depth:
            return []
        results = []
        for key, val in node.items():
            if not isinstance(val, dict):
                continue
            if _is_stage_node(val):
                # val 本身就是阶段数据
                results.append((key, val))
            else:
                # val 是中间层（如 "第一周：MySQL基础" -> {"Day1": {...}, ...}），继续展平
                results.extend(_collect_all_stages(val, depth + 1, max_depth))
        return results

    # ── 提取规划标题和阶段 ──

    plan_title = ""
    raw_stages = []  # [(key, data), ...]

    for key, val in data.items():
        if isinstance(val, dict) and val:
            # 检查是否直接包含阶段数据
            first_child = next(iter(val.values()), None)
            if isinstance(first_child, dict) and _is_stage_node(first_child):
                plan_title = key
                # val 的所有 child 都是阶段
                for k, v in val.items():
                    if _is_stage_node(v):
                        raw_stages.append((k, v))
                break
            else:
                # 可能有多层嵌套，递归展平
                collected = _collect_all_stages(val)
                if collected:
                    plan_title = key
                    raw_stages = collected
                    break

    if not raw_stages:
        return None

    # ── 排序 + 构建输出 ──

    def _sort_key(item: tuple[str, dict]) -> int:
        """按 Day数字 / 阶段中文数字 / 阿拉伯数字 排序"""
        key_str = item[0]
        # Day1, Day2, ...
        day_match = re.match(r'Day\s*(\d+)', key_str, re.IGNORECASE)
        if day_match:
            return int(day_match.group(1))
        # 阶段一, 阶段二, ...
        cn_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                  "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
                  "十一": 11, "十二": 12, "十三": 13, "十四": 14}
        for cn, num in cn_map.items():
            if cn in key_str:
                return num
        # 阿拉伯数字
        nums = re.findall(r'\d+', key_str)
        return int(nums[0]) if nums else 99

    raw_stages.sort(key=_sort_key)

    stages = []
    all_tasks = []

    for stage_key, stage_data in raw_stages:
        stage_name = str(stage_data.get("阶段名称", stage_key))[:200]
        summary = str(stage_data.get("总述说明", ""))[:500]
        goals = [str(g)[:500] for g in stage_data.get("目标", []) if g]
        tasks = [str(t)[:500] for t in stage_data.get("任务清单", []) if t]
        all_tasks.extend(tasks)

        stages.append({
            "name": stage_name,
            "summary": summary,
            "goals": goals,
        })

    if not stages:
        return None

    return {
        "title": plan_title,
        "stages": stages,
        "daily_tasks": all_tasks[:50],
    }


def _extract_plan_title(text: str) -> str:
    """从AI回复中提取规划标题，优先JSON顶层key，其次取第一个阶段标题"""
    # 优先从JSON中提取标题
    json_result = _extract_plan_from_json(text)
    if json_result and json_result.get("title"):
        return _safe_title(json_result["title"], fallback="AI生成学习规划")

    # Fallback: Markdown 格式
    stage_match = re.search(r'(?:^|\n)\s*#{0,4}\s*阶段[一二三四五六七八九十\d]+\s*[：:]\s*(.+?)(?:\n|$)', text, re.MULTILINE)
    if stage_match:
        title = stage_match.group(1).strip().rstrip('：:')
        return _safe_title(title, fallback="AI生成学习规划")

    patterns = [
        r'#{1,3}\s*(.+?规划.+?)(?:\n|$)',
        r'#{1,3}\s*(.+?计划.+?)(?:\n|$)',
        r'\*\*(.+?规划.*?)\*\*',
        r'\*\*(.+?计划.*?)\*\*',
        r'「(.+?)」',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _safe_title(match.group(1), fallback="AI生成学习规划")
    return "AI生成学习规划"


def _extract_plan_content(text: str) -> dict:
    """
    从AI回复中提取规划内容，返回结构化字典。
    优先尝试 JSON 格式解析，失败时 fallback 到 Markdown 正则解析。

    JSON结构：
    {"规划标题": {"阶段一": {"阶段名称":"...", "总述说明":"...", "目标":[...], "任务清单":[...]} }}

    Markdown结构（兼容）：
      ### 阶段一：标题
      [总述]
      **目标：**  - 目标项
      **任务清单：**  - 任务项
    """
    # 优先尝试 JSON
    json_result = _extract_plan_from_json(text)
    if json_result:
        json_result["raw_markdown"] = text
        return json_result

    # Fallback: Markdown 正则解析
    stages = []
    all_tasks = []

    stage_pattern = r'(?:^|\n)\s*#{0,4}\s*(阶段[一二三四五六七八九十\d]+)\s*[：:]\s*(.*?)(?:\n|$)'
    stage_splits = list(re.finditer(stage_pattern, text, re.MULTILINE))

    if stage_splits:
        for idx, match in enumerate(stage_splits):
            stage_num = match.group(1).strip()
            stage_title = match.group(2).strip()
            full_name = f"{stage_num}：{stage_title}" if stage_title else stage_num

            start = match.end()
            end = stage_splits[idx + 1].start() if idx + 1 < len(stage_splits) else len(text)
            section = text[start:end]

            summary_match = re.search(r'\[([^\]]+)\]', section)
            summary = summary_match.group(1).strip() if summary_match else ""

            goals = _extract_list_under_heading(section, "目标", stop_words=["任务清单", "每日安排"])
            task_items = _extract_list_under_heading(section, "任务清单", stop_words=["每日安排", "目标"])
            all_tasks.extend(task_items)

            stages.append({
                "name": full_name[:200],
                "summary": summary[:500] if summary else "",
                "goals": goals,
            })
    else:
        goals = _extract_list_under_heading(text, "目标")
        tasks = _extract_list_under_heading(text, "任务清单")
        all_tasks = tasks[:30] if tasks else goals[:30]
        stages = [{"name": "综合规划", "summary": "", "goals": goals}] if goals else [{"name": "综合规划", "summary": "", "goals": []}]

    noise_keywords = ["我是小途", "小途可以", "欢迎", "温馨提示", "点击"]
    all_tasks = [t for t in all_tasks if len(t) >= 4 and not any(kw in t for kw in noise_keywords)]

    return {
        "raw_markdown": text,
        "stages": stages if stages else [{"name": "综合规划", "summary": "", "goals": []}],
        "daily_tasks": all_tasks[:50],
    }


def _extract_list_under_heading(text: str, heading: str, stop_words: list[str] | None = None) -> list[str]:
    """
    从文本中提取指定标题下的列表项。
    heading: 标题关键词（如 "目标"、"任务清单"）
    stop_words: 遇到这些词时停止提取

    支持两种格式：
    - 标准 markdown 列表：- xxx / • xxx / 1. xxx
    - 纯文本换行列表（无前缀符号，每行一条）

    标题格式兼容：
    - 纯文本：目标：\n
    - 加粗：**目标：**\n / **目标**：\n
    - Markdown标题：### 目标：\n
    """
    # 找到标题位置（兼容多种加粗/冒号组合格式）
    # 先尝试完整的加粗行匹配（**标题：**\n 或 **标题**：\n），再退化为纯文本
    heading_match = None
    bold_patterns = [
        # **目标：**\n  — 加粗包裹，冒号在内
        re.compile(r'\*{2}\s*' + re.escape(heading) + r'\s*[：:]?\s*\*{2}\s*\n', re.IGNORECASE),
        # **目标**：\n  — 加粗包裹，冒号在外
        re.compile(r'\*{2}\s*' + re.escape(heading) + r'\s*\*{2}\s*[：:]?\s*\n', re.IGNORECASE),
    ]
    for bp in bold_patterns:
        heading_match = bp.search(text)
        if heading_match:
            break
    if not heading_match:
        # 纯文本或 markdown 标题格式：目标：\n / ### 目标：\n
        heading_match = re.compile(
            r'(?:#{1,4}\s*)?' + re.escape(heading) + r'\s*[：:]?\s*\n',
            re.IGNORECASE,
        ).search(text)
    if not heading_match:
        return []

    # 从标题后开始，逐行提取列表项
    start = heading_match.end()
    lines = text[start:].split('\n')
    items = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 遇到下一个阶段标题则停止
        if re.match(r'^#{0,4}\s*阶段[一二三四五六七八九十\d]+\s*[：:]', stripped):
            break
        # 遇到下一个 markdown 标题停止
        if re.match(r'^#{1,4}\s+\S', stripped):
            break
        if stop_words:
            if any(re.search(re.escape(sw), stripped) for sw in stop_words):
                break

        # 先尝试匹配标准列表项：- / • / 数字. / 数字、/ 数字)
        list_match = re.match(r'\s*(?:[-•]|\d+[.、)）])\s+(.+)', stripped)
        if list_match:
            item = list_match.group(1).strip()
            if len(item) >= 4:
                items.append(item[:500])
        else:
            # 纯文本行（无前缀符号）：作为列表项纳入
            # 但要排除"每日安排"等标题行和 DayX 开头的内容
            if re.match(r'^Day\d+', stripped, re.IGNORECASE):
                # DayX 行属于详细安排，跳过
                continue
            if re.match(r'^(?:#{1,4}\s*|\*\*)', stripped):
                continue
            if len(stripped) >= 4 and not stripped.endswith('：') and not stripped.endswith(':'):
                items.append(stripped[:500])

    return items


def _extract_resume_from_json(text: str) -> dict | None:
    """
    从AI回复中提取JSON格式的简历数据。

    期望的Coze输出格式：
    {
      "求职简历": {
        "基本信息": {"姓名":"", "学校":"", "专业":"", "学历":"", "求职意向":"", "联系方式":""},
        "教育背景": [{"学校":"", "专业":"", "学历":"", "时间":""}],
        "专业技能": ["技能1", "技能2"],
        "项目经历": [{"名称":"", "角色":"", "时间":"", "描述":"", "成果":""}],
        "证书与比赛": [{"名称":"", "等级/颁发机构":"", "时间":""}],
        "自我评价": ""
      }
    }
    顶层 key 即为简历标题。
    """
    # 去掉 markdown 代码块包裹
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\n?\s*```\s*$', '', cleaned, flags=re.MULTILINE)

    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if not json_match:
            return None
        try:
            data = json.loads(json_match.group())
        except (json.JSONDecodeError, TypeError):
            return None

    if not isinstance(data, dict):
        return None

    # 找到顶层 key（简历标题）及其内容
    resume_title = ""
    resume_body: dict | None = None

    for key, val in data.items():
        if isinstance(val, dict) and (
            "基本信息" in val or "专业技能" in val or "项目经历" in val
        ):
            resume_title = key
            resume_body = val
            break

    if resume_body is None:
        return None

    # ── 提取各字段 ──
    basic = resume_body.get("基本信息", {})
    if not isinstance(basic, dict):
        basic = {}

    education = resume_body.get("教育背景", [])
    if not isinstance(education, list):
        education = []

    skills = resume_body.get("专业技能", [])
    if not isinstance(skills, list):
        skills = [str(skills)] if skills else []

    experience = resume_body.get("项目经历", [])
    if not isinstance(experience, list):
        experience = []

    # 证书与比赛：兼容 key 中带空格的变体（等级/颁发机构 / 等级 / 颁发机构）
    certs_raw = resume_body.get("证书与比赛", [])
    if not isinstance(certs_raw, list):
        certs_raw = []
    certs = []
    for cert in certs_raw:
        if not isinstance(cert, dict):
            continue
        # 兼容 "等级/颁发机构" 和 "等级 / 颁发机构" 两种 key 写法
        institution = cert.get("等级/颁发机构") or cert.get("等级 / 颁发机构") or ""
        certs.append({
            "名称": str(cert.get("名称", ""))[:200],
            "等级/颁发机构": str(institution)[:200],
            "时间": str(cert.get("时间", ""))[:50],
        })

    summary = str(resume_body.get("自我评价", ""))[:1000]

    return {
        "title": resume_title,
        "basic": {
            "姓名": str(basic.get("姓名", ""))[:50],
            "学校": str(basic.get("学校", ""))[:100],
            "专业": str(basic.get("专业", ""))[:100],
            "学历": str(basic.get("学历", ""))[:20],
            "求职意向": str(basic.get("求职意向", ""))[:200],
            "联系方式": str(basic.get("联系方式", ""))[:200],
        },
        "education": [
            {
                "学校": str(e.get("学校", ""))[:100],
                "专业": str(e.get("专业", ""))[:100],
                "学历": str(e.get("学历", ""))[:20],
                "时间": str(e.get("时间", ""))[:50],
            }
            for e in education if isinstance(e, dict)
        ],
        "skills": [str(s)[:500] for s in skills if s],
        "experience": [
            {
                "名称": str(exp.get("名称", ""))[:200],
                "角色": str(exp.get("角色", ""))[:100],
                "时间": str(exp.get("时间", ""))[:50],
                "描述": str(exp.get("描述", ""))[:1000],
                "成果": str(exp.get("成果", ""))[:500],
            }
            for exp in experience if isinstance(exp, dict)
        ],
        "certs": certs,
        "summary": summary,
        "raw_markdown": text,
    }


def _extract_resume_title(text: str) -> str:
    """从AI回复中提取简历标题，优先从JSON顶层key获取"""
    json_result = _extract_resume_from_json(text)
    if json_result and json_result.get("title"):
        return _safe_title(json_result["title"], fallback="AI生成简历")

    # Fallback: Markdown 格式
    patterns = [
        r'#{1,3}\s*(.+?简历.+?)(?:\n|$)',
        r'\*\*(.+?简历.*?)\*\*',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _safe_title(match.group(1), fallback="AI生成简历")
    return "AI生成简历"


def _extract_resume_content(text: str) -> dict:
    """
    从AI回复中提取简历内容，返回结构化字典。
    优先尝试 JSON 格式解析，失败时 fallback 存原文。

    JSON结构（期望Coze输出）：
    {"求职简历": {"基本信息":{...}, "教育背景":[...], "专业技能":[...],
                  "项目经历":[...], "证书与比赛":[...], "自我评价":"..."}}
    """
    json_result = _extract_resume_from_json(text)
    if json_result:
        return json_result

    # Fallback：存原始文本，前端走 markdown 渲染
    return {
        "title": "",
        "basic": {},
        "education": [],
        "skills": [],
        "experience": [],
        "certs": [],
        "summary": "",
        "raw_markdown": text,
    }
