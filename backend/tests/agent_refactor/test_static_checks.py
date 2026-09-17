# 智途校园 - Agent 重构验证：静态核查
"""静态核查（Round 3「整理与可移植化」后更新，并做 clone-safe 化）：

1. 【备份清场】第 1 轮重构产生的散落 `*.bak` 已全部归入隔离区
   `_cleanup_backup_20260917/removed/`（工作区内不再残留散落备份）；
   隔离区中对应备份**可寻址、未丢失**（改前原文保全）。—— 原「铁律 8：
   9 个 .bak 必须存在且与 HEAD 一致」在用户确认清理后翻转为「备份已清场且归档」。
   ⚠️ 隔离区被 `.gitignore` 忽略，**克隆仓库中不存在** → 相关用例自动 skip。
2. 【变更范围】git 跟踪文件的改动集必须**恰好**等于本轮（重构 W1–W6 + 清理）
   授权清单，无未授权改动、无遗漏。克隆/已提交态（工作区干净）自动 skip 遗漏校验。
3. 【零改动清单】下列从未被授权改动的文件，必须仍未被修改，且未被
   langchain/langgraph 等新框架引用污染。（`main.py` 因本轮 W4 合法改动了
   描述文案，已从零改动清单移出、改列授权改动；另补入同为零改动的
   `app/core/database.py` 以维持清单规模。）
4. 【.env 追加】`.env` 相对（隔离区中归档的）`.env.bak` 仅追加新键，原段保留。
   克隆仓库中二者均不存在 → 自动 skip。
5. 【DB schema】数据库 7 张表无 schema 变更（对比 docs/ai_learning_system.sql 基线）。
   DB 不可达（无 DB 的克隆机）→ 自动 skip，不报 error。

clone-safe 约定：依赖「本机迁移中间态」（隔离区 / 真实 .env / 脏工作区 / 本地 DB）
的用例在缺失前置时 **skip 而非 FAIL/ERROR**；安全相关断言（框架污染、表集合、
变更范围无未授权项等）**一律保留、不因跳过而削弱**。
"""
import re
import subprocess
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent

# 第 1 轮重构的 9 个修改文件（相对 backend/）——其 .bak 现已清场归档
MODIFIED_FILES = [
    "requirements.txt",
    ".env",
    "app/core/config.py",
    "app/agent/intent.py",
    "app/agent/tools/query_plans.py",
    "app/agent/tools/query_resumes.py",
    "app/agent/tools/query_profile.py",
    "app/agent/tools/query_points.py",
    "app/api/chat.py",
]

# 其中被 git 跟踪、可在隔离区回溯的 8 个（.env 被 gitignore，同样已归档）
TRACKED_MODIFIED = [f for f in MODIFIED_FILES if f != ".env"]

# 本轮（重构 + 整理/可移植化）git 跟踪文件的**授权改动集**（相对 backend/）。
# 含第 1 轮 8 个跟踪改文件 + 本轮 W1/W2/W4/W5 合法改动：
#   .gitignore(W1)、.env.example(W2)、main.py(W4 描述文案)、stop.bat(W5)
# 注：README.md 本轮新增但当前为 untracked（不进入 `git status -s` 的 " M " 集），故不在此列。
AUTHORIZED_MODIFIED = set(TRACKED_MODIFIED) | {
    ".gitignore",
    ".env.example",
    "main.py",
    "stop.bat",
}

# 从未被任何一轮授权改动的文件（须保持原样且不被新框架污染）。
# 原清单含 main.py；因本轮 W4 合法改动 main.py 描述文案，已移出并补入
# 同为零改动的 app/core/database.py，维持清单规模与原测试意图。
ZERO_CHANGE_FILES = [
    "app/services/coze_client.py",
    "app/services/ai_service.py",
    "app/agent/tools/base.py",
    "app/agent/tools/registry.py",
    "app/agent/tools/generate_plan.py",
    "app/agent/tools/generate_resume.py",
    "app/skills/base.py",
    "app/skills/registry.py",
    "app/skills/plan_skill.py",
    "app/skills/resume_skill.py",
    "app/skills/__init__.py",
    "app/core/database.py",
    "app/models/chat.py",
    "app/models/plan.py",
    "app/models/points.py",
    "app/models/resume.py",
    "app/models/user.py",
    "app/services/plan_service.py",
    "app/services/resume_service.py",
    "app/services/points_service.py",
    "app/services/profile_service.py",
    "app/services/auth_service.py",
    "app/services/ability_service.py",
    "app/services/email_service.py",
]

