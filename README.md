# 智途校园（AI Learning System）

> 大学生 AI 成长服务平台 —— AI 助手「小途」驱动的「学习规划 / 简历生成 / 个人画像 / 积分成长」一站式应用。

智途校园面向高校学生，提供由大模型智能体驱动的个性化学习规划与求职简历服务，并通过积分体系激励持续成长。后端为 FastAPI 服务，内置**本地 LangChain / LangGraph 智能体**（默认对接 DeepSeek，工具调用 + 技能插件 + Prompt 热加载），前端为原生 HTML/CSS/JS 单页应用。

> 仓库内另有 [`AGENTS.md`](./AGENTS.md)（面向开发者的架构细节与注意事项）。README 是**上手第一步**，AGENTS.md 为补充。

---

## 1. 技术栈

| 层 | 技术 |
| --- | --- |
| Web 框架 | FastAPI 0.115 + Uvicorn（ASGI） |
| ORM / 数据库 | SQLAlchemy 2.0（async）+ aiomysql + MySQL 8.0 |
| 鉴权 | python-jose（JWT）+ passlib[bcrypt] |
| 智能体 | LangChain 0.3 + LangGraph 0.2（本地图式 Agent） |
| 大模型 | DeepSeek（OpenAI 兼容 API，默认）；Coze 扣子 / 通义千问为可选通道 |
| Prompt | PyYAML + Jinja2（沙箱渲染 + mtime 热加载） |
| 前端 | 原生 HTML / CSS / JS SPA（hash 路由），由后端 `static/` 托管 |
| 配置 | pydantic-settings（`.env`） |

---

## 2. 目录结构

```
ai_learning_system/
├─ backend/
│  ├─ main.py                # FastAPI 入口：注册 7 个路由 + 静态文件 + SPA 回退
│  ├─ start.bat / stop.bat   # Windows 启停脚本
│  ├─ requirements.txt       # 依赖清单
│  ├─ .env.example           # 环境变量模板（复制为 .env 使用）
│  ├─ app/
│  │  ├─ api/        # 路由层：各业务 HTTP 端点（auth/profile/points/plans/resumes/chat/abilities）
│  │  ├─ services/   # 业务层：与每个 API 对应的 Service 类
│  │  ├─ models/     # 数据层：SQLAlchemy 模型（User/UserProfile/LearningPlan/DailyTask/Resume/Point/ChatMessage）
│  │  ├─ schemas/    # 契约层：Pydantic 请求/响应模型
│  │  ├─ core/       # 基础设施：config(.env) / database(AsyncSession) / security(JWT,bcrypt) / deps(依赖注入)
│  │  ├─ llm/        # LLM 工程化层：model_config(采样参数) / llm_provider(ChatOpenAI) / llm_harness(校验+重试+护栏) / prompt_manager(YAML 热加载)
│  │  ├─ agent/      # LangGraph 智能体：graph(图工厂) / node_*(节点) / state(状态) / tools(工具与工厂)
│  │  ├─ skills/     # 技能插件：SkillEngine + 各技能目录（prompt YAML + 技能定义）
│  │  └─ mcpserver/  # 外部 MCP Server 注册表（骨架，默认不启用）
│  ├─ static/        # 前端静态资源（index.html + css/js），SPA 模式
│  ├─ tests/         # 测试（tests/agent_refactor/ 为 Agent 重构验证用例）
│  └─ migrations/    # 手动数据库迁移脚本
└─ docs/
   ├─ ai_learning_system.sql          # MySQL 建表脚本（表结构，见下）
   └─ migration_add_conversation_id.sql # 迁移：为 chat_messages 增加 conversation_id
```

---

## 3. 快速开始（Windows）

> 前置：Windows 10/11、已安装 MySQL 8.0、已安装 Python 3.13（本项目基于 Python 3.13.12 开发）。

### 3.1 创建虚拟环境并安装依赖

```bat
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

- `requirements.txt` 已锁定兼容版本线（LangChain 0.3.x / pydantic 2.9 / websockets 14.x）。
- **测试依赖需单独安装**：`requirements.txt` 中**不含** pytest，跑测试前请额外执行：
  ```bat
  venv\Scripts\pip install pytest pytest-asyncio requests
  ```

### 3.2 准备数据库

1. 启动 MySQL，创建数据库：
   ```sql
   CREATE DATABASE ai_learning_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
