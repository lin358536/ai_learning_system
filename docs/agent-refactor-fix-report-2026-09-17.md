# 智途校园 · LangChain Agent 重构 — 缺陷修复报告（P1 / P2 / P3）

- **修复人**：寇豆码（software-engineer）
- **日期**：2026-09-17
- **输入**：`docs/agent-refactor-test-report-2026-09-17.md`（QA 严过关 的真实密钥验收报告）
- **变更范围**：仅 4 个文件（`.env`、`app/api/chat.py`、`app/skills/plan/prompts/plan_system.yaml`、`app/skills/resume/prompts/resume_system.yaml`）+ 新增非源码验证脚本（`backend/_fix_verify/`）
- **备份铁律**：所有既有文件改动前均已备份，**未覆盖**任何既有 `.bak`

---

## 一、备份清单（铁律核对）

| 被改文件 | 本轮备份（带日期） | 既有备份（未覆盖，09-16 留下） |
|---|---|---|
| `backend/.env` | `.env.bak.20260917`（1170B, 13:08） | `.env.bak`（621B, 09-16 17:40）✔保留 |
| `backend/app/api/chat.py` | `app/api/chat.py.bak.20260917`（38481B, 13:09） | `app/api/chat.py.bak`（31855B, 09-16 17:40）✔保留 |
| `backend/app/skills/plan/prompts/plan_system.yaml` | `plan_system.yaml.bak.20260917`（2396B, 13:16） | 无 |
| `backend/app/skills/resume/prompts/resume_system.yaml` | `resume_system.yaml.bak.20260917`（2678B, 13:16） | 无 |

---

## 二、P1【高】模型 ID 非法 — 已修复

- **文件**：`backend/.env` 第 30 行
- **修改**：`DEEPSEEK_MODEL=deepseek-v4.1-flash` → `DEEPSEEK_MODEL=deepseek-flash`
- **范围控制**：`diff .env.bak.20260917 .env` 仅 1 行差异（第 30 行），DB/JWT/Coze/Qwen/SMTP 等一律未动
- **验证**（`_fix_verify/verify_p1_p2.py`）：`get_llm().ainvoke("你好")` → `'你好！很高兴见到你 😊 ...'`（返回非空中文），**PASS**

---

## 三、P2【中】done 事件 intent 恒为 chat — 已修复

- **文件**：`app/api/chat.py:235`（修复后为 237 行）
- **修改**：
  ```python
  # 修复前
  output = event.get("output")
  # 修复后（含中文注释说明事件负载嵌套）
  output = event.get("data", {}).get("output")
  ```
- **同类遗漏核查**：`grep event.get(` 全量核查同函数取值点——
  - `chat.py:220  ev_type = event.get("event")` → astream_events 顶层键，**正确无需改**；
  - `chat.py:223  chunk = event.get("data", {}).get("chunk")` → **已正确走 `event["data"]`，未动**；
  - `chat.py:118/121/126/127/128/130` → 属 **Coze 通道自建事件字典**（非 astream_events），顶层键取值正确，**未动**。
  结论：QA 报告的 235 行为唯一同类遗漏，无其他遗漏。
- **验证**：
  1. **事件结构验证**（同构 StateGraph 复现）：
     - `on_chain_end` 顶层 `event["output"]` 非空次数 = **0**（证明旧写法恒 None）；
     - `event["data"]["output"]` 命中 `final_content`+`intent` 次数 = **3**（新写法可取到）；
     - **PASS**
  2. **端到端验证**（真实 plan 技能 + 真实模型跑 `build_agent_graph`，`--e2e`）：
     - 推导出的 `done.intent = 'generate_plan'`（期望 `generate_plan`）；
     - 日志：`[node_respond] skill=plan intent=generate_plan content_len=6346`；
     - **PASS**
- **连带修复**：`full_content` 兜底（`chat.py:240` 原 P4）随本修复一并生效。

---

## 四、P3【中·非确定性】规划 JSON 解析不健壮 — 已按「先度量、只改提示词」处置

### 4.1 基线度量（修复前）

