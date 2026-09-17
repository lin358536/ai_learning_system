# 智途校园 - 意图识别
"""根据用户消息匹配最合适的工具"""


from app.agent.tools.registry import tool_registry


# 工具关键词映射（优先匹配）
INTENT_KEYWORDS = {
    "generate_plan": ["规划", "计划", "学习规划", "学习计划", "制定规划", "帮我规划", "帮我计划", "学习路径"],
    "generate_resume": ["简历", "写简历", "制作简历", "生成简历", "帮我写简历", "简历模板"],
    "query_plans": ["查看规划", "我的规划", "规划列表", "规划进度", "有几个规划"],
    "query_resumes": ["查看简历", "我的简历", "简历列表", "有几份简历"],
    "query_profile": ["画像", "我的信息", "个人信息", "什么专业", "目标岗位"],
    "query_points": ["积分", "多少积分", "积分排行", "排名", "我的积分", "排行榜"],
}


def identify_intent(user_message: str) -> str | None:
    """
    根据用户消息识别意图（工具key）。

    优先使用关键词精确匹配，回退到模糊匹配工具描述。

    Returns:
        工具key 或 None（未匹配到任何工具）
    """
    msg = user_message.lower().strip()

    # 第一轮：关键词精确匹配
    best_tool = None
    best_score = 0

    for tool_key, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg)
        if score > best_score:
            best_score = score
            best_tool = tool_key

    if best_score > 0 and best_tool:
        return best_tool

    # 第二轮：模糊匹配工具描述
    tool = tool_registry.get_by_description_match(msg)
    if tool:
        return tool.key

    return None


# ── Agent 重构新增：从回复内容解析意图（移植自 coze_client._parse_intent） ──
# 注意：coze_client.py 本体零改动，此处为逻辑复制，供 LangGraph 通道的 node_respond 使用。

# 意图 → 技能 key 映射（SkillEngine 路由的语义来源；query_*/None 由 chat 技能兜底承接）
INTENT_TO_SKILL: dict[str, str] = {
    "generate_plan": "plan",
    "generate_resume": "resume",
}


def parse_intent_from_reply(text: str) -> str:
    """
    从 AI 完整回复中解析意图。

    仅当回复内容明显包含生成的规划/简历结构时才触发，
    避免误匹配功能描述类回复。

    Returns:
        generate_plan / generate_resume / chat（封闭集）
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