2. 导入建表脚本（如用命令行）。注意：上一步 §3.1 已 `cd backend`，当前工作目录是 `backend/`，因此用 `..\docs\` 回到上一级的 `docs/`：
   ```bat
   mysql -u root -p ai_learning_system < ..\docs\ai_learning_system.sql
   ```
   > ℹ️ 若你当前在**项目根目录**执行，则路径改为 `docs\ai_learning_system.sql`。
   > ⚠️ **该 SQL 仅包含 7 张表的表结构，不含 `CREATE DATABASE`，也不含任何初始/种子数据**；且脚本开头是 `DROP TABLE IF EXISTS`，**导入会清空同名表**。首次搭建时请先手动建库，再导入。
   > 若表结构后续有变动（如新增 `conversation_id`），再执行 `docs/migration_add_conversation_id.sql`。

### 3.3 配置环境变量

```bat
cd backend
copy .env.example .env
```

用编辑器打开 `backend\.env`，至少填写 **`DEEPSEEK_API_KEY`**（去 [platform.deepseek.com](https://platform.deepseek.com) 申请；模型名以平台实际可用 ID 为准，默认 `deepseek-flash`，另可能有 `deepseek-v4-pro`）。数据库账号密码等按实际情况调整即可。

### 3.4 启动服务

```bat
cd backend
start.bat
```

启动后访问：

- 应用首页：<http://localhost:8000>
- 健康检查：<http://localhost:8000/api/health>
- Swagger 文档：<http://localhost:8000/docs>

停止服务：双击 `backend\stop.bat`（**仅停止占用 8000 端口的 uvicorn 进程**，不会误杀其它 python 进程）。

手动启动（等价方式）：

```bat
venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3.5 运行测试

**必须以 `backend/` 为工作目录运行**（`.env` 相对路径解析依赖 cwd）：

```bat
cd backend
venv\Scripts\python.exe -m pytest tests/agent_refactor
```

> 若提示 `No module named pytest`，先执行 `venv\Scripts\pip install pytest pytest-asyncio requests`（见 3.1）。
> 部分用例会启动真实 uvicorn 子进程，请确保 8000/8123/8125 等端口空闲。

---

## 4. 环境变量说明

| 变量 | 是否必填 | 说明 |
| --- | --- | --- |
| `DB_HOST` | 必填 | MySQL 主机，默认 `127.0.0.1` |
| `DB_PORT` | 必填 | MySQL 端口，默认 `3306` |
| `DB_USER` | 必填 | 数据库用户，默认 `root` |
| `DB_PASSWORD` | 必填 | 数据库密码 |
| `DB_NAME` | 必填 | 数据库名，默认 `ai_learning_system` |
| `JWT_SECRET_KEY` | 必填 | JWT 签名密钥，生产务必替换为随机长串 |
| `JWT_ALGORITHM` | 可选 | 签名算法，默认 `HS256` |
| `JWT_EXPIRE_HOURS` | 可选 | token 有效期（小时），默认 `168` |
| `DEEPSEEK_API_KEY` | **必填** | 本地 Agent 默认 LLM 的密钥（langgraph 通道必需） |
| `DEEPSEEK_MODEL` | 可选 | 模型 ID，默认 `deepseek-flash`（以平台实际为准） |
| `DEEPSEEK_BASE_URL` | 可选 | DeepSeek OpenAI 兼容端点，默认 `https://api.deepseek.com/v1` |
| `AGENT_BACKEND` | 可选 | Agent 通道：`langgraph`（默认）/ `coze` |
| `AGENT_MAX_ITER` | 可选 | LangGraph 工具循环最大轮数（防死循环），默认 `8` |
| `PROMPT_HOT_RELOAD` | 可选 | 技能 YAML prompt 热加载，默认 `true` |
| `LLM_TEMPERATURE` | 可选 | 采样温度，默认 `0.7` |
| `LLM_MAX_TOKENS` | 可选 | 单次最大输出 token，默认 `4096` |
| `COZE_PAT` | 可选 | 扣子 Coze 访问令牌（仅 `AGENT_BACKEND=coze` 时必需） |
| `COZE_BOT_ID` | 可选 | 扣子 Coze 机器人 ID（仅 `AGENT_BACKEND=coze` 时必需） |
| `QWEN_API_KEY` | 可选 | 通义千问备用 key（本期不自动启用） |
| `QWEN_MODEL` | 可选 | 通义千问模型，默认 `qwen3.5-flash` |
| `QWEN_BASE_URL` | 可选 | 通义千问兼容端点 |
| `SMTP_HOST` | 可选 | 邮件服务器（注册验证码等功能需要） |
| `SMTP_PORT` | 可选 | 邮件端口，默认 `465` |
| `SMTP_USER` | 可选 | 发件邮箱 |
| `SMTP_PASSWORD` | 可选 | 邮箱 SMTP 授权码（非登录密码） |

---

## 5. Agent 架构与扩展

本地智能体采用「**规范层（Harness）+ 技能（Skill）+ 工具工厂（Tool Factory）**」的分层设计，核心入口为 `POST /api/chat`（SSE 流式）。

### 5.1 请求处理链路

