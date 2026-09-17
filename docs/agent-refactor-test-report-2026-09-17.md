# 智途校园 · LangChain Agent 重构 — 真实 DeepSeek 密钥端到端验证报告

- **报告人**：严过关（software-qa-engineer / QA）
- **日期**：2026-09-17
- **被测版本**：昨日（2026-09-16）完成的本地 LangGraph Agent 重构（Coze → LangChain/LangGraph）
- **任务来源**：`docs/agent-refactor-tasks.md` 附录 C「待填 key 验证清单」+ T01/T04/T05 验收标准
- **测试性质**：**只测不修**。本轮未修改任何源码（`app/`、`requirements.txt`、`.env` 均未改动）。新增脚本仅落在 `backend/_qa_verify/`（非源码）。
- **总体结论**：⚠️ **不通过（1 个高危 + 1 个中危 + 1 个非确定性中危）**。核心链路（工具调用 / 流式 / SSE 三事件 / 落库 / 积分）可用，但 **（P1）当前 `.env` 配置的模型 ID 非法导致全部真实 LLM 调用 400 失败**；**（P2）`done` 事件 `intent` 恒为 `chat`**（源码 Bug，已定位到 `chat.py:235`）。

---

## 一、测试环境与配置快照

| 项 | 值 |
|---|---|
| 库/框架 | Python 3.13.14（backend/venv）；FastAPI 0.115.0；SQLAlchemy 2.0.35；aiomysql 0.2.0 |
| LLM 依赖 | langchain 0.3.30；langchain-core **0.3.86**；langchain-openai 0.3.35；langgraph 0.2.76；openai 2.54.0；httpx 0.28.1 |
| pydantic | 2.9.0 / pydantic-settings 2.5.2 |
| `DEEPSEEK_MODEL` | **`deepseek-v4.1-flash`**（`.env` / `app/core/config.py:39` 默认值） |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` |
| `DEEPSEEK_API_KEY` | **已配置**（len=35，前缀 `sk-`；本报告不记录明文） |
| `AGENT_BACKEND` | `langgraph` |
| 其他配置 | `AGENT_MAX_ITER=8`、`PROMPT_HOT_RELOAD=true`、`LLM_TEMPERATURE=0.7`、`LLM_MAX_TOKENS=4096` |
| 数据库 | MySQL 本地 `127.0.0.1:3306` 库 `ai_learning_system`（全程只读核对，未改 schema） |
| 测试用户 | `user_id=3`（username=admin，name=lilolr；画像：大数据技术/大二/目标 agent 开发工程师） |
| **HTTP 代理** | shell 注入 `HTTP_PROXY=HTTPS_PROXY=http://127.0.0.1:64025`（已做「继承 / 剥离」对照，见 §2.4） |

> 说明：因 P1（模型 ID 非法）会阻断一切 LLM 调用，为把「其余链路」测通，T04/T05 验证时通过**环境变量覆盖** `DEEPSEEK_MODEL=deepseek-flash`（环境变量优先于 `.env`，**未改任何文件**）。报告中已明确区分「按 `.env` 原样」与「覆盖为合法模型」两种结论。

---

## 二、逐项结果表

### 2.1 全量回归基线（`backend/tests/agent_refactor`，186 用例）

`venv/Scripts/python.exe -m pytest tests/agent_refactor` → **183 passed / 3 failed**（19.05s）

| 用例 | 预期 | 实际 | 结论 |
|---|---|---|---|
| 其余 183 个用例 | 通过 | 通过 | **PASS** |
| `test_imports.py::test_get_llm_empty_key_raises_zhitu_error` | `DEEPSEEK_API_KEY == ""` | 断言失败：key 已填入 | **FAIL（测试前置过期，非源码 Bug）** |
| `test_graph.py::TestGraphRuntime::test_empty_key_error_propagates` | 空 key 抛 `[zhitu]` 错误 | 断言失败：key 已填入 | **FAIL（测试前置过期）** |
| `test_api_langgraph.py::TestChatEmptyKey::test_chat_returns_error_event_not_500` | error.message 含 `DEEPSEEK_API_KEY` | 现返回非法模型 400 错误信息 | **FAIL（测试前置过期）** |

> 结论：基线整体仍绿（98.4%）。3 个失败均为「空 key 前置条件」用例在填入真实 key 后失效，**非源码缺陷**；建议后续改用 `monkeypatch` 注入空 key 而非依赖真实 `.env`。

### 2.2 T01 冒烟 + 模型可用性（附录 C 第 1、5 项）

| 用例 | 预期 | 实际 | 结论 |
|---|---|---|---|
| T01-1 `get_llm().ainvoke("你好")`（`deepseek-v4.1-flash`，继承代理） | 返回中文回复 | `openai.BadRequestError 400`：`The supported API model names are deepseek-flash, deepseek-v4-pro, but you passed deepseek-v4.1-flash.` | **FAIL** |
| T01-2 同上（剥离代理） | 返回中文回复 | 同样的 400 非法模型错误 | **FAIL** |
| T01-3 覆盖为 `deepseek-flash`（继承代理） | 返回中文回复 | ✅ `'你好！很高兴见到你 😊 ...'`（1363ms） | **PASS** |
| T01-4 覆盖为 `deepseek-flash`（剥离代理） | 返回中文回复 | ✅ `'你好！很高兴见到你 😊 ...'`（1224ms） | **PASS** |
| T01-5 覆盖为 `deepseek-v4-pro`（继承代理） | 返回中文回复 | ✅ `'你好！很高兴见你别...'`（1890ms） | **PASS** |

> **平台合法模型 ID = `deepseek-flash` / `deepseek-v4-pro`**；`.env` 现值 `deepseek-v4.1-flash` **非法**。

### 2.3 T04 离线三场景 + 流式（附录 C 第 2、3 项；模型覆盖为 `deepseek-flash`）

| # | 用例 | 预期 | 实际 | 结论 |
|---|---|---|---|---|
| A | 问「我的积分多少」 | 触发 `query_points` 工具调用；回复含真实积分 | `used_tools=['query_points']`；流式文本含 **290**（真实总积分）；2 轮（tool → respond） | **PASS** |
| B | 问「帮我制定学习规划」 | 路由 plan 技能；中文键 JSON；`_extract_plan_from_json` 解析出非空 stages/daily_tasks | 路由 ✅ `skill=plan`；输出 ✅ 含中文键（阶段一/阶段名称/总述说明/目标/任务清单）；但**本次** `_extract_plan_from_json` 返回 **None**（模型输出含前置说明 + 字符串值内未转义英文双引号） | **FAIL（非确定性，见 P3）** |
| C | 普通闲聊「你好呀，今天心情不错」 | 无 tool_call，一轮直达 respond | `used_tools=[]`；`node_respond` 输出 186 字，流式文本非空 | **PASS** |
| D | `astream_events(version="v2")` | 收到 `on_chat_model_stream` 增量 | 场景 A 收 180 个、场景 C 收 132 个 `on_chat_model_stream` 事件 | **PASS** |
| E | 规划场景工具调用 | plan 技能按需查画像/规划 | `used_tools=['query_profile','query_plans']`（2 轮后直出 JSON） | **PASS** |

> 注：首轮探针 `probe_t04_graph.py` 自身用 `event.get("output")` 读取 `final_content` 失败（与 P2 同源），导致 B/C 的 `final_content` 显示为空；改用流式 `stream_text` 复核后 C 通过、B 复现 P3。此为探针缺陷，非源码新增问题。

### 2.4 代理对照结论（附录 C 第 6 项）

| 场景 | 继承 `HTTP_PROXY=127.0.0.1:64025` | 剥离代理 | 结论 |
|---|---|---|---|
| LLM 直连（有效模型） | ✅ 成功 | ✅ 成功 | 两者一致 |
| LLM 直连（无效模型） | ❌ 400（**API 级响应**） | ❌ 400（**API 级响应**） | 两者一致 |
| 服务进程 `/chat`（有效模型，`--light`） | ✅ text+done | ✅ text+done | 两者一致 |

