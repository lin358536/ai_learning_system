# AGENTS.md — 智途校园 (AI Learning System)

## 快速起步

```bash
cd backend
venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
# 或: start.bat (后台启动); stop.bat (taskkill /f /im python.exe)
# Swagger: http://localhost:8000/docs
```

依赖: `requirements.txt` (FastAPI, SQLAlchemy+aiomysql, python-jose, cozepy, httpx)
无 `pyproject.toml` / `setup.py` — 纯 `requirements.txt` 管理依赖。

## 项目结构

```
backend/
  main.py               # FastAPI 入口，注册 7 个 router + 静态文件 + SPA fallback
  app/
    api/                 # 路由层: auth, profile, points, plans, resumes, chat, abilities
    services/            # 业务层: 每个 API 对应一个 Service 类
    models/              # SQLAlchemy 模型: User, UserProfile, LearningPlan, DailyTask, Resume, Point, ChatMessage
    schemas/             # Pydantic 请求/响应模型
    core/                # config (pydantic-settings .env), database (AsyncSession), security (JWT/bcrypt), deps (get_current_user)
    agent/               # 工具系统: ToolRegistry + 6 个 BaseTool 子类 + intent 路由
    skills/              # 技能系统: SkillRegistry + 2 个 BaseSkill (定义 system prompt，但实际未被 Coze 流程使用)
    api_backup/          # 旧版文件，可忽略
    models_backup/       # 旧版文件，可忽略
  static/                # 前端静态文件 (HTML/CSS/JS)，SPA 模式
  migrations/            # 手动数据库迁移脚本
docs/
  ai_learning_system.sql # 完整 MySQL 建表脚本
```

## 关键架构事实

### API 约定
- 成功: `{"success": true, "data": {...}}`
- 错误: `{"success": false, "error": {"code": "UNAUTHORIZED", "message": "..."}}` (通过 HTTPException + status code)
- 认证: JWT Bearer token via `HTTPBearer`, 由 `deps.get_current_user` 注入
- 数据库: `deps.get_db` 注入 AsyncSession, 请求结束时自动 commit/rollback

### AI 对话流程
1. 前端 POST `/api/chat` (SSE `text/event-stream`) → 服务端拼装用户画像 + 历史 → 调用 Coze SDK 流式响应
2. Coze 回复结束后 `_parse_intent()` 从全文识别意图: `chat` / `generate_plan` / `generate_resume`
3. 前端收到 `done` 事件后，再调用 `/api/chat/save-plan` 或 `/api/chat/save-resume` 保存结构化数据
4. 对话历史在本地 `chat_messages` 表中持久化，按 `conversation_id` (UUID) 分组

### AI 后端双通道
- **主: Coze (扣子)** — 生产使用，`cozepy` SDK, 线程+队列包装为异步流式。Config: `COZE_PAT` + `COZE_BOT_ID`
- **备: 通义千问** — `AiService` 类封装，可通过 httpx 调用，当前未被实际聊天流程使用。Config: `QWEN_API_KEY` + `QWEN_MODEL`
- Coze 的 `conversation_id` 在 `_user_conversations` 字典中**进程内缓存**，重启后丢失

### 技能系统 vs 工具系统
- `agent/tools/`: 6 个工具 (GeneratePlan, GenerateResume, QueryPlans, QueryResumes, QueryProfile, QueryPoints) 通过 `ToolRegistry` 注册，用于意图识别
- `skills/`: `PlanSkill` 和 `ResumeSkill` 定义了结构化 JSON 输出的 system prompt，但**并未被实际聊天流程引用** — Coze 自身的 prompt 才是生效的
- 意图识别: `intent.py` 关键词匹配优先 → 工具描述模糊匹配回退

### 积分逻辑
- 完成任务: +5 (首次完成, `task_complete` source, 有去重检查)
- 创建规划: +20 (`plan` source)
- 生成简历: +15 (`resume` source)

### 数据库
- MySQL 8.0, 驱动 `aiomysql`, SQLAlchemy 2.0 async
- 7 张表: users, user_profiles, learning_plans, daily_tasks, resumes, points, chat_messages
- `skills` / `certificates` 以 JSON 字符串存在 `user_profiles` 的 `Text` 列中 (非 JSON 列)
- `content` 在 `learning_plans` 和 `resumes` 中也是 JSON 字符串存于 `Text` 列
- 无迁移框架；建表 SQL 在 `docs/ai_learning_system.sql`，手动迁移脚本在 `backend/migrations/`
- 注册/登录时自动创建 `user_profiles` 行（默认字段值）

## 开发注意事项

- **无测试 / 无 CI / 无 lint** — 仓库无测试套件、无 pytest 配置、无 ruff/flake8/mypy
- `.env` 中的凭据已提交到 git（虽然 `.env` 在 `.gitignore` 中）
- 编辑 `chat.py` (850 行) 时注意 `_extract_plan_from_json` 和 `_extract_resume_from_json` 与 Coze 实际输出格式的兼容性
- 所有 import 使用绝对路径如 `from app.core.config import get_settings`
- FastAPI router 注册使用两种风格: `prefix="/auth"` 和 `tags=["认证"]`；部分路由 (abilities, plans) 有 prefix，部分无
- 添加新 API 端点需: 创建路由文件 → 创建 Service → 创建 Model (如需) → `main.py` include_router