FORBIDDEN_IMPORT_RE = re.compile(
    r"langchain|langgraph|skill_engine|build_agent_graph|get_llm|prompt_manager",
    re.IGNORECASE,
)

# 改前备份隔离区（Round 3 由用户确认，29 项无用文件统一移入）。
# 该目录被 .gitignore 忽略，克隆仓库中不存在。
QUARANTINE_BACKEND = REPO_DIR / "_cleanup_backup_20260917" / "removed" / "backend"

# 视为「DB 不可达」的异常类名（含 sqlalchemy 包裹的 DBAPI/连接类错误）。
_DB_UNAVAILABLE_NAMES = {
    "OperationalError", "InterfaceError", "InternalError", "ProgrammingError",
    "DBAPIError", "SQLAlchemyError", "ModuleNotFoundError", "ImportError",
    "OSError", "ConnectionError", "ConnectionRefusedError", "TimeoutError",
}


def _is_db_unavailable(exc: BaseException) -> bool:
    """判断异常是否属于「DB 不可达 / 依赖缺失」类（用于 skip 而非 error）。"""
    return bool(
        _DB_UNAVAILABLE_NAMES & {c.__name__ for c in type(exc).__mro__}
    )


def _git(*args) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败: {result.stderr}")
    return result.stdout


class TestBakFiles:
    """Round 3：备份由「必须就地存在」翻转为「已清场归档」。"""

    @pytest.mark.parametrize("rel", MODIFIED_FILES)
    def test_bak_exists(self, rel):
        """散落备份必须已清场：backend/ 下不再残留 {rel}.bak。

        该断言不依赖隔离区，克隆仓库同样成立（克隆中本就不会有散落 .bak）。
        """
        bak = BACKEND_DIR / f"{rel}.bak"
        assert not bak.exists(), (
            f"工作区残留散落备份文件（应已归入隔离区）: {bak}"
        )

    @pytest.mark.parametrize("rel", TRACKED_MODIFIED)
    def test_bak_relocated_to_quarantine(self, rel):
        """改前原文未丢失：已归档至隔离区 `_cleanup_backup_*/removed/backend/`。

        隔离区被 .gitignore 忽略，**克隆仓库中不存在** → 本机迁移态护栏专用，
        克隆时 skip（不 FAIL）。
        """
        if not QUARANTINE_BACKEND.is_dir():
            pytest.skip("隔离区不在克隆仓库中（已被 .gitignore 忽略）")
        quarantined = QUARANTINE_BACKEND / f"{rel}.bak"
        assert quarantined.exists(), (
            f"改前备份未在隔离区归档，可能丢失: {quarantined}"
        )

    def test_env_only_additions(self):
        """T01：.env 相对（隔离区归档的）.env.bak 仅追加新键，原段保留。

        克隆仓库中 `.env` 与隔离区 `.env.bak` 均不存在 → 自动 skip。
        """
        archived_bak = QUARANTINE_BACKEND / ".env.bak"
        live_env = BACKEND_DIR / ".env"
        if not archived_bak.exists() or not live_env.exists():
            pytest.skip("克隆仓库缺少 .env / 隔离区 .env.bak，跳过迁移期追加校验")
        old_lines = archived_bak.read_text(encoding="utf-8").splitlines()
        new_text = live_env.read_text(encoding="utf-8")
        for line in old_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                assert stripped in new_text, f".env 丢失了原有配置行: {stripped}"
        for new_key in (
            "DEEPSEEK_API_KEY",
            "DEEPSEEK_MODEL",
            "DEEPSEEK_BASE_URL",
            "AGENT_BACKEND",
            "AGENT_MAX_ITER",
            "PROMPT_HOT_RELOAD",
        ):
            assert re.search(rf"^{new_key}=", new_text, re.MULTILINE), f".env 缺少新键 {new_key}"