> **明确结论：本机代理 `127.0.0.1:64025` 可正常转发 `api.deepseek.com`，并非本次 LLM 失败的成因。** 附录 C 第 6 项「需清代理或加 `trust_env=False`」的担忧**不成立**（对 LLM 出站而言）。真正的失败原因是模型 ID 非法（P1），与代理无关。

### 2.5 T05 API 端到端（附录 C 第 4 项；真实服务 8130 + 真实 JWT；模型覆盖为 `deepseek-flash`）

服务以 `.env`+`DEEPSEEK_MODEL=deepseek-flash` 覆盖启动；JWT 由 `app.core.security.create_access_token({"sub":"3"})` 签发。

| 用例 | 预期 | 实际 | 结论 |
|---|---|---|---|
| `/api/health` | 200 success | 200 `{success:true}` | **PASS** |
| 闲聊 SSE | 200 + `text/event-stream`；text 增量 + done | 168 个 text + done | **PASS** |
| done 事件字段 | `{type,intent,full_content,conversation_id}` | 字段齐全，`conversation_id` 已注入 | **PASS** |
| 积分查询 | 回复含真实积分 | `full_content` 含「总积分：290 分 / 第 1 名」 | **PASS** |
| **规划 done.intent** | `generate_plan` | **`chat`** | **FAIL（P2）** |
| `/chat/save-plan` | 成功；`learning_plans`+1、`daily_tasks`>0、积分 +20 | success=true（title=「大数据技术（专科大二）→ Agent开发工程师 升学+就业双轨规划」）；DB `plans`+1、`tasks` **+44**、积分 **+20** | **PASS** |
| **简历 done.intent** | `generate_resume` | **`chat`** | **FAIL（P2）** |
| `/chat/save-resume` | 成功入库 | success=true（title=求职简历）；DB `resumes`+1、积分 **+15** | **PASS** |
| `/chat/conversations` | 200，含 icon 映射 | 200，total=21，icon ∈ {📋,📄,💬} | **PASS** |
| `/chat/conversations/{id}` | 200 详情 | 200，msg_count=2 | **PASS** |
| `DELETE /chat/conversations/{id}` | 200 | 200 success | **PASS** |
| DB 落库 intent 核对（只读） | assistant.intent=generate_plan | **`intent='chat'`** | **FAIL（P2）** |
| 无 key/异常 → error 事件不 500（按 `.env` 原样：非法模型） | 返回 error 事件，HTTP 200 | 200 + `{"type":"error","message":"智能体调用异常: Error code: 400 ..."}` | **PASS**（错误护栏生效） |

T05 汇总：**PASS 17 / FAIL 2**（2 个 FAIL 均为 P2 intent）。

---

## 三、问题清单

### P1【高】`DEEPSEEK_MODEL` 配置为平台非法模型 ID，导致全部真实 LLM 调用失败

- **配置键 / 位置**：`.env` 的 `DEEPSEEK_MODEL=deepseek-v4.1-flash`；默认值见 `app/core/config.py:39`
- **现象**：所有 LLM 调用（`get_llm().ainvoke`、图内 `call_model`、服务 `/chat`）均返回 HTTP 400，`/chat` 仅吐出一个 `error` 事件。
- **原始报错**：
  ```
  openai.BadRequestError: Error code: 400 - {'error': {'message':
  'The supported API model names are deepseek-flash, deepseek-v4-pro,
   but you passed deepseek-v4.1-flash.', 'type': 'invalid_request_error',
  'code': 'invalid_request_error'}}
  ```
- **复现步骤**：
  ```
  cd backend
  venv\Scripts\python.exe _qa_verify/probe_t01_smoke.py --mode with
  # 输出 RESULT=FAIL ... invalid model
  # 服务级：venv\Scripts\python.exe _qa_verify/probe_t05_api.py --uid 3 --port 8132 --light
  # → SSE 事件序列=['error']
  ```
- **期望**：使用 DeepSeek 平台**合法**模型 ID（实测 `deepseek-flash` 或 `deepseek-v4-pro` 均可）。
- **影响**：重构后 Agent 完全不可用（对话、工具、规划、简历全部失败）。
- **建议修复（仅记录，未执行）**：改 `.env` 一行 `DEEPSEEK_MODEL=deepseek-flash`（或平台确认后的正式 ID），无需改代码。**修复后须重跑本报告 T01/T04/T05。**
- **严重级**：**高**（阻塞一切真实场景）。

### P2【中】`done` 事件 `intent` 恒为 `chat` —— 源码 Bug（已定位）

- **文件:行号**：`app/api/chat.py:235`
  ```python
  elif ev_type == "on_chain_end":
      output = event.get("output")        # ← 错误：取不到值
      if isinstance(output, dict) and "final_content" in output:
          final_intent = output.get("intent", "chat")
          ...
  ```
- **根因**：`astream_events(version="v2")` 的事件负载嵌套在 `event["data"]` 下，**顶层无 `output` 键**。已核验 langchain-core 0.3.86 源码 `venv/Lib/site-packages/langchain_core/tracers/event_stream.py:596-611`：
  ```python
  data: EventData = {"output": outputs, "input": inputs,}
  self._send({"event": event, "data": data, "run_id": ..., "name": ..., ...}, run_type)
  ```
  实测：所有 `on_chain_end` 事件 `event.get("output") is None`（`has_top_output=false`），respond 节点真实输出位于 `event["data"]["output"]`（`final_content` 长度 3404、`intent=generate_plan`）。故 `final_intent` 永远停留在初值 `"chat"`。
- **现象 / 影响**：
  1. `/chat` 的 `done` 事件 `intent` 对规划/简历**恒为 `chat`**（违反任务文档 1.6/1.7「intent 必须为 generate_plan/generate_resume」铁律）；
  2. 落库的 assistant 消息 `intent='chat'` → `/chat/conversations` 的图标映射**恒为 💬**（📋/📄 永不出现）；
  3. `full_reply` 空时的 `full_content` 兜底（`chat.py:240-241`）永不生效。
  前端 `static/js/chat.js:437-447,528-537` 有自救逻辑（按消息关键词 + 结构化内容兜底推断 intent），所以「保存按钮」仍会出现、落库仍成功；**用户可直接感知的退化为「对话列表图标错误」**。
- **复现步骤**：
  ```
  venv\Scripts\python.exe _qa_verify/probe_t05_api.py --model deepseek-flash --uid 3 --port 8130
  # [FAIL] 规划 done intent=generate_plan: intent='chat'
  # [FAIL] 简历 done intent=generate_resume: intent='chat'
  # 只读核对：SELECT intent FROM chat_messages WHERE conversation_id='qa-t05-plan' AND role='assistant' → 'chat'
  ```
- **期望**：将 `event.get("output")` 改为 `event.get("data", {}).get("output")`，使 plan/resume 场景 `done.intent` 分别为 `generate_plan`/`generate_resume`，且落库 intent 正确。
- **严重级**：**中**（不阻断保存主流程，但破坏接口契约与对话列表图标；属确定性源码缺陷）。

### P3【中·非确定性】规划 JSON 解析对真实模型输出不健壮

- **文件:行号**：`app/api/chat.py:537`（`_extract_plan_from_json`，及 `:696` `_extract_plan_content` 的兜底）
- **现象**：真实模型输出含「**前置说明句** + ```` ```json ```` 代码块 + **字符串值内未转义的英文双引号**」时，`json.loads` 与 `re.search(r'\{[\s\S]*\}')` 均失败 → 返回 `None`。
- **原始片段（T04-B 实测）**：
  ```
  我先查询一下你的画像和学习规划信息。```json
  { "大数据技术·大二 → Agent开发工程师进阶规划": { "阶段一": {
      "总述说明": "把已有Python/Java/SQL技能从"会用"打磨到"能写工程化代码"，...   ← 值内出现未转义 " 
  ```
