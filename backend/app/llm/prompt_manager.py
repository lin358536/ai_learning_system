# 智途校园 - Prompt 统一管理器（YAML + jinja2）
"""扫描 app/skills/*/prompts/*.yaml，sandbox 渲染，mtime 热加载。"""
import time
from pathlib import Path

import yaml
from jinja2 import ChainableUndefined
from jinja2.sandbox import ImmutableSandboxedEnvironment  # jinja2 3.1.6 起需从 sandbox 子模块导入

from app.core.config import get_settings


class PromptManager:
    """
    技能 prompt 统一管理。

    - 启动时扫描 app/skills/<skill>/prompts/*.yaml，以目录名作为 skill_key 注册；
    - YAML 结构：{name: str, version: str|int, system_prompt: str}；
    - 渲染使用 ImmutableSandboxedEnvironment + ChainableUndefined（变量缺失不抛 KeyError）；
    - PROMPT_HOT_RELOAD=true 时每次 render 前比对 mtime，变更自动重载（改 prompt 免重启）。
    """

    def __init__(self, base_dir: str | Path | None = None):
        # 默认扫描 app/skills/（本文件位于 app/llm/ 下）
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent.parent / "skills"
        self._base_dir = Path(base_dir)
        # 沙箱环境：禁用危险语法；ChainableUndefined：缺变量链式访问不炸，渲染为空串
        self._env = ImmutableSandboxedEnvironment(
            undefined=ChainableUndefined,
            keep_trailing_newline=True,
        )
        # skill_key -> {"path": Path, "mtime": float, "raw": str, "name": str, "version": str}
        self._prompts: dict[str, dict] = {}
        self.reload()

    # ── 加载 ────────────────────────────────────────────────────

    def reload(self) -> None:
        """全量重新扫描 prompt 目录。"""
        self._prompts.clear()
        if not self._base_dir.exists():
            print(f"[zhitu][prompt] 技能 prompt 目录不存在: {self._base_dir}")
            return

        for yaml_path in sorted(self._base_dir.glob("*/prompts/*.yaml")):
            skill_key = yaml_path.parent.parent.name  # .../<skill>/prompts/xx.yaml → <skill>
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                system_prompt = data.get("system_prompt", "")
                if not system_prompt:
                    print(f"[zhitu][prompt] 跳过空 prompt 文件: {yaml_path}")
                    continue
                self._prompts[skill_key] = {
                    "path": yaml_path,
                    "mtime": yaml_path.stat().st_mtime,
                    "raw": system_prompt,
                    "name": str(data.get("name", skill_key)),
                    "version": str(data.get("version", "1")),
                }
            except Exception as e:
                print(f"[zhitu][prompt] 加载 prompt 失败 {yaml_path}: {e}")

        print(
            f"[zhitu][prompt] 已加载 {len(self._prompts)} 个技能 prompt: "
            f"{', '.join(self._prompts.keys())}"
        )

    def _maybe_hot_reload(self, skill_key: str) -> None:
        """热加载检查：文件 mtime 变化时重新读取该文件（不重启进程）。"""
        if not get_settings().PROMPT_HOT_RELOAD:
            return
        info = self._prompts.get(skill_key)
        if info is None:
            return
        try:
            mtime = info["path"].stat().st_mtime
            if mtime > info["mtime"]:
                with open(info["path"], "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                system_prompt = data.get("system_prompt", "")
                if system_prompt:
                    self._prompts[skill_key].update({
                        "mtime": mtime,
                        "raw": system_prompt,
                        "name": str(data.get("name", skill_key)),
                        "version": str(data.get("version", info["version"])),
                    })
                    print(f"[zhitu][prompt] 热加载 prompt: {skill_key} (v{self._prompts[skill_key]['version']})")
        except FileNotFoundError:
            print(f"[zhitu][prompt] prompt 文件被删除: {info['path']}，继续使用缓存版本")
        except Exception as e:
            print(f"[zhitu][prompt] 热加载失败 {skill_key}: {e}，继续使用缓存版本")

    # ── 渲染 ────────────────────────────────────────────────────

    def render(self, skill_key: str, context: dict | None = None) -> str:
        """
        渲染指定技能的 system prompt。

        Args:
            skill_key: 技能 key（plan / resume / chat，即技能目录名）
            context: jinja2 渲染上下文（如用户画像变量），缺失变量渲染为空串

        Returns:
            渲染后的完整 system prompt 字符串

        Raises:
            KeyError: 技能未注册时抛出（调用方应保证 skill_key 来自 SkillEngine）
        """
        if skill_key not in self._prompts:
            self.reload()  # 允许运行期新增技能目录后无需重启
        info = self._prompts.get(skill_key)
        if info is None:
            raise KeyError(f"[zhitu][prompt] 未注册的技能 prompt: {skill_key}")

        self._maybe_hot_reload(skill_key)

        template = self._env.from_string(info["raw"])
        return template.render(**(context or {}))

    def get_version(self, skill_key: str) -> str:
        """获取技能 prompt 版本号（观测用）。"""
        info = self._prompts.get(skill_key)
        return info["version"] if info else "unknown"


# 模块级懒加载单例
_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    """获取 PromptManager 懒加载单例。"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