class TestChangeScope:
    def test_git_modified_files_within_authorization(self):
        """变更范围：git 跟踪文件中仅本轮的授权改动集被修改。

        - 始终校验「无未授权改动」(unexpected) —— 安全护栏，克隆态同样有效。
        - 「遗漏」(missing) 仅在迁移期（工作区有改动）校验；克隆/已提交态
          （`modified == set()`）自动 skip，避免用户 `git add -A && git commit`
          后工作区变干净导致本用例 FAIL。
        """
        out = _git("status", "--short")
        modified = {
            line[3:].replace("backend/", "", 1)
            for line in out.splitlines()
            if line.startswith(" M ")
        }
        unexpected = modified - AUTHORIZED_MODIFIED
        assert not unexpected, f"未授权的文件被修改: {unexpected}"
        if not modified:
            pytest.skip("工作区干净（克隆/已提交态），跳过迁移期遗漏校验")
        missing = AUTHORIZED_MODIFIED - modified
        assert not missing, f"授权文件未被修改（可能遗漏任务）: {missing}"

    @pytest.mark.parametrize("rel", ZERO_CHANGE_FILES)
    def test_zero_change_files_unmodified_in_git(self, rel):
        out = _git("status", "--short", f"backend/{rel}")
        assert not out.strip(), f"零改动文件 {rel} 在 git 中存在变更: {out}"

    @pytest.mark.parametrize("rel", ZERO_CHANGE_FILES)
    def test_zero_change_files_no_new_framework_pollution(self, rel):
        path = BACKEND_DIR / rel
        if not path.exists():
            pytest.skip(f"{rel} 不存在")
        content = path.read_text(encoding="utf-8", errors="replace")
        match = FORBIDDEN_IMPORT_RE.search(content)
        assert match is None, (
            f"零改动文件 {rel} 被新框架引用污染: 命中 '{match.group()}'"
        )


class TestDatabaseSchema:
    """T05 验收：数据库 7 张表无 schema 变更（只读核查）。

    无 DB 的克隆机：连接类异常 → skip（不 error）。
    """

    EXPECTED_TABLES = {
        "users",
        "user_profiles",
        "learning_plans",
        "daily_tasks",
        "resumes",
        "points",
        "chat_messages",
    }

    async def _show_create_tables(self) -> dict[str, str]:
        from sqlalchemy import text

        from app.core.database import AsyncSessionLocal, engine

        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result.all()]
                schemas = {}
                for t in tables:
                    r = await db.execute(text(f"SHOW CREATE TABLE `{t}`"))
                    schemas[t] = r.one()[1]
                return schemas
        finally:
            await engine.dispose()

    async def _schemas_or_skip(self) -> dict[str, str]:
        try:
            return await self._show_create_tables()
        except Exception as exc:  # noqa: BLE001 — 仅将连接/依赖缺失类转为 skip
            if _is_db_unavailable(exc):
                pytest.skip(f"DB 不可达，跳过 schema 校验: {type(exc).__name__}")
            raise

    async def test_table_set_unchanged(self):
        schemas = await self._schemas_or_skip()
        assert set(schemas.keys()) == self.EXPECTED_TABLES, (
            f"表集合变更: 多出 {set(schemas) - self.EXPECTED_TABLES}, "
            f"缺少 {self.EXPECTED_TABLES - set(schemas)}"
        )

    async def test_columns_match_baseline(self):
        """列集合对比 docs/ai_learning_system.sql 基线
        （conversation_id 为改造前已存在的迁移，允许）。"""
        baseline_sql = (REPO_DIR / "docs" / "ai_learning_system.sql").read_text(
            encoding="utf-8", errors="replace"
        )
        baseline_columns: dict[str, set[str]] = {}
        for m in re.finditer(
            r"CREATE TABLE `(\w+)`\s*\((.*?)\) ENGINE", baseline_sql, re.DOTALL
        ):
            table, body = m.group(1), m.group(2)
            cols = set(re.findall(r"^\s*`(\w+)`", body, re.MULTILINE))
            baseline_columns[table] = cols

        schemas = await self._schemas_or_skip()
        # 改造前已存在的会话分组迁移
        allowed_extra = {"chat_messages": {"conversation_id"}}
        for table, create_sql in schemas.items():
            live_cols = set(re.findall(r"^\s*`(\w+)`", create_sql, re.MULTILINE))
            base_cols = baseline_columns.get(table, set())
            extra = live_cols - base_cols - allowed_extra.get(table, set())
            missing = base_cols - live_cols
            assert not extra and not missing, (
                f"表 {table} schema 变更: 新增列 {extra}, 缺失列 {missing}"
            )