- **非确定性证据**：同模型下 **T04-B 一次失败（解析 None）/ T05 一次成功（title 正确、44 条 daily_tasks 入库）**。
- **影响**：偶发时 `_extract_plan_content` 走 Markdown 兜底 → 返回 `stages=[{"name":"综合规划",...}]`、`daily_tasks=[]`（非空字典 → `if not plan_content` 判不成立）→ **save-plan 仍返回 success 并 +20 积分，但规划无阶段内容、`daily_tasks` 入库 0 条**（静默数据质量退化）；或前端拿到不可保存的 JSON。
- **期望**：模型严格输出纯 JSON（无前置语、字符串内引号转义）；或在 `_extract_plan_from_json` 增加容错（提取首个 `{` 后按括号配平截取、正则修复值内裸引号 / 改用 `json_repair` 类策略）。**（建议在 P1 修复后重点复测此路径，多轮采样量化失败率。）**
- **严重级**：**中**（非确定性，影响规划入库质量）。

### P4【低】`full_content` 兜底失效（与 P2 同源）

- **文件:行号**：`app/api/chat.py:240-241`。同样受 `event.get("output")` 影响，`output["final_content"]` 兜底永不触发；若某次模型未产出 `on_chat_model_stream` 增量，接口会误发 `error`（"智能体未返回有效内容"），即使图实际产生了内容。当前 `streaming=True` 下增量稳定，实际影响低。

### P5【低】error 事件 message 被截断

- **文件:行号**：`app/api/chat.py:277` `str(e)[:200]`。非法模型场景下用户看到的报错在 `...'code'` 处被截断，缺少收尾，不便排障。

### P6【信息】回归套件中的空 key 前置用例已失效（非源码 Bug）

- **文件**：`tests/agent_refactor/test_imports.py:22`、`test_graph.py`（`test_empty_key_error_propagates`）、`test_api_langgraph.py`（`TestChatEmptyKey`）。
- **原因**：这些用例以「`DEEPSEEK_API_KEY` 为空」为前置，真实 key 填入后断言不再成立。建议改用 `monkeypatch.setenv("DEEPSEEK_API_KEY","")` + `reset_llm()` 隔离。

---

## 四、结论汇总

| 类别 | 数量 | 明细 |
|---|---|---|
| **PASS** | 全量回归 183 + T01 3 + T04 4 + T05 17 + 代理对照 3 | 工具调用、流式、SSE 三事件、落库、积分、鉴权、错误护栏均可用 |
| **FAIL（源码 Bug）** | 1 | **P2**：`done.intent` 恒为 `chat`（`chat.py:235`） |
| **FAIL（配置）** | 1 | **P1**：`DEEPSEEK_MODEL` 非法 → LLM 全废 |
| **FAIL（非确定性）** | 1 | **P3**：规划 JSON 解析不健壮 |
| **FAIL（测试前置过期）** | 3 | P6：空 key 用例 |

**放行建议**：**不予放行**。上线前必须至少修复 **P1（改 `.env` 模型 ID）** 与 **P2（`chat.py:235` 事件取值）**，并在 P1 修复后**重跑** T01/T04/T05 全量真实验收（尤其 P3 规划落库质量需多轮采样）。

---

## 五、未验证项与原因

| 未验证项 | 原因 |
|---|---|
| `AGENT_BACKEND=coze` 回退演练（T05 验收） | 附录 C 第 7 项：Coze PAT 已失效（4101 token incorrect），且本轮聚焦 DeepSeek；未演练。**BLOCKED** |
| 数据库 7 张表 `SHOW CREATE TABLE` schema 比对 | 本轮为只读核对，仅比对了行数/字段值，未做 DDL 逐表比对。**未做** |
| 前端浏览器实操（点击「保存规划/简历」、对话列表图标、打字机观感） | 未做真实浏览器端到端；仅通过后端 SSE + DB 间接验证。P2 的图标退化结论基于源码分析（`chat.js` 兜底 + `chat.py` 落库 intent）。**BLOCKED** |
| P3 规划解析失败率量化 | 需要多轮真实采样（费用/耗时约束），本轮样本量 2（1 失败/1 成功）。**部分验证** |
| 「按 `.env` 原样」下 T04/T05 全流程 | P1 使合法模型不可用，全流程必须覆盖模型名才能跑通；已用「覆盖合法模型」完成链路验证，并单独用「.env 原样」验证了 error 护栏。 |
| 工具内部抛异常 → 图不崩（T04 验收附加项） | 已由既有套件 `tests/agent_refactor/test_graph.py` 离线覆盖，本轮未重复真实调用。 |

---

## 附：本轮新增验证脚本（非源码，位于 `backend/_qa_verify/`）

| 脚本 | 用途 |
|---|---|
| `probe_t01_smoke.py` | T01 冒烟 + 模型可用性 + 代理对照（`--mode with/without`） |
| `probe_db_snapshot.py` | 数据库只读快照（users/points/profile/plans/tasks/resumes/chats） |
| `probe_t04_graph.py` | T04 离线三场景 + `astream_events` 流式 |
| `probe_t04b_debug.py` | T04 焦点复核 + `on_chain_end` 事件结构排查（定位 P2） |
| `probe_t05_api.py` | T05 API 端到端（真实服务 + 真实 JWT + SSE/DB 核对；`--light` 轻量代理对照） |

---

# 修复后复验（Round 2）

- **复验人**：严过关（software-qa-engineer / QA）
- **日期**：2026-09-17
- **复验对象**：寇豆码的三项修复（P1 `.env`/`config.py` 模型 ID、P2 `chat.py:237` done 事件取值、P3 两份 YAML 提示词追加约束）
- **复验性质**：**独立复测**——P1/P2/P3 全部自研脚本自证，**未复用工程师 `_fix_verify/` 脚本**；本轮**未改任何源码**（`app/`、`requirements.txt`、YAML、`.env` 均未动），改动仅限测试文件与新增 QA 脚本（`backend/_qa_round2/`）。
- **复验环境**：Python 3.13.14（backend/venv）；MySQL 本地；shell 注入 `HTTP_PROXY=127.0.0.1:64025`（LLM 出站正常）；测试服务端口 8123/8124/8125/8130/8131；测试用户 `user_id=3`。
- **总体判定**：✅ **可交付**。P1/P2/P3 三项修复**独立复测全部通过**；回归套件 **186 passed / 0 failed**（5 项测试侧失效用例已修复）；真实端到端四链路全绿。

---

## 一、A. 修复有效性独立复测

### A-1 P1（模型 ID 非法）— **PASS**

自研脚本 `_qa_round2/qa_p1.py`（三路独立自证）：

| 断言 | 期望 | 实测 | 结论 |
|---|---|---|---|
| `Settings(_env_file=None).DEEPSEEK_MODEL`（隔离 .env 的默认值） | 平台合法 ID | `deepseek-flash` | **PASS** |
| `get_settings().DEEPSEEK_MODEL`（读 .env 生效值） | 平台合法 ID | `deepseek-flash` | **PASS** |
| 真实 `get_llm().ainvoke("你好")` | 返回中文、无 400 模型错误 | `'你好！很高兴见到你。有什么我可以帮你的吗？'`（1182ms） | **PASS** |

> 结论：`.env` 取值与 `config.py` 默认值均已为合法 `deepseek-flash`；真实调用不再出现 400，且返回中文。**修复有效**。
> （旁证：上一轮 P1 复现的 400 报错为 `The supported API model names are deepseek-flash, deepseek-v4-pro, but you passed deepseek-v4.1-flash`，本轮未再出现。）

### A-2 P2（done 事件 intent 恒为 chat）— **PASS**

自研脚本 `_qa_round2/qa_p2.py`（**自研设计**，不复用工程师脚本）：
**设计**：起真实 uvicorn（8130，剥离代理）→ 用应用密钥自发 JWT（sub=3）→ 真实 `POST /api/chat` 各走一次「生成规划」「生成简历」→ **从 SSE 的 done 事件读取 `intent`** → 另**只读核对 DB** 对应 conversation 的 assistant 消息 `intent` 落库值。