1. **意图路由**：`agent/intent.py` 关键词匹配 → `SkillEngine.route(intent)` 选择技能（`plan` / `resume` / `chat`，默认兜底 `chat`）。
2. **装配**：`SkillEngine.get_tools(skill, ctx)` 按技能的 `allowed_tools` 从 `toolkit.TOOL_FACTORIES` 装配 LangChain `StructuredTool`（请求级依赖 `ToolContext(db, user_id)` 经闭包绑定，**不进入 AgentState**）。
3. **构图**：`agent/graph.build_agent_graph()` 组装 `call_model ⟷ execute_tool → respond` 的 LangGraph，`AGENT_MAX_ITER` 限制工具轮数以防死循环。
4. **调用**：`llm/llm_harness.LLMHarness.invoke()` 统一包装——输入校验 → 指数退避重试 → 输出护栏（剥离 `<think>` 标签）→ trace 日志。
5. **流式输出**：`chat.py` 以 `astream_events(v2)` 向前端推送 SSE 增量。

### 5.2 如何扩展（重点）

**① 新增一个技能（Skill）**

1. 新建目录 `backend/app/skills/<name>/`，并在其中创建：
   - `__init__.py`：导出技能类；
   - `<name>_skill.py`：继承 `skills.skill_engine.SkillBase`，声明类属性 `key` / `prompt_skill` / `allowed_tools` / `intents`；
   - `prompts/<name>_system.yaml`：`name` / `version` / `system_prompt`（支持 Jinja2 变量注入用户画像）。
2. 在 `skills/skill_engine.py` 的 `SkillEngine.__init__` 中 import 并 `self.register(YourSkill())`。
3. （如需新工具）在 `agent/tools/` 下实现工具并在 `toolkit.TOOL_FACTORIES` 注册工厂，再把工具名加入该技能的 `allowed_tools`。

**② 修改 Prompt（免重启）**

- 直接编辑 `backend/app/skills/<name>/prompts/<name>_system.yaml`。
- `PROMPT_HOT_RELOAD=true` 时，`prompt_manager` 在每次渲染前比对文件 mtime，**改动后无需重启服务即生效**（控制台会打印「热加载 prompt」日志）。

**③ 接入外部 MCP Server**

- 在 `backend/app/mcpserver/registry.py` 的 `MCP_SERVERS` 字典中追加声明式配置（文件中已给出 `stdio` 与 `streamable_http` 两种示例）；
- `stdio` 形式的 `command` 请使用 `sys.executable`（Windows 下勿写死 `python`）；
- 加载逻辑由 `agent/tools/mcp_tools.py` 统一处理，未注册任何 server 时为零开销空列表。

### 5.3 关键约束

- 工具依赖（db / user_id）永不写入 `AgentState`，只经 `ToolContext` 闭包注入，保证 state 可序列化。
- LLM 调用一律走 `LLMHarness`，禁止绕过（校验/重试/护栏/日志都在此层）。
- 采样参数集中在 `llm/model_config.py`，**禁止硬编码**，一律来自 `get_settings()`。

---

## 6. 切回 Coze 远程智能体（回退通道）

默认使用本地 `langgraph` 智能体。若需切回扣子 Coze：

```env
# backend/.env
AGENT_BACKEND=coze
COZE_PAT=<有效的扣子令牌>
COZE_BOT_ID=<扣子机器人 ID>
```

> Coze 回退要求 `COZE_PAT` 有效；令牌无效时该通道不可用，请保持 `AGENT_BACKEND=langgraph` 使用本地智能体。

---

## 7. 常见问题（FAQ）

| 现象 | 排查方向 |
| --- | --- |
| 启动报端口占用（`error while attempting to bind ... 8000`） | 8000 端口被占用；先运行 `stop.bat`，或改用 `--port` 指定其它端口 |
| 对话返回 **400** 错误 | 多为 `DEEPSEEK_MODEL` 非法（模型名须与平台实际 ID 完全一致）；检查 `.env` 中的模型名 |
| 启动报 `DEEPSEEK_API_KEY 未配置` | `.env` 中 `DEEPSEEK_API_KEY` 为空；填写后重启 |
| 数据库连接失败 / `Can't connect to MySQL server` | MySQL 未启动、账号密码错误或库未创建；核对 `.env` 的 `DB_*` 并确认已建库导入 SQL |
| 页面 404 / 白屏 | 确认 `backend/static/index.html` 存在（SPA 回退依赖它） |
| 测试报 `No module named pytest` | 未安装测试依赖：`venv\Scripts\pip install pytest pytest-asyncio requests` |
| 中文控制台乱码 | 脚本已 `chcp 65001`；手动运行时可在 cmd 执行 `chcp 65001` |

---

## 8. 其他说明

- **无迁移框架**：建表与迁移均为手动 SQL，见 `docs/*.sql` 与 `backend/migrations/`。
- **凭据安全**：`.env` / `*.bak` / `api.txt` 等含密钥的文件均已在 `.gitignore` 中忽略，请勿提交。
- **前端**：无构建步骤，直接由后端 `static/` 目录托管，采用 hash 路由。
