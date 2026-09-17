# 智途校园 - Agent 重构验证：PromptManager
"""覆盖 T02 验收：三技能渲染、缺省变量不炸、热加载（测试后还原 yaml）。"""
import os
from pathlib import Path

import pytest

from app.llm.prompt_manager import PromptManager, get_prompt_manager

SKILLS_DIR = Path(__file__).resolve().parents[2] / "app" / "skills"
CHAT_YAML = SKILLS_DIR / "chat" / "prompts" / "chat_system.yaml"


class TestRender:
    @pytest.mark.parametrize("skill_key", ["plan", "resume", "chat"])
    def test_three_skills_render(self, skill_key):
        pm = get_prompt_manager()
        out = pm.render(skill_key, {})
        assert isinstance(out, str) and len(out) > 100

    def test_render_with_context(self):
        # T02 验收原文用例
        pm = get_prompt_manager()
        out = pm.render("plan", {"user_name": "测试", "major": "软件工程"})
        assert "测试" in out
        assert "软件工程" in out
        assert "JSON" in out  # 输出格式段落仍在

    def test_missing_variables_no_crash(self):
        """未定义变量不炸：ChainableUndefined + default 兜底。"""
        pm = get_prompt_manager()
        out = pm.render("plan", {})
        assert "同学" in out      # user_name default
        assert "未填写" in out    # major default
        out2 = pm.render("resume", {"unknown_key": "x"})
        assert "同学" in out2
        out3 = pm.render("chat", None)
        assert "小途" in out3

    def test_unknown_skill_raises_keyerror(self):
        pm = get_prompt_manager()
        with pytest.raises(KeyError):
            pm.render("nonexistent_skill", {})

    def test_plan_output_format_fields(self):
        """T02 铁律 + QA Round 1 修复：plan prompt 输出为中文键 Coze 结构，
        与 chat.py._extract_plan_from_json 的识别字段（STAGE_FIELD_KEYS）一致。"""
        out = get_prompt_manager().render("plan", {})
        for field in ['"阶段名称"', '"总述说明"', '"目标"', '"任务清单"']:
            assert field in out, f"plan prompt 缺少输出字段 {field}"

    def test_resume_output_format_fields(self):
        """QA Round 1 修复：resume prompt 输出为中文键 Coze 结构，
        与 chat.py._extract_resume_from_json 的识别字段一致。"""
        out = get_prompt_manager().render("resume", {})
        for field in ['"基本信息"', '"教育背景"', '"专业技能"', '"项目经历"', '"证书与比赛"', '"自我评价"']:
            assert field in out, f"resume prompt 缺少输出字段 {field}"
        # 证书内层 key 必须与 _extract_resume_from_json 的机构字段识别集一致
        assert '"等级/颁发机构"' in out or '"等级 / 颁发机构"' in out, (
            "resume prompt 证书机构 key 与解析器识别集不一致"
        )


class TestHotReload:
    def test_hot_reload_and_restore(self):
        """修改 yaml 后下一次 render（不重启）生效；测试后必须还原。"""
        pm = PromptManager()  # 独立实例，避免污染全局单例
        original_bytes = CHAT_YAML.read_bytes()
        original_mtime = CHAT_YAML.stat().st_mtime
        marker = "QA_HOTRELOAD_MARKER_7f3d9a"

        before = pm.render("chat", {})
        assert marker not in before

        try:
            text = original_bytes.decode("utf-8")
            # 在 system_prompt 块标量内追加标记行（保持两级缩进，仍是合法 YAML）
            CHAT_YAML.write_text(text.rstrip("\n") + f"\n  # {marker}\n", encoding="utf-8")
            # 强制推进 mtime，避免文件系统时间戳粒度导致热加载漏检
            os.utime(CHAT_YAML, (original_mtime + 10, original_mtime + 10))

            after = pm.render("chat", {})
            assert marker in after, "热加载未生效：修改 yaml 后 render 未拿到新内容"
        finally:
            # 还原原文并恢复 mtime
            CHAT_YAML.write_bytes(original_bytes)
            os.utime(CHAT_YAML, (original_mtime + 20, original_mtime + 20))

        restored = pm.render("chat", {})
        assert marker not in restored, "yaml 还原后 render 仍含测试标记"
        # 最终把 mtime 恢复到接近原值（内容已逐字节还原）
        os.utime(CHAT_YAML, (original_mtime, original_mtime))