| 场景 | 对话ID | HTTP | 耗时 | done.intent | DB assistant.intent | 期望 | 结论 |
|---|---|---|---|---|---|---|---|
| 生成规划（「帮我制定一份从大二到毕业的学习规划」） | `qa-r2-plan` | 200 | 15809ms | `generate_plan` | `generate_plan` | `generate_plan` | **PASS** |
| 生成简历（「帮我生成一份求职简历」） | `qa-r2-resume` | 200 | 9342ms | `generate_resume` | `generate_resume` | `generate_resume` | **PASS** |

> 铁律校验：SSE done 事件 intent 与 DB 落库 intent **一致且正确**，不再是恒定的 `chat`。**修复有效**。
> 说明：该验证为端到端黑盒（真实 HTTP + 真实 SSE + 真实落库），与工程师的「复现同构 StateGraph」白盒验证路径不同，互为交叉印证。

### A-3 P3（规划 JSON 解析不健壮）— **PASS**

自研脚本 `_qa_round2/qa_p3.py`：渲染真实 plan 技能 system prompt（含 user_id=3 画像）→ 真实模型**独立采样 12 轮**（真实用户消息「帮我制定学习规划」）→ 每轮输出喂给**生产真实解析器** `app.api.chat._extract_plan_from_json`。

| 轮次 | 输出长度 | 解析 stages | 解析 tasks | 结果 |
|---|---|---|---|---|
| 01 | 3742 | 6 | 50 | OK |
| 02 | 5379 | 6 | 50 | OK |
| 03 | 6930 | 6 | 50 | OK |
| 04 | 8034 | 6 | 50 | OK |
| 05 | 4261 | 6 | 50 | OK |
| 06 | 5142 | 6 | 50 | OK |
| 07 | 11164 | 5 | 50 | OK |
| 08 | 5173 | 6 | 50 | OK |
| 09 | 4225 | 6 | 50 | OK |
| 10 | 4572 | 6 | 50 | OK |
| 11 | 4167 | 5 | 50 | OK |
| 12 | 4894 | 5 | 50 | OK |

| 阶段 | 成功 | 失败 | 失败率 |
|---|---|---|---|
| 修复后（QA 独立采样） | **12** | **0** | **0.0%** |

> 摘要落盘 `_qa_round2/summary_plan_r2.txt`（`rounds=12 ok=12 fail=0 fail_rate=0.0%`）；失败样本文件 `_qa_round2/samples_plan_r2.txt` 为 0 字节（无失败样本）。
> 红线遵守：全程**未改** `_extract_plan_from_json` / `_extract_resume_from_json`。

**YAML 结构未被改动（键结构零变化）核对**：
- `diff plan_system.yaml.bak.20260917 plan_system.yaml` → 仅 2 处**追加块**（第 13-20 行「输出格式硬性约束」6 条、第 41 行注意事项呼应）+ 1 处**收尾说明句换行改写**（第 51 行 → 60-61 行，语义为「该轮只输出 JSON 本体的」补充，非键结构行）。
- 抽提两份 YAML 中所有 JSON 模板**键行**（正则 `^\s+"`）逐一比对 → `PLAN JSON KEY LINES IDENTICAL` / `RESUME JSON KEY LINES IDENTICAL`（**JSON 键与嵌套结构完全一致**，save-plan/save-resume 解析依赖不受影响）。
- YAML 语法与渲染：`_qa_round2/qa_p3.py` 实测 `skill.get_prompt(ctx)` 渲染成功，prompt 长度 1316 字且含「输出格式硬性约束」块。

### A-4 备份与铁律核对 — **PASS**

| 文件 | 本轮备份（带日期） | 09-16 旧备份（须未覆盖） | 结论 |
|---|---|---|---|
| `backend/.env` | `.env.bak.20260917`（1170B, 09-17 13:08） | `.env.bak`（621B, 09-16 17:40） | **旧备份未覆盖** ✔ |
| `app/api/chat.py` | `chat.py.bak.20260917`（38481B, 09-17 13:09） | `chat.py.bak`（31855B, 09-16 17:40） | **旧备份未覆盖** ✔ |
| `app/core/config.py` | `config.py.bak.20260917`（1990B, 09-17 13:37） | `config.py.bak`（1242B, 09-16 17:40） | **旧备份未覆盖** ✔（旧 1242B / 新 1990B 旁证吻合） |
| `plan_system.yaml` | `plan_system.yaml.bak.20260917`（2396B） | 无 | ✔ |
| `resume_system.yaml` | `resume_system.yaml.bak.20260917`（2678B） | 无 | ✔ |

**改动范围最小化核对（diff 当日备份 vs 现文件）**：
- `chat.py`：**仅第 235 行**由 `output = event.get("output")` 改为 `output = event.get("data", {}).get("output")`（+2 行中文注释），无其它改动。
- `config.py`：**仅第 39 行**默认值改动，无其它改动。
- **`_extract_*` 解析逻辑零变化**：用 `ast` 抽提新旧两版 7 个函数源码（`_extract_plan_from_json` / `_extract_plan_title` / `_extract_plan_content` / `_extract_list_under_heading` / `_extract_resume_from_json` / `_extract_resume_title` / `_extract_resume_content`）逐字符比对 → `RESULT = SAME_ALL`（与 09-16 `chat.py.bak` 完全一致）。**证实本轮只改了 235 行附近的 event 取值，未触碰解析逻辑。**

---

## 二、B. 测试套件修复（5 项失效用例）

**修复原则**：让用例**不再依赖真实 `.env` 状态**，改为**显式构造前置条件**；**未放宽/删除任何断言**。改动**仅限测试文件**（`backend/tests/agent_refactor/`），未动源码。

### 改动清单

| 文件 | 改动 | 说明 |
|---|---|---|
| `conftest.py` | ①`start_server()` 新增 `extra_env` 参数；②新增 `empty_key_env` 夹具（进程内）；③新增 `empty_key_server` 夹具（子进程，端口 8125） | `extra_env` 显式覆盖子进程环境变量（pydantic 环境变量优先于 .env 文件） |
| `test_imports.py` | `test_get_llm_empty_key_raises_zhitu_error` 增加 `empty_key_env` 前置 | 原靠「.env key 为空」失效；现 `monkeypatch.setenv("DEEPSEEK_API_KEY","")` + `get_settings.cache_clear()` + `reset_llm()` 强制空 key，用例结束复原 |
| `test_graph.py` | `TestGraphRuntime::test_empty_key_error_propagates` 增加 `empty_key_env` 前置 | 同上，显式注入空 key |
| `test_api_langgraph.py` | `TestChatEmptyKey` 类内新增 `base_url` 夹具覆盖，指向 `empty_key_server` | 该类 4 个用例改用「子进程 env 显式注入空 key」的真实服务（8125），不再依赖真实 .env |
| `test_api_coze_fallback.py` | `coze_server` 夹具改为 `start_server(8124, extra_env={"AGENT_BACKEND": "coze"})`；**移除对真实 .env 的改写/还原** | 子进程 env 显式注入 `AGENT_BACKEND=coze`，覆盖 `coze_client.load_dotenv()` 注入的 `langgraph`；**未改 `coze_client.py`**（维持零改动裁定），且不再临时改写真实 .env（降低崩溃残留风险） |

### 前置构造原理（为何有效）

- pydantic-settings 中**环境变量优先级高于 `.env` 文件**：向子进程/进程 env 注入 `DEEPSEEK_API_KEY=""` 或 `AGENT_BACKEND=coze`，即可在与真实 `.env` 无关的前提下确定性地构造前置条件。
- `coze` 用例根因（工程师已定位）：`app/services/coze_client.py` import 时 `load_dotenv()` 把 `.env` 注入 `os.environ`，`conftest._clean_env()` 又继承 `os.environ` 启动子进程 → 子进程被强制为 `langgraph`。本轮显式注入 `AGENT_BACKEND=coze` 覆盖之。

### 目标用例复跑（显式证据）

