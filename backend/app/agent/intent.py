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
