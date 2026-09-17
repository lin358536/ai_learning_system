# 智途校园 - Agent 重构验证：意图识别双通道
"""覆盖任务书 1.7 / T03 验收：identify_intent 关键词通道 + parse_intent_from_reply 兜底。"""
import pytest

from app.agent.intent import (
    INTENT_TO_SKILL,
    identify_intent,
    parse_intent_from_reply,
)


class TestIdentifyIntent:
    @pytest.mark.parametrize(
        "message,expected",
        [
            ("帮我制定学习计划", "generate_plan"),  # T03 验收原文用例
            ("帮我制定学习规划", "generate_plan"),
            ("给我一条学习路径", "generate_plan"),
            ("帮我写简历", "generate_resume"),
            ("我想制作一份简历", "generate_resume"),
            ("我的积分还有多少", "query_points"),
            ("积分排行榜上我排第几", "query_points"),
            ("查看规划进度", "query_plans"),
            ("查看简历列表", "query_resumes"),
            ("我的个人信息和目标岗位", "query_profile"),
        ],
    )
    def test_keyword_hit(self, message, expected):
        assert identify_intent(message) == expected

    @pytest.mark.parametrize(
        "message",
        [
            "你好",               # 无关键词命中
            "今天天气怎么样",      # 闲聊
            "",                   # 空消息兜底
            "   ",                # 纯空白
            "什么是快速排序",      # 知识问答
        ],
    )
    def test_no_hit_returns_none(self, message):
        assert identify_intent(message) is None

    def test_case_and_whitespace_insensitive(self):
        assert identify_intent("  帮我规划一下  ") == "generate_plan"


class TestParseIntentFromReply:
    def test_plan_by_structure_words(self):
        # T03 验收原文用例：阶段 + 任务清单 等结构词
        reply = "阶段一：打好基础\n目标：掌握 MySQL\n任务清单：\n- 完成安装\n- 写完练习"
        assert parse_intent_from_reply(reply) == "generate_plan"

    def test_plan_by_keyword_plus_structure(self):
        reply = "这是你的学习计划：第一周目标如下，第 2 周继续推进"
        assert parse_intent_from_reply(reply) == "generate_plan"

    def test_resume_by_keyword_plus_structure(self):
        reply = "这是你的简历：\n教育背景：XX大学\n项目经历：商城系统"
        assert parse_intent_from_reply(reply) == "generate_resume"

    def test_plain_chat(self):
        assert parse_intent_from_reply("今天天气不错，适合学习") == "chat"

    def test_function_description_not_misjudged(self):
        # 仅描述功能、无结构内容，不应误判为 generate_plan
        reply = "我可以帮你制定学习规划，告诉我你的专业吧"
        assert parse_intent_from_reply(reply) == "chat"

    def test_closed_set(self):
        # intent 封闭集：只允许三个值
        for text in ["", "随便聊聊", "简历 教育背景", "阶段 目标 任务清单"]:
            assert parse_intent_from_reply(text) in {
                "generate_plan",
                "generate_resume",
                "chat",
            }


def test_intent_to_skill_mapping():
    assert INTENT_TO_SKILL == {"generate_plan": "plan", "generate_resume": "resume"}