```
test_imports.py::test_get_llm_empty_key_raises_zhitu_error ............... PASSED
test_graph.py::TestGraphRuntime::test_empty_key_error_propagates ......... PASSED
test_api_langgraph.py::TestChatEmptyKey::test_chat_returns_error_event_not_500 PASSED
test_api_langgraph.py::TestChatEmptyKey::test_chat_empty_message_error_event  PASSED
test_api_langgraph.py::TestChatEmptyKey::test_chat_oversized_message_422      PASSED
test_api_langgraph.py::TestChatEmptyKey::test_chat_with_explicit_conversation_id PASSED
test_api_coze_fallback.py::test_coze_fallback_error_event_not_500 ........ PASSED
test_api_coze_fallback.py::test_coze_channel_health ..................... PASSED
======================== 8 passed in 9.51s ========================
```
> 原 5 项失败用例（4 空 key 前置 + 1 coze 回退）**全部转绿**。

---

## 三、C. 全量回归 + 端到端

### C-1 全量回归

```
cd backend && venv\Scripts\python.exe -m pytest tests/agent_refactor -v
====================== 186 passed, 9 warnings in 30.31s =======================
```
- **结果：186 passed / 0 failed**（修复前为 181 passed / 5 failed）。失败集合清零，**无源码回归、无新增失败**。
- 回归套件覆盖「零改动文件未被修改」「DB 表集合/列结构未变」「工具/技能注册表完整」等静态校验，均通过。

### C-2 真实端到端（`_qa_round2/qa_e2e.py`，服务 8131）

真实 JWT（sub=3）+ 真实模型 + 真实 DB。**DB 只读核对**（save 端点为其正常业务写入）。

| # | 链路 | 期望 | 实测 | 结论 |
|---|---|---|---|---|
| 1 | 普通聊天「你好呀，今天心情不错」 | text + done | http200 / done=True / intent=`chat` / 195 字 | **PASS** |
| 2 | 积分查询「我现在有多少积分？」 | 触发 `query_points`，回复含真实积分 | 回复含 **425 分**、排名第 1 名（真实总数 425） | **PASS** |
| 3 | 生成规划 → `/chat/save-plan` | done.intent=`generate_plan`；入库 `learning_plans`+1、`daily_tasks`>0、积分+20 | intent=`generate_plan`；save success（id=31）；**plans +1、tasks +50、points +20** | **PASS** |
| 4 | 生成简历 → `/chat/save-resume` | done.intent=`generate_resume`；入库 `resumes`+1、积分+15 | intent=`generate_resume`；save success（id=14）；**resumes +1、points +15** | **PASS** |

DB 前后快照：`BEFORE {plans:15, tasks:70, resumes:6, points:425}` → 规划后 `{+1,+50,0,+20}` → 简历后 `{0,0,+1,+15}`。**四条主链路端到端全绿。**

### C-3 残留文件清理

- 工程师报告提到的 `backend/_fix_verify/_cleanup.txt`、`_rmlog.txt` 两个残留小文件**已删除**（`rm -f` 成功）。`_fix_verify/` 现仅保留有效的验证脚本与样本文件。
- 测试用 uvicorn 子进程已全部精准退出：`netstat` 显示 8123/8124/8125/8130/8131 **无残留监听**，`tasklist` **无 python.exe 残留**。未使用 `stop.bat`。

---

## 四、观察与未验证项

### 观察（信息级，不阻断交付）

1. **积分查询回复的 done.intent 可能被内容兜底判为 `generate_plan`**：本轮 C-2 #2 中，`query_points` 类消息（路由至 chat 技能）的回复因含「学习规划 / 阶段 / 目标」等结构词，被 `node_respond` 的**内容兜底解析** `parse_intent_from_reply`（任务书 1.7 规则 2/3，属既有设计逻辑）判为 `generate_plan`。**这是设计内的启发式回退**，非 P2 引入的缺陷（P2 的正确性已由 A-2 铁律断言覆盖）；唯一可见影响是对话列表图标（📋 vs 💬）可能偏差。**建议后续评估**：对 `query_*` 意图收紧内容兜底阈值（**超出本轮范围，未改动**）。
2. P3 修复为**提示词侧软约束**，LLM 非确定性仍存：本轮 12/12 成功，但建议持续抽样监控（本轮以 0% 失败率通过 <10% 阈值）。

### 未验证项

| 未验证项 | 原因 |
|---|---|
| 前端浏览器实操（点击保存按钮、对话列表图标、打字机观感） | 本轮为后端黑盒（真实 SSE + DB），未做真实浏览器端到端。**BLOCKED** |
| `AGENT_BACKEND=coze` 正常链路演练 | Coze PAT 仍失效（4101），仅验证「回退可达 + error 事件不 500」护栏，未验证 Coze 正常对话。**BLOCKED（平台侧）** |
| DB DDL `SHOW CREATE TABLE` 逐表比对 | 已由套件 `test_static_checks.py::TestDatabaseSchema`（表集合/列结构未变）覆盖并通过，未单独再做 DDL dump。 |

---

## 五、Round 2 结论

| 项 | 结论 |
|---|---|
| P1 修复有效性（独立复测） | **PASS** |
| P2 修复有效性（独立复测，SSE done.intent + DB 落库） | **PASS** |
| P3 修复有效性（独立 12 轮采样 0 失败 + YAML 键结构零变化 + 解析逻辑零改动） | **PASS** |
| 备份铁律（当日备份齐全、09-16 旧备份未覆盖） | **PASS** |
| 测试套件修复（5 项失效用例） | **PASS**（未放宽/删除断言） |
| 全量回归 | **186 passed / 0 failed** |
| 真实端到端（聊天/积分/规划入库+20/简历入库+15） | **PASS** |
| 残留文件与子进程清理 | **已完成** |

**最终判定：✅ 可交付（放行）。** 三项缺陷修复经 QA 独立复测全部有效，测试套件全绿，真实端到端全链路通过。仅存 2 项信息级观察与 2 项受环境限制的未验证项（前端浏览器、Coze 正常链路），均不阻断交付。

**本轮新增 QA 脚本（非源码，位于 `backend/_qa_round2/`）**：

| 脚本 | 用途 |
|---|---|
| `qa_p1.py` | P1 三路独立复测（默认值 / .env 值 / 真实调用） |
| `qa_p2.py` | P2 自研黑盒复测（真实服务 8130 + SSE done.intent + DB 只读核对） |
| `qa_p3.py` | P3 独立采样（真实 prompt + 真实解析器 + 12 轮） |
| `qa_e2e.py` | 真实端到端四链路（聊天/积分/规划入库/简历入库） |
| `cmp_extract_funcs.py` | `_extract_*` 解析逻辑新旧一致性核对（ast 抽提比对） |

---

# Round 3 · 项目整理与可移植化验证（2026-09-17）

- **验证人**：严过关（software-qa-engineer / QA）
- **验证对象**：工程师 W1–W6 整理改动（根 `.gitignore`、`backend/.env.example`、根 `README.md`、`main.py:30` 文案、`stop.bat` 精确停端口、改前备份目录）+ 主理人对 29 项无用文件的隔离（`_cleanup_backup_20260917/removed/`）
- **验证性质**：**只验不改**——未修改任何源码/配置；全部临时验证脚本置于**系统临时目录**（`%TEMP%`），**项目内零新增文件**。
- **验证范围**：A 密钥零泄露 / B `.env.example` 完整性 / C README 可执行性 / D `stop.bat` 精准停端口 / E 清理后回归 / F 保留资产完整性 / G 可移植性

---

## A【最高优先】密钥零泄露验证 — ✅ **PASS**

### A-1 提交清单 dry-run（`git add -A -n`，未改索引）

「将被暂存」共 **54 add + 5 remove**。逐一核对：**清单中不含** `.env`、`api.txt`、任何 `*.bak`、任何 `*.log`、任何 `_qa_*/`、任何 `_cleanup_backup_*/` —— 全部为**零命中**。

- 5 个 remove 为历史遗留 tracked 文件的删除（`app/api_backup/chat.py`、`app/models_backup/chat.py`、2 个 `.css.copy`、`chat.js.new_version`），**方向为「移除」而非「新增」**，不引入任何文件。
- 新增项仅为：`README.md`、`backend/tests/agent_refactor/*`（11 用例 + conftest + pytest.ini）、`app/llm|agent|skills|mcpserver` 源码、3 份 `docs/*.md`。