- 方法：真实模型 + plan 技能 system prompt（`get_skill_engine().route("generate_plan").get_prompt(ctx)`）+ 真实用户消息「帮我制定学习规划」，采样 **12 轮**，每轮输出喂给生产真实解析器 `app.api.chat._extract_plan_from_json`
- 结果：**成功 11 / 失败 1（失败率 8.3%，1/12）**
- 失败样本（`_fix_verify/samples_plan_before.txt`）关键特征：
  - 输出以 ```` ```json ```` 代码块包裹 + 前置说明句；
  - **字符串值内出现未转义英文双引号**（致命）：
    ```
    "总述说明": "把项目从"能跑"升级为"能上线、能展示"，补齐后端、容器化与部署能力…"
    ```
  - `json.loads` 直接失败；`re.search(r'\{[\s\S]*\}')` 提取后再次失败 → 返回 None。

### 4.2 修复（仅提示词侧，解析器零改动）

- 文件：`app/skills/plan/prompts/plan_system.yaml`、`app/skills/resume/prompts/resume_system.yaml`
- 在两份 prompt 的「## 输出要求」下**新增**「### 输出格式硬性约束（必须全部遵守）」6 条：
  1. 只输出 JSON 本体，首字符 `{`、末字符 `}`，禁止任何前置/后置说明文字；
  2. 禁止 ```` ```json ```` / ```` ``` ```` 代码块包裹；
  3. **字符串值内禁止英文双引号 `"`，需要引号时用中文引号「」**；
  4. 英文双引号只能作键/值定界符，不得出现在字符串内容中间；
  5. 输出必须能被 `json.loads` 一次性解析（无注释/尾随逗号/省略号）；
  6. 键名与嵌套结构与模板完全一致，不得增删/改名。
  并在「## 注意事项」各加一条呼应；收尾「询问/直出」段补充「该轮只输出 JSON 本体」。
- **`diff` 证明为纯追加**，**未改动任何 JSON 键结构**（`{"<标题>":{"阶段一":{"阶段名称","总述说明","目标","任务清单"}}}` / `{"求职简历":{"基本信息",…}}` 原样保留），save-plan/save-resume 解析依赖不受影响。
- YAML 语法与渲染校验：`yaml.safe_load` 正常，`get_skill_engine().route(...).get_prompt(...)` 渲染正常且含新约束块（plan 1248 字、resume 1467 字）。

### 4.3 复测（修复后）

- 同法采样 **12 轮**：**成功 12 / 失败 0（失败率 0.0%，0/12）**
- 样本：`_fix_verify/samples_plan_after.txt`（无失败样本）；摘要 `summary_plan_before.txt` / `summary_plan_after.txt`

| 阶段 | 成功 | 失败 | 失败率 |
|---|---|---|---|
| 修复前 | 11 | 1 | 8.3% |
| 修复后 | 12 | 0 | 0.0% |

> **红线遵守**：全程未改 `_extract_plan_from_json` / `_extract_resume_from_json`。修复后失败率 0%（<10% 阈值），无需升级。

---

## 五、回归结果（`pytest tests/agent_refactor -v`）

- **结果**：**181 passed / 5 failed**（两次运行一致，约 30–39s）
- 说明：QA 基线为 `183/3`；由于 **P1 修复后真实模型恢复可用 + `.env` 事件注入副作用**，失败集合从 3 变为 5，**均为测试侧前置/环境问题，非源码回归**。

| # | 失败用例 | 归因 |
|---|---|---|
| 1 | `test_imports.py::test_get_llm_empty_key_raises_zhitu_error` | 前置 `DEEPSEEK_API_KEY == ""` 已失效（QA 已报，P6） |
| 2 | `test_graph.py::TestGraphRuntime::test_empty_key_error_propagates` | 同为空 key 前置失效（QA 已报） |
| 3 | `test_api_langgraph.py::TestChatEmptyKey::test_chat_returns_error_event_not_500` | 空 key 前置失效（QA 已报） |
| 4 | `test_api_langgraph.py::TestChatEmptyKey::test_chat_with_explicit_conversation_id` | **同类**：断言期望 error 事件；真实 key+合法模型下正常返回 text+done → 失败 |
| 5 | `test_api_coze_fallback.py::test_coze_fallback_error_event_not_500` | 见下方根因，**测试夹具/环境串扰** |

### #5 根因（已定位到确定机制）

- **现象**：该用例单独运行 **PASS**；与 `test_save_parser_compat.py`（或全量）同跑则 **FAIL**，断言收到的却是 **langgraph 通道**的聊天回复（`server_8124.log` 显示 `node_call_model`/`node_respond` 日志）。
- **根因**：`app/services/coze_client.py:14-16` 在 **import 时调用 `load_dotenv()`**，把 `.env` 内容注入 `os.environ`（实测：`import app.api.chat` 后 `'AGENT_BACKEND' in os.environ → True`，值 `langgraph`）。而 `test_api_coze_fallback` 夹具**通过改写 `.env` 文件**切换通道，`conftest.start_server` 又用 `env=_clean_env()`（= `os.environ`）启动子进程——pydantic 的**环境变量优先级高于 `.env` 文件**，故子进程仍按 `AGENT_BACKEND=langgraph` 走 LangGraph 通道。
- **为何此前 PASS、现在 FAIL**：改动前 `.env` 模型 ID 非法，LangGraph 通道恒返回 400 → 恰好产出 error 事件 → 用例“侥幸通过”；P1 修复后模型合法，LangGraph 通道正常返回 text+done → 断言失败。
- **结论**：`coze_client.load_dotenv()` 属零改动文件（任务书 `ZERO_CHANGE_FILES`），**不在本次修复范围**；夹具应按环境变量切换通道（或 `monkeypatch.delenv("AGENT_BACKEND")` / 子进程 env 显式覆盖）。**建议移交 QA 处理**。
- **旁证**：独立探针（`_fix_verify/check_coze_channel.py`，以 `AGENT_BACKEND=coze` 启动真实服务）→ 返回 `{'type':'error','message':'Coze 调用异常: code: 4101 ...'}`，**Coze 通道本身完好**。

