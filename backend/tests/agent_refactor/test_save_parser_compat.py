# 智途校园 - Agent 重构验证：技能 YAML 输出格式 ↔ save-plan/save-resume 解析兼容性
"""T05 验收前置：新通道下主模型按 plan/resume YAML 直出 JSON 后，
/chat/save-plan、/chat/save-resume 的 _extract_* 必须能解析（附录 C.2）。

QA Round 1 结论（已修复）：YAML 输出段落曾沿用旧进程内技能的英文键结构，
与 _extract_plan_from_json / _extract_resume_from_json 的中文键解析不兼容，
导致 save-plan 兜底保存空规划、save-resume 结构化字段全空。
修复（2026-09-16）：两份 YAML 输出格式段落已改为中文键 Coze 结构，
_extract_* 零改动。本文件的 mock 同步改为新中文键结构，原 xfail 转 PASS。
"""
import json

from app.api.chat import _extract_plan_from_json, _extract_resume_from_json

# 严格按 plan_system.yaml（v2）「输出要求」段落构造的模型输出（中文键格式 A）
YAML_CONFORMANT_PLAN = json.dumps(
    {
        "大数据技术3年进阶规划": {
            "阶段一": {
                "阶段名称": "基础打牢期",
                "总述说明": "夯实基础",
                "目标": ["目标1", "目标2"],
                "任务清单": ["第一天的具体任务", "第二天的具体任务", "第三天的具体任务"],
            },
            "阶段二": {
                "阶段名称": "进阶提升期",
                "总述说明": "项目实战",
                "目标": ["目标3"],
                "任务清单": ["第四天的具体任务", "第五天的具体任务"],
            },
        }
    },
    ensure_ascii=False,
)

# 严格按 resume_system.yaml（v2）「输出要求」段落构造的模型输出（中文键结构）
YAML_CONFORMANT_RESUME = json.dumps(
    {
        "求职简历": {
            "基本信息": {
                "姓名": "张三",
                "学校": "XX大学",
                "专业": "软件工程",
                "学历": "本科",
                "求职意向": "数据分析师",
                "联系方式": "13800000000",
            },
            "教育背景": [
                {"学校": "XX大学", "专业": "软件工程", "学历": "本科", "时间": "2023.09-2027.06"}
            ],
            "专业技能": ["Python", "SQL"],
            "项目经历": [
                {
                    "名称": "商城系统",
                    "角色": "项目负责人",
                    "时间": "3个月",
                    "描述": "项目描述",
                    "成果": "项目成果",
                }
            ],
            "证书与比赛": [
                {"名称": "CET-4", "等级/颁发机构": "教育部", "时间": "2024.06"}
            ],
            "自我评价": "个人优势总结",
        }
    },
    ensure_ascii=False,
)


def test_plan_yaml_output_parseable_by_save_plan():
    """plan YAML（中文键格式 A）规定的输出必须可被 save-plan 解析（原 xfail，修复后转 PASS）。"""
    result = _extract_plan_from_json(YAML_CONFORMANT_PLAN)
    assert result is not None, "save-plan 无法解析 plan YAML 规定的输出格式"
    assert result["title"] == "大数据技术3年进阶规划"
    assert result["daily_tasks"] == [
        "第一天的具体任务", "第二天的具体任务", "第三天的具体任务",
        "第四天的具体任务", "第五天的具体任务",
    ], "解析结果丢失 daily_tasks（每日任务将为空）"
    assert len(result["stages"]) == 2, "解析结果丢失 stages"


def test_resume_yaml_output_parseable_by_save_resume():
    """resume YAML（中文键结构）规定的输出必须可被 save-resume 解析（原 xfail，修复后转 PASS）。"""
    result = _extract_resume_from_json(YAML_CONFORMANT_RESUME)
    assert result is not None, "save-resume 无法解析 resume YAML 规定的输出格式"
    assert result["basic"].get("姓名") == "张三", "解析结果丢失基本信息"
    assert result["skills"] == ["Python", "SQL"]
    assert result["experience"][0]["名称"] == "商城系统"
    assert result["certs"][0]["名称"] == "CET-4"
    assert result["summary"] == "个人优势总结"


def test_coze_chinese_format_still_parseable():
    """回归保护：Coze 中文键格式解析能力不受影响（_extract_* 零改动）。"""
    coze_plan = json.dumps(
        {
            "MySQL学习规划": {
                "阶段一": {
                    "阶段名称": "基础",
                    "总述说明": "说明",
                    "目标": ["掌握安装"],
                    "任务清单": ["完成安装", "写完练习"],
                }
            }
        },
        ensure_ascii=False,
    )
    result = _extract_plan_from_json(coze_plan)
    assert result is not None
    assert result["title"] == "MySQL学习规划"
    assert result["daily_tasks"] == ["完成安装", "写完练习"]

    coze_resume = json.dumps(
        {
            "求职简历": {
                "基本信息": {"姓名": "张三", "学校": "XX大学"},
                "专业技能": ["Python"],
                "项目经历": [{"名称": "商城"}],
            }
        },
        ensure_ascii=False,
    )
    result = _extract_resume_from_json(coze_resume)
    assert result is not None
    assert result["basic"]["姓名"] == "张三"