### A-2 密钥特征扫描（只报命中/未命中，不记录密钥值）

| 扫描范围 | `sk-[A-Za-z0-9]{20,}` | `pat_[A-Za-z0-9]{20,}` | SMTP 授权码字面量 | `JWT_SECRET_KEY=` 非占位 |
|---|---|---|---|---|
| 全工作区（排除 venv/.git/`__pycache__`/`_cleanup_backup_*`，共 **134** 文件） | **未命中** | **未命中** | **未命中** | 未命中（见下误报说明） |
| `git grep -l` 扫描 **HEAD 全部已跟踪 blob** | **未命中**（exit 1） | **未命中** | **未命中** | — |
| 专项：`docs/` 3 份 md + 2 份 sql、`README.md`、`AGENTS.md`、`backend/.env.example` | **未命中** | **未命中** | **未命中** | 未命中（示例值均为占位符） |

- **`JWT_SECRET_KEY` 误报说明**：`app/core/config.py:24` 命中系匹配到类型注解 `JWT_SECRET_KEY: str = ""`（真实为空）；`app/core/security.py:30/36` 命中系代码引用 `settings.JWT_SECRET_KEY`（运行时读配置）。**均非硬编码密钥。**
- **被忽略文件确含真实密钥**（证明 `.gitignore` 防护必要性，仅报布尔，不记录明文）：
  - `api.txt` → 含 `sk-` 特征
  - `backend/.env` → 含 `sk-` + `pat_` + SMTP 授权码 特征
  - `_cleanup_backup_20260917/removed/backend/.env.bak` → 含 `sk-` + `pat_` + SMTP 授权码 特征
  - **以上三者均被 `.gitignore` 拦截，不会进入仓库。**

### A-3 `git check-ignore -v` 抽查

| 路径 | 命中规则 | exit |
|---|---|---|
| `api.txt` | `.gitignore:14:api.txt` | 0（已忽略）✅ |
| `backend/.env` | `.gitignore:8:.env` | 0（已忽略）✅ |
| `backend/.env.bak` | `.gitignore:17:*.bak` | 0（已忽略）✅ |
| `backend/server.log` | `.gitignore:57:backend/server.log` | 0（已忽略）✅ |
| `_cleanup_backup_20260917/` | `.gitignore:69:_cleanup_backup_*/` | 0（已忽略）✅ |
| `backend/tests/agent_refactor/server_8124.log` | `.gitignore:56:server_*.log` | 0（已忽略）✅ |
| **`backend/.env.example`** | **无匹配（反证）** | **1（未被忽略）✅** |

### A-4 结论

> **clone 该仓库不会拿到任何真实密钥。** 模板文件（`.env.example`）未被忽略且仅含占位符；所有含密钥文件（`.env`/`api.txt`/`*.bak`）均被拦截；HEAD 与待提交清单均无密钥特征命中。**A 项：PASS。**

---

## B · `backend/.env.example` 完整性 — ✅ **PASS（25/25，零缺失零多余）**

以 `app/core/config.py` 的 `Settings` 类字段为基准逐字段对照（`DATABASE_URL` 为 `@property`、非配置字段，不计入）：

| 分组 | 字段数 | 明细 | .env.example 覆盖 |
|---|---|---|---|
| DB_* | 5 | HOST/PORT/USER/PASSWORD/NAME | ✅ 齐全 |
| JWT_* | 3 | SECRET_KEY/ALGORITHM/EXPIRE_HOURS | ✅ 齐全 |
| DEEPSEEK_* | 3 | API_KEY/MODEL/BASE_URL | ✅ 齐全 |
| AGENT_* + PROMPT_HOT_RELOAD | 3 | BACKEND/MAX_ITER/HOT_RELOAD | ✅ 齐全 |
| LLM_* | 2 | TEMPERATURE/MAX_TOKENS | ✅ 齐全 |
| COZE_* | 2 | PAT/BOT_ID | ✅ 齐全 |
| QWEN_* | 3 | API_KEY/MODEL/BASE_URL | ✅ 齐全 |
| SMTP_* | 4 | HOST/PORT/USER/PASSWORD | ✅ 齐全 |
| **合计** | **25** | | **缺失=无 / 多余=无** |

> **口径修正**：任务书称「24 字段」，实测 `Settings` 共 **25** 个字段（`5+3+3+3+2+2+3+4=25`），`.env.example` 亦为 **25** 键，**逐字段一一对应，零遗漏**——「零遗漏」结论成立，仅是计数标注为 25。

**占位值安全性**（敏感项均为占位符或留空，无真实密钥）：

| 键 | 值 | 判定 |
|---|---|---|
| `DB_PASSWORD` | `your_password` | 占位符 ✅ |
| `JWT_SECRET_KEY` | `change-me-to-a-random-secret` | 占位符 ✅ |
| `DEEPSEEK_API_KEY` | `your_deepseek_api_key` | 占位符 ✅ |
| `COZE_PAT` / `QWEN_API_KEY` | （留空） | 留空 ✅ |
| `SMTP_USER` / `SMTP_PASSWORD` | `your_email@qq.com` / `your_smtp_auth_code` | 占位符 ✅ |

---

## C · README 可执行性审查 — ✅ **PASS（含 2 处轻微提示，不阻断）**

| 检查项 | 结论 |
|---|---|
| §3.1 venv 创建 + `pip install -r requirements.txt` | ✅ 命令正确；`venv\Scripts\pip.exe` 实际存在 |
| §3.2 建库 + 导入 `docs/ai_learning_system.sql` | ✅ **独立核对 SQL 内容**：`CREATE TABLE` 恰 **7** 张；**无 `CREATE DATABASE`**、**无 `INSERT`/种子数据**、**含 `DROP TABLE IF EXISTS`** —— 与 README 描述**完全一致** |
| §3.3 `.env` 配置（`copy .env.example .env`） | ✅ 正确 |
| §3.4 `start.bat` 启动 + 访问端口 | ✅ `start.bat` 内 `cd /d "%~dp0"` 自适应工作目录；端口 8000、`/api/health`、`/docs` 表述正确 |
| §3.5 测试命令与 pytest 前置 | ✅ **自洽**：`requirements.txt` 确**不含** pytest，README 已在 §3.1/§3.5 明示需单独 `pip install pytest pytest-asyncio requests` |
| 工作目录要求 | ✅ README 明确「必须以 `backend/` 为工作目录」，与实际 `.env` 相对路径解析一致 |

**轻微提示（建议优化，非阻断）**：
1. **§3.2 SQL 相对路径**：§3.1 已执行 `cd backend`，而 §3.2 导入命令写作 `mysql ... < docs\ai_learning_system.sql`；若读者仍在 `backend/` 下，该路径不存在（应为 `..\docs\...` 或注明「在仓库根目录执行」）。
2. `docs/agent-refactor-tasks.md`（历史文档）称默认模型为 `deepseek-v4.1-flash`，而 README §3.3 与 `config.py` 默认值均为 `deepseek-flash`（README 正确）；历史文档口径差异不影响上手。

---

## D · `stop.bat` 新逻辑实测 — ✅ **PASS**

以「无关 python 长驻进程 + 8000 端口 uvicorn」双进程实测：

| 步骤 | 实测 |
|---|---|
| 起无关 python 进程 | PID **26952**（存活） |
| 起 uvicorn（8000） | 启动器 PID 11516；`netstat` 实际 LISTENING 于 8000 的 PID = **19836** |
| 执行 `backend\stop.bat` | 输出：`[zhitu] 停止 PID 19836（端口 8000）...` / `[zhitu] Stopped.`（returncode=0） |
| 断言① uvicorn 已停 | ✅ uvicorn 存活=False，8000 不再监听 |
| 断言② **无关 python 仍存活** | ✅ PID 26952 存活=True（**关键：未被误杀**） |
| 清理 | ✅ 已停止我起的全部进程；8000 无残留监听 |

> 结论：新逻辑**仅 taskkill 监听 8000 的 PID**，`":8000 "` 精确匹配避免误伤 18000 等端口，**不再杀全机 python**。**D 项：PASS。**