---

## 六、遗留与风险

1. **`app/core/config.py:39` 默认值仍为非法 `deepseek-v4.1-flash`**（本次按指令仅改 `.env`）。若 `.env` 缺失 `DEEPSEEK_MODEL`，将回落非法默认值再次 400。**建议将默认值同步改为 `deepseek-flash`**（需二次授权）。
2. **`coze_client.load_dotenv()` 的全局副作用**：import 即污染 `os.environ`，影响所有子进程/夹具的配置优先级。属零改动文件，仅记录，建议排期评估。
3. **P3 样本量**：各 12 轮。修复后 0 失败，但 LLM 非确定性仍在，建议 QA 在 T04/T05 复测时继续多轮采样监控。
4. **回归套件 5 个失败全部在测试侧**：按指令**未改任何测试文件**，交 QA 维护（空 key 用例改 `monkeypatch` 注入空 key + `reset_llm()`；coze 夹具改环境变量切换）。
5. `error` 事件 message 截断（原 P5，`str(e)[:200]`）与只读兜底语义（原 P4 随 P2 已修）等低危项未动，属可选优化。

---

## 七、本轮新增非源码验证脚本（`backend/_fix_verify/`）

| 文件 | 用途 |
|---|---|
| `verify_p1_p2.py` | P1 冒烟 + P2 事件结构 + P2 端到端 intent（`--e2e`） |
| `sample_plan_json.py` | P3 采样（`--rounds N --tag before/after`），统计解析失败率、落盘失败样本 |
| `check_coze_channel.py` | Coze 通道独立探针（env / file 两种切换方式） |
| `samples_plan_before.txt` / `summary_plan_before.txt` | 修复前失败样本与摘要 |
| `samples_plan_after.txt` / `summary_plan_after.txt` | 修复后样本与摘要 |

---

## 八、补充修复：`config.py` 默认模型 ID（主理人二次授权后补做）

> 承接「六、遗留与风险」第 1 项。此步在收到主理人授权后单独补做。

- **备份**：`app/core/config.py` → `app/core/config.py.bak.20260917`（1990B）；既有 `app/core/config.py.bak`（1242B, 09-16）**未覆盖**
- **改动**：`app/core/config.py:39`
  ```
  - DEEPSEEK_MODEL: str = "deepseek-v4.1-flash"   # 模型名可配置…
  + DEEPSEEK_MODEL: str = "deepseek-flash"        # 模型名可配置…（默认须为平台合法 ID）
  ```
- **范围核对**：逐行比对 `config.py.bak.20260917` vs `config.py` → **62 行对 62 行，仅第 39 行不同**，其余字段（DB/JWT/Coze/Qwen/SMTP/Agent）一律未动
- **其它硬编码兜底核查**（`grep deepseek|MODEL` 全量）：
  - `app/llm/llm_provider.py:29` `model=settings.DEEPSEEK_MODEL` —— **无硬编码兜底**，无需改
  - `app/llm/model_config.py` —— 仅温度/最大 token 与降级常量，**无模型名**，无需改
  - 其余 `MODEL` 命中均为 Qwen 段（`QWEN_MODEL`，与本次无关），未动
  - **结论：仅 `config.py:39` 一处需要修改，无其它硬编码模型兜底值**
- **隔离验证**（不改 `.env`，用 `_env_file=None` 绕过 .env 读默认值）：
  ```
  venv\Scripts\python.exe -c "import sys;sys.path.insert(0,'.');from app.core.config import Settings; print(Settings(_env_file=None).DEEPSEEK_MODEL)"
  → deepseek-flash        # 默认值已合法
  venv\Scripts\python.exe -c "import sys;sys.path.insert(0,'.');from app.core.config import get_settings; print(get_settings().DEEPSEEK_MODEL)"
  → deepseek-flash        # 读 .env 后亦一致
  ```
  **PASS**：默认值与 `.env` 取值一致，均为合法 `deepseek-flash`；即便 `.env` 缺失 `DEEPSEEK_MODEL` 也不再回落非法值。
- **回归复跑**：改动后重跑 `pytest tests/agent_refactor` = **181 passed / 5 failed**（与改动前逐项一致），本步未引入任何新失败。