---

## E · 清理后回归 — ❌ **FAIL（165 passed / 21 failed）**

```
cd backend && venv\Scripts\python.exe -m pytest tests/agent_refactor -v
================= 21 failed, 165 passed, 9 warnings in 21.96s =================
```

总量仍为 **186**（165+21），但较 Round 2（186/0）**新增 21 个失败**，**全部集中在 `tests/agent_refactor/test_static_checks.py`**（其余 10 个测试模块全绿，含 `TestDatabaseSchema` 真实 DB 校验）。

**失败分类与根因**（均为**测试侧断言过期**，非产品/源码缺陷）：

| 失败类 | 数量 | 断言内容（Round 1 遗留不变量） | 本轮为何失败 |
|---|---|---|---|
| `TestBakFiles::test_bak_exists` | 9 | 9 个 `.bak` 备份必须存在 | 清理轮已将 14 个 `.bak`（含 `.env.bak`）**移入隔离区** |
| `TestBakFiles::test_bak_matches_git_head` | 8 | `.bak` 须与 HEAD 逐字节一致 | 同上，`.bak` 已不在 `backend/` |
| `TestBakFiles::test_env_only_additions` | 1 | 依赖 `backend/.env.bak` 存在 | 同上 |
| `TestChangeScope::test_git_modified_files_within_authorization` | 1 | 仅 9 个授权文件可被修改 | 本轮合法新增改动 `.gitignore`/`main.py`/`.env.example`/`stop.bat`（W1–W5） |
| `TestChangeScope::test_zero_change_files_unmodified_in_git[main.py]` | 1 | `main.py` 必须零改动 | W4 合法修改了 `main.py:30` 描述文案 |
| `TestChangeScope::test_zero_change_files_no_new_framework_pollution[main.py]` | 1 | `main.py` 不得含 `LangChain` 等字样 | W4 文案新增「本地 LangChain / LangGraph」 |
| **合计** | **21** | | |

> **根因判定**：`test_static_checks.py` 是 **Round 1 Agent 重构轮**的产物，其断言固化了「9 个 .bak 必须存在 / 仅 9 文件可改 / main.py 零改动」三项**针对上一轮的临时铁律**。本轮「清理 + 可移植化」（W1–W6 + 用户确认隔离 29 项）**按需求合法破坏了这三项不变量**，故这些断言**已过期、不再成立**。
> **性质**：**测试侧过期（assertion 本身错误）**，非源码 Bug；按 QA 决策规则本应由 QA 自行修正，但**主理人本轮明确要求「只验不改」**，故此处**仅报告不改**，交由主理人决策。
> **修复建议（供决策，本轮未执行）**：更新 `test_static_checks.py` —— 将 `TestBakFiles` 适配为「.bak 已归入 `_cleanup_backup_*/` 或已不存在」，将 `TestChangeScope` 的授权/零改动清单适配到本轮的 W1–W6 改动集（或移除该轮历史临时铁律）。修复后预期回到 **186 passed / 0 failed**。

> **影响**：**不阻断密钥安全（A 项已独立证明无泄露）**；但使「186/0」验收不成立，且新人/CI 首次跑测试会见到 21 项红色。

---

## F · 保留资产完整性 — ✅ **PASS（含 2 处口径修正）**

| 必需资产 | 状态 |
|---|---|
| `backend/tests/agent_refactor/`：**11** 个 `test_*.py` + `conftest.py` + `pytest.ini`（共 13 文件，承载 186 用例） | ✅ 齐全 |
| `docs/`：**3** 份 md（tasks / fix-report / test-report）+ **2** 份 sql | ✅ 齐全 |
| `AGENTS.md` | ✅ 在 |
| `backend/app/llm`（5 py）、`app/agent`（18 py）、`app/skills/{chat,plan,resume}`（含 prompts yaml）、`app/mcpserver`（3 py） | ✅ 齐全 |
| `backend/.env.example`、`README.md`、`start.bat` | ✅ 齐全 |
| 隔离区 `_cleanup_backup_20260917/` **不在** `git status` 视野 | ✅ 确认（`git status --short` 无任何 `_cleanup_backup_*` 条目） |

**口径修正**：
1. 任务书称「13 个 test 文件」——实际为 **11 个 `test_*.py`**；若含 `conftest.py` + `pytest.ini` 则共 **13 个文件**（与 186 用例吻合）。
2. 任务书称「docs 4 个 md」——实际为 **3 个 md + 2 个 sql**。

**发现（信息级，不阻断）**：`backend/tests/agent_refactor/server_8124.log` 为上一轮测试残留日志，**已被 `.gitignore:56:server_*.log` 忽略**，不会进入仓库；建议顺手删除以保持目录整洁。

---

## G · 可移植性 — ✅ **PASS（代码层）；文档层 2 处轻微**

| 检查 | 结论 |
|---|---|
| 全项目（排除 venv/.git/`__pycache__`/隔离区）硬编码绝对路径扫描 | 代码层**零命中** ✅ |
| `main.py` 静态目录 | ✅ 使用相对路径：`STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")` |
| `.idea/*`（含本机绝对路径） | ✅ 被 `.gitignore:35:.idea/` 忽略且**未跟踪**，不进入仓库 |
| `docs/agent-refactor-tasks.md` | ⚠️ 原第 **4、106** 行含本机绝对路径（历史文档路径基准引用，仅文字说明）——**已在 Round 3 修复轮泛化为 `<项目根>`** |

---

## Round 3 结论汇总

| 项 | 结论 | 备注 |
|---|---|---|
| **A 密钥零泄露** | ✅ **PASS** | dry-run 清单无敏感文件；134 文件 + HEAD 全 blob 密钥扫描零命中；check-ignore 防护有效；`.env.example` 反证未被忽略 |
| B `.env.example` 完整性 | ✅ PASS | 25/25 逐字段对齐，零缺失零多余，占位值安全 |
| C README 可执行性 | ✅ PASS | SQL 独立核对与描述一致；2 处轻微提示（SQL 相对路径、历史文档模型名口径） |
| D `stop.bat` 精准停端口 | ✅ PASS | 仅停 8000，未误杀无关 python |
| **E 清理后回归** | ❌ **FAIL** | **165 passed / 21 failed**；全部为 `test_static_checks.py` **测试侧过期**，非源码缺陷 |
| F 保留资产完整性 | ✅ PASS | 资产齐全；隔离区不在 git 视野；2 处口径修正 |
| G 可移植性 | ✅ PASS | 代码零硬编码绝对路径；文档层 2 处轻微 |

### 最终判定

> **【密钥维度：可安全上传】仓库不含任何真实密钥，clone 后不会泄露 `.env`/`api.txt`/Coze PAT/Qwen Key/SMTP 授权码/DeepSeek Key。**
>
> **【存在 1 个非安全阻断项】** `E` 项「186/0」验收**未达成**（165/21）：建议在正式推送前**更新 `tests/agent_refactor/test_static_checks.py`**（其断言固化了上一轮临时铁律，与本轮用户确认的清理/可移植化相冲突），否则新人/CI 会看到 21 项失败。此项**不影响密钥安全**，可由主理人裁定「先修测试再提交」或「本轮接受、下轮更新」。

### 阻断项清单

| # | 类型 | 描述 | 是否阻断「安全上传」 |
|---|---|---|---|
| 1 | 测试过期（非安全）→ **已修复** | `test_static_checks.py` 断言已适配本轮状态，全量回归回到 **186 passed / 0 failed** | 否（已解除） |
| 2 | 信息级 → **已处理** | `server_8123/8124/8125.log` 已移入隔离区 `_cleanup_backup_20260917/removed/backend/tests/agent_refactor/` | 否 |
| 3 | 轻微 → **已修复** | `docs/agent-refactor-tasks.md:4,106` 硬编码路径已泛化为 `<项目根>` | 否 |
| 4 | 轻微 → **已修复** | README §3.2 SQL 相对路径已改为 `..\docs\ai_learning_system.sql` 并加注说明 | 否 |

> **验证阶段**未修改任何源码/配置；全部验证脚本置于系统临时目录（`%TEMP%/qa_r3_*.py`）。修复阶段的改动见下节「Round 3 · 修复复验」。

---

### Round 3 · 修复复验（Fix Pass，经 team-lead 授权）

**授权**：team-lead 解除「只验不改」约束，授权有界修复 4 项（目标：整仓库 clone 后 `pytest` 全绿 + README 照做可跑通）。**全程未做任何 `git add` / `git commit`。**

#### 变更清单（路径 + 改了什么 + 为什么）

| # | 文件 | 改动 | 原因 |
|---|---|---|---|
| 1 | `backend/tests/agent_refactor/test_static_checks.py` | ① `TestBakFiles::test_bak_exists`（9 例）由「断言 `{rel}.bak` 必须存在」**翻转为**「断言其已清场（工作区不再残留）」；② 原 `test_bak_matches_git_head`（8 例）重命名为 `test_bak_relocated_to_quarantine`，断言隔离区归档副本存在（改前原文未丢）；③ `test_env_only_additions`（1 例）改从隔离区读 `.env.bak`；④ `TestChangeScope` 授权集更新为本轮合法改动（原 8 个跟踪改文件 + `.gitignore`/`.env.example`/`main.py`/`stop.bat`）；⑤ `ZERO_CHANGE_FILES` 移出 `main.py`（本轮 W4 合法改了描述文案），补入同为零改动的 `app/core/database.py` 以维持清单规模。 | 该文件固化的是第 1 轮重构临时铁律，被本轮用户确认的清理/可移植化击穿。 |
| 2 | `backend/tests/agent_refactor/server_8123/8124/8125.log` | 移入 `_cleanup_backup_20260917/removed/backend/tests/agent_refactor/`（同名归档已存在 → 追加 `.regen_r3`，不覆盖） | 清除工作区残留日志；不用 `rm` |
| 3 | `README.md` §3.2 | SQL 导入相对路径改为 `..\docs\ai_learning_system.sql`，并加注「若在项目根执行则为 `docs\...`」 | §3.1 已 `cd backend`，原 `docs\...` 字面照做会失败 |
| 4 | `docs/agent-refactor-tasks.md` 第 4/106 行 | 硬编码本机绝对路径泛化为 `<项目根>` | 去除本机绝对路径引用 |

**未削弱任何安全相关断言**：`FORBIDDEN_IMPORT_RE` 框架污染检查、DB 7 表 schema 校验、`.env` 追加键校验、变更范围校验**全部保留**（仅参数与目标值随本轮状态据实更新）。
**`main.py` 为何移出「零改动清单」**：经 Read 实际确认，其**无** `langchain/langgraph` 的 `import`，仅 W4 在 FastAPI 描述字符串中写入「本地 LangChain / LangGraph」文案；且其已属本轮**授权改动**文件，故据实从零改动清单移出（污染检查仍对其余 24 个零改动文件生效）。

#### 全量回归（原始输出片段）

```
============================= test session starts ============================
...
tests\agent_refactor\test_static_checks.py::TestBakFiles::test_bak_relocated_to_quarantine[requirements.txt] PASSED [ 65%]
tests\agent_refactor\test_static_checks.py::TestBakFiles::test_env_only_additions PASSED [ 69%]
tests\agent_refactor\test_static_checks.py::TestChangeScope::test_git_modified_files_within_authorization PASSED [ 69%]
tests\agent_refactor\test_static_checks.py::TestChangeScope::test_zero_change_files_unmodified_in_git[app/core/database.py] PASSED [ 76%]
tests\agent_refactor\test_static_checks.py::TestDatabaseSchema::test_table_set_unchanged PASSED [ 96%]
====================== 186 passed, 9 warnings in 31.52s =======================
PYTEST_EXIT=0
```

> 测试 ID 总数保持 **186**（本文件 69 例：TestBakFiles 9+8+1、TestChangeScope 1+24+24、TestDatabaseSchema 2），与修复前一致，仅断言语义据实更新。

#### Fix Pass 结论

`clone` 后执行 `cd backend && venv\Scripts\python.exe -m pytest tests\agent_refactor` → **186 passed / 0 failed**；README 照做可跑通。**Round 3 全部 4 项阻断/提示均已闭环。**

---

### Round 3 · 二次修复（clone-safe 化）+ 克隆模拟复验

**背景（team-lead 复核发现）**：上一版 `test_static_checks.py` 有 3 类断言绑定「本机迁移中间态」，**fresh clone 会 FAIL**：
1. `test_bak_relocated_to_quarantine`（8 例）依赖隔离区 `.bak`，而隔离区被 `.gitignore:69` 忽略 → 克隆后不存在；
2. `test_env_only_additions` 依赖隔离区 `.env.bak` + `backend/.env`（均被 gitignore）→ 克隆后不存在；
3. `test_git_modified_files_within_authorization` 要求 `git status -s` 的 `" M "` 集**恰等于**授权集；用户执行 `git add -A && git commit` 后工作区转干净 → `missing`=全部授权文件 → FAIL。
即：**一旦提交（正是用户要做的），克隆仓库跑 pytest 会挂约 10 例**，与「可在别处使用」目标冲突。

**修复（skip 守卫；保留全部安全断言）**：

| 用例 | 守卫条件 |
|---|---|
| `test_bak_relocated_to_quarantine`（8） | `QUARANTINE_BACKEND` 目录不存在 → `pytest.skip` |
| `test_env_only_additions`（1） | 隔离区 `.env.bak` 或 `backend/.env` 缺失 → `pytest.skip` |
| `test_git_modified_files_within_authorization`（1） | **始终保留 `unexpected`（无未授权改动）断言**；仅 `modified` 非空时校验 `missing`；`modified==set()`（克隆/已提交态）→ `pytest.skip` |
| `TestDatabaseSchema`（2） | 连接类异常（`_is_db_unavailable`）→ `pytest.skip`，无 DB 的克隆机不 error |

> 安全相关断言（`FORBIDDEN_IMPORT_RE` 框架污染扫描、DB 表集合校验、变更范围「无未授权项」等）**一律保留**；skip 仅替代「存在性前置」，不因跳过而削弱安全校验。

**克隆模拟（`%TEMP%\zhitu_clone_sim`，含独立 `.git`；全程未触碰真实仓库）**：
1. 目录拷贝仓库（排除 `venv`/缓存）+ 为副本 `backend/venv` 建**目录联接（junction）**指向真实 venv（`conftest.start_server` 硬编码该路径）；
2. 副本内 `git add -A && git commit -m sim` → `59 files changed`，commit `2040066`，**工作区转干净（status 空）**；
3. 删除副本隔离区 `_cleanup_backup_20260917/` 与所有 `*.bak`（模拟只拿到仓库内容的机器；保留副本 `.env`）；
4. 副本内跑全量 pytest。

副本 pytest 原始输出尾部：
```
tests\agent_refactor\test_static_checks.py::TestDatabaseSchema::test_table_set_unchanged PASSED  [ 96%]
tests\agent_refactor\test_static_checks.py::TestDatabaseSchema::test_columns_match_baseline PASSED [ 96%]
tests\agent_refactor\test_tools_db.py::test_query_points_summary PASSED  [ 97%]
...
tests\agent_refactor\test_tools_db.py::test_query_profile_nonexistent_user PASSED [100%]
================ 176 passed, 10 skipped, 9 warnings in 27.96s =================
```

> **10 skipped = 8 + 1 + 1**，恰为上述三个守卫用例；**0 failed / 0 error**；`176 + 10 = 186` 总数不变。
> 另核实副本跟踪集 **127 文件，`suspect(env/api/bak/log/quarantine)=NONE`** —— 克隆/提交视图零敏感文件。

**真实仓库复跑（隔离态护栏生效、无 skip 触发）**：
```
====================== 186 passed, 9 warnings in 18.11s =======================
```

**二次修复结论**：克隆后 `pytest` = **0 failed / 0 error（10 skip）**；本机 = **186 passed / 0 skipped**。配合「A 密钥零泄露」→ 仓库**可安全上传且可在别处使用**。
