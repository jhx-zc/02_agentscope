# 模块二：Agent 核心 — `agentscope_course/`

## 包概览

- **路径**: `src/agentscope_course/`
- **子模块数**: 5 个核心模块 + 1 个模型适配子包
- **职责**: Agent 的核心逻辑层——大脑(LLM) + 双手(工具) + 感知(事件流)

```
agentscope_course/
├── __init__.py           # 包声明
├── agent.py              # Agent 创建与编排（核心组装厂）
├── config.py             # 配置加载（TOML + .env）
├── console.py            # 终端渲染器（Codex 风格流式输出）
├── conversation.py       # 对话循环（确认处理 + 任务延续）
├── trace.py              # 结构化追踪日志（JSONL + Summary）
└── models/               # 模型适配子包
    ├── __init__.py
    └── ollama.py         # Ollama 模型补丁（修复工具调用 ID 冲突）
```

---

## 2.1 `agent.py` — Agent 创建与编排

- **行数**: 203 行
- **依赖**: `agentscope_course.*`（几乎所有子模块）+ `agentscope_tools`
- **对外接口**: `ask_agent()`, `create_agent()`, `create_model()`, `create_toolkit()`

### 职责

将"大脑"(模型)与"双手"(工具)组装成完整 Agent，并提供交互循环入口。

### 函数详解

#### `create_model(config) → ChatModelBase`

```
create_model()
  ├── load_dotenv()                    # 加载 .env 文件
  ├── 从环境变量 / config 读取参数：
  │   ├── OLLAMA_MODEL / model        # 模型名（默认 qwen3.5:4b-mlx）
  │   ├── stream                      # 是否流式（默认 True）
  │   ├── temperature                 # 创意程度
  │   ├── max_tokens                  # 最大 Token
  │   └── thinking_enable             # 是否启用思考链
  ├── 创建 PatchedOllamaChatModel.Parameters()
  ├── 可选 OLLAMA_HOST 配置 OllamaCredential()
  └── return PatchedOllamaChatModel()
```

**设计要点**:
- 使用 `PatchedOllamaChatModel`（见 2.6 节）而非 AgentScope 原生的 `OllamaChatModel`
- 参数优先级：环境变量 > 配置文件 > 默认值
- `_maybe_number()` 将字符串参数转为数字类型

#### `create_toolkit() → Toolkit`

```python
def create_toolkit():
    from agentscope_tools.agentscope_wrapper import create_markdown_toolkit
    return create_markdown_toolkit()
```

**设计要点**:
- 延迟导入（lazy import）避免启动时循环依赖
- 委托给 `agentscope_tools` 模块完成所有工具注册逻辑

#### `create_agent(config) → Agent`

```
create_agent()
  ├── load_config() → 加载 TOML
  ├── Agent(
  │     name=config["name"],
  │     system_prompt=config["system_prompt"],
  │     model=create_model(model_config),
  │     toolkit=create_toolkit(),
  │     react_config=ReActConfig(max_iters=N)
  │   )
  └── 注入初始用户记忆到 agent.state.context
```

**设计要点**:
- `max_iters` 控制单次任务最大思考步数（默认 20，配置中为 30）
- Agent 启动时自动注入 `init_user_memory()` 作为首次对话上下文
- `ReActConfig` 启用 AgentScope 的 ReAct 推理循环

#### `ask_agent(config_path) → None`

这是整个 Agent 的主循环入口：

```
ask_agent(path)
  ├── create_agent(load_config(path))
  ├── TraceRecorder() → 初始化追踪日志
  ├── WHILE LOOP:
  │   ├── input("🧑 You: ") 或 预填测试 prompt
  │   ├── 'quit' → 退出
  │   ├── trace_recorder.start_turn(user_input)
  │   ├── StreamConsoleRenderer(trace_recorder)
  │   ├── trace_recorder_context → 设置上下文变量
  │   ├── reply_until_done(agent, msg, renderer)
  │   └── EXCEPTION → trace_recorder.record_local_event("turn_error", ...)
  └── FINALLY: trace_recorder.close()
```

**设计要点**:
- 内置一个标准测试 prompt（30+ 行），用于快速验证 Agent 全流程
- `trace_recorder_context` 使用 `contextvars` 确保工具调用能追踪到对应的 recorder
- 异常被记录到 trace 后重新抛出（不静默吞掉）
- `KeyboardInterrupt/EOFError` 捕获后优雅退出

### 测试 Prompt 结构

`ask_agent()` 中的硬编码测试 prompt 包含 9 个步骤，覆盖了所有主要功能路径：

| 步骤 | 操作 | 涉及模块 |
|------|------|---------|
| 1 | 读取记忆中的文件 | memory → scanner |
| 2 | 使用 Plan Mode | task_management |
| 3 | 识别文档结构 | parser (markdown_outline) |
| 4 | 保护章节确认 | parser (markdown_get_section) |
| 5 | 读取指定章节 | parser |
| 6 | 重写风险章节 | editor (markdown_replace_section) |
| 7 | 插入新章节 | editor (markdown_insert_after_heading) |
| 8 | 更新任务状态 | editor (markdown_update_task_status) |
| 9 | 格式化检查 | formatter (markdown_check_format) |

---

## 2.2 `config.py` — 配置加载

- **行数**: 51 行
- **依赖**: `tomllib`（Python 3.11+ 内置）+ `dotenv`

### 职责

加载 TOML 配置文件和 `.env` 环境变量。

### 常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `PROJECT_ROOT` | `Path(__file__).resolve().parents[2]` | 项目根目录（`src/agentscope_course/` → `src/` → 根） |
| `DEFAULT_CONFIG_PATH` | `PROJECT_ROOT / "config/agentscope.toml"` | 默认配置文件路径 |
| `DEFAULT_ENV_PATH` | `PROJECT_ROOT / ".env"` | 默认环境变量文件 |

### 函数详解

| 函数 | 说明 | 关键细节 |
|------|------|---------|
| `load_dotenv(path)` | 加载 `.env` 但不覆盖已存在的环境变量 | `override=False` |
| `load_config(path)` | 加载 TOML 配置 | 支持 `AGENTSCOPE_CONFIG` 环境变量覆盖路径 |
| `_maybe_number(value)` | 字符串→数字类型转换 | `int > float > str` 优先级 |

### 配置优先级

```
--config 参数 > AGENTSCOPE 环境变量 > 默认 config/agentscope.toml > 不存在则返回 {}
```

---

## 2.3 `console.py` — 终端渲染器

- **行数**: 678 行（本项目最大的文件）
- **依赖**: `rich`（终端美化）+ `trace.py`
- **核心类**: `StreamConsoleRenderer`

### 职责

实现 Codex/Claude Code 风格的实时终端交互体验——文字流式输出、工具调用实时展示。

### 架构

```
StreamConsoleRenderer
  ├── 状态管理
  │   ├── _ToolRenderState  dataclass  ← 单个工具调用的渲染状态
  │   └── _ToolBatchState   dataclass  ← 一次 Agent 回复中的工具调用组
  │
  ├── 事件处理 (render 方法)
  │   ├── TextBlockDeltaEvent    → _render_text()         ← 文字流式输出
  │   ├── ToolCallStartEvent     → _render_tool_start()   ← 工具调用开始
  │   ├── ToolCallDeltaEvent     → _render_tool_args()     ← 参数实时流入
  │   ├── ToolCallEndEvent       → _render_tool_call_end() ← 参数收集完成
  │   ├── RequireUserConfirmEvent→ _render_tool_confirmation_request()
  │   ├── ToolResultStartEvent   → _render_tool_result_start()
  │   ├── ToolResultTextDeltaEvent→ _collect_tool_output()
  │   ├── ToolResultDataDeltaEvent→ _render_tool_data()
  │   └── ToolResultEndEvent     → _render_tool_result_end()
  │
  ├── 日志记录
  │   ├── _log_agent_event()     ← 记录 AgentScope 原始事件
  │   ├── _log_local_event()     ← 记录自定义事件（确认/阻塞/延续）
  │   └── _write_event_log()     ← 写入 agentscope_events.jsonl
  │
  └── Live 渲染
      ├── _start_live()          ← 启动 rich.Live（自刷新面板）
      ├── _refresh_live()        ← 刷新渲染
      ├── _stop_live()           ← 停止 Live，固定输出
      └── _render_active_batch() ← 构建工具调用面板（Tree → Panel）
```

### 工具调用渲染面板

当 Agent 发起工具调用时，终端上会显示一个 `rich.Panel`，使用树形结构展示：

```
┌──────────────────────────────────────────────┐
│ 🧰 Tool batch #1 · 2 calls                   │
│                                              │
│ 🔧 [1/2] markdown_outline · abc123...def     │
│   args: {"path": "Test.md"}                  │
│   status: running                            │
│                                              │
│ 🔧 [2/2] markdown_get_section · abc789...xyz │
│   args: {"path": "Test.md", ...}             │
│   status: finished                           │
│   result: success                            │
└──────────────────────────────────────────────┘
```

### Unicode 中文解码

`decode_unicode_chinese()` 函数专门处理工具参数中的 `\uXXXX` 编码，确保中文字符在终端上正常显示。

### 输出截断保护

| 常量 | 默认值 | 作用 |
|------|--------|------|
| `_MAX_TOOL_OUTPUT_LINES` | 24 | 工具输出最大预览行数 |
| `_MAX_TOOL_OUTPUT_CHARS` | 4000 | 工具输出最大预览字符 |
| `_EVENT_LOG_PREVIEW_CHARS` | 1000 | 事件日志单字段预览截断 |

### 事件序号追踪

每个事件获得自增的 `seq` 号和 `renderer_id`，便于后续分析和调试。

---

## 2.4 `conversation.py` — 对话循环

- **行数**: 119 行
- **依赖**: `agentscope.*`（事件类型）+ `console.py`
- **核心函数**: `reply_until_done()`

### 职责

管理 Agent 和用户之间的完整对话流程，处理确认请求和任务延续。

### 执行流程

```
reply_until_done(agent, user_msg, renderer)
  │
  ├── WHILE next_input is not None:
  │   ├── agent.reply_stream(next_input) → 事件流
  │   │   └── renderer.render(event) → 实时输出
  │   │
  │   ├── RequireUserConfirmEvent 出现
  │   │   └── _confirm_tool_calls() → 自动放行所有工具
  │   │       └── renderer.record_tool_permission()
  │   │
  │   ├── RequireExternalExecutionEvent 出现
  │   │   └── raise RuntimeError("CLI 无法执行外部工具")
  │   │
  │   └── 所有事件处理完毕：
  │       ├── 有待确认 → UserConfirmResultEvent 作为 next_input
  │       ├── 有未完成任务 → UserMsg("继续任务") 作为 next_input
  │       └── 全部完成 → renderer.close_turn(), next_input = None
  │
  └── 循环结束，等待下一次用户输入
```

### 确认机制（当前实现）

目前**所有工具调用自动放行**（`confirmed = True`），代码中保留了手动确认的注释代码：

```python
# 注释掉的手动确认代码
# renderer.pause_live()
# print(f"⚠️  Tool permission required: {tool_call.name}")
# answer = input("   Allow this tool call? [y/N]: ").strip().lower()
# confirmed = answer in {"y", "yes"}
```

### 任务延续机制

Agent 的 `state.tasks_context.tasks` 中如果有未完成的 Task（不是 `"completed"` 状态），会自动触发延续：

```python
next_input = UserMsg(
    name="user",
    content=f'not finished tasks: {task_ids}. Continue your job.'
)
```

---

## 2.5 `trace.py` — 结构化追踪日志

- **行数**: 538 行
- **依赖**: 标准库（`difflib`, `hashlib`, `json`, `contextvars`）
- **核心类**: `TraceRecorder`

### 职责

记录 Agent 每次运行的完整过程，生成 JSONL 格式的详细事件流和 JSON 格式的运行摘要。

### 架构

```
TraceRecorder
  ├── 运行生命周期
  │   ├── __init__()      → 创建 jsonl + summary 文件，写入 run_start
  │   ├── start_turn()    → 开始一轮对话
  │   ├── end_turn()      → 结束本轮，记录摘要
  │   └── close()         → 写入 run_end, 输出 summary.json
  │
  ├── 事件记录
  │   ├── record_agent_event()       ← AgentScope 原始事件
  │   ├── record_text_delta()        ← 助手文本增量
  │   ├── record_tool_call_start()   ← 工具调用开始
  │   ├── record_tool_call_args_delta() ← 工具参数流动
  │   ├── record_tool_call_ready()   ← 工具参数完整
  │   ├── record_confirmation_request() ← 确认请求
  │   └── record_local_event()       ← 自定义事件
  │
  ├── 工具执行追踪
  │   ├── begin_tool_execution()     → 快照 before 文件状态
  │   └── end_tool_execution()       → 对比 after，生成 diff
  │
  └── 辅助
      ├── pending_tool_calls 列表       ← 待匹配的工具调用
      └── _match_tool_call()            ← 按名称+参数匹配跟踪
```

### 文件结构

每次运行生成一对文件：

```
.agentscope_traces/
├── 20260608-081705-<run_id_prefix>.jsonl        ← 完整事件流
└── 20260608-081705-<run_id_prefix>.summary.json  ← 运行摘要
```

### JSONL 事件类型

| 事件 | 触发时机 | 关键字段 |
|------|---------|---------|
| `run_start` | 追踪器初始化 | `cwd`, `jsonl_path` |
| `turn_start` | 新用户输入 | `turn_index`, `user_input` |
| `turn_end` | 回复完成 | `assistant_text`, `file_changes` |
| `assistant_text_delta` | 文本流每片段 | `delta`, `delta_len` |
| `tool_call_start` | Agent 发出工具调用 | `tool_call_id`, `tool_name` |
| `tool_call_ready` | 参数收集完成 | `args` (已解析 JSON) |
| `tool_execution_start` | 工具实际执行前 | `execution_id`, `candidate_paths` |
| `tool_execution_end` | 工具执行完成 | `status`, `result`, `file_changes` |
| `confirmation_request` | 需要用户确认 | `tool_calls` 列表 |
| `agent_event` | 渲染器收到的原始事件 | `event_class`, `fields` |
| `run_end` | 追踪器关闭 | `turn_count` |

### 文件变更追踪（Diff）

当工具修改文件时，`trace.py` 会自动：

1. 在执行前对候选路径做快照（`FileSnapshot`：`path`, `sha256`, `text`）
2. 执行后重新快照
3. 对比生成 unified diff
4. 记录到 `tool_execution_end` 事件的 `file_changes` 字段

```python
# diff 示例
--- a/Test.md
+++ b/Test.md
@@ -1,6 +1,8 @@
 # 标题
+新内容
```

### 上下文变量（ContextVar）

```python
_CURRENT_RECORDER = contextvars.ContextVar(
    "agentscope_trace_recorder", default=None
)
```

通过 `trace_recorder_context()` 上下文管理器设置，确保工具包装器可以无参获取当前 recorder：

```python
def current_trace_recorder() -> TraceRecorder | None:
    return _CURRENT_RECORDER.get()
```

### 剪枝保护

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `MAX_RECORDED_TEXT_CHARS` | 20000 | 单段文本最大记录长度 |
| `MAX_DIFF_CHARS` | 30000 | 单次 diff 最大长度 |

---

## 2.6 `models/ollama.py` — 模型补丁

- **行数**: 141 行
- **依赖**: `agentscope.model.OllamaChatModel`
- **核心类**: `PatchedOllamaChatModel`

### 职责

修复 AgentScope 官方 Ollama 适配器的一个 Bug：当同一轮回复中多次调用同一个工具时，工具调用 ID 会重复，导致运行时无法区分多个同名工具调用。

### Bug 根因

AgentScope 原生实现使用 `idx`（工具在列表中的索引）和工具名拼接 ID。但如果同一个工具被调用多次，每次调用的索引值相同，导致 ID 重复。

### 修复方式

```python
# AgentScope 原生实现（有 Bug）
tool_id = f"{idx}_{function.name}"  # 不同轮次同工具同索引时冲突！

# PatchedOllamaChatModel 修复方案
tool_id = f"{response_id}_{idx}_{function.name}"  # 加入 response_id 区分
```

`response_id` 来自 Ollama API 响应的 `id` 字段，每次请求都不同，确保了工具调用 ID 的全局唯一性。

### 实现细节

`PatchedOllamaChatModel` 重写了两个方法：

| 方法 | 用途 | 修改要点 |
|------|------|---------|
| `_parse_stream_response()` | 处理流式响应 | 每个工具块 ID 中加入 `response_id` |
| `_parse_completion_response()` | 处理非流式响应 | 同上 |

两个方法都保持了 AgentScope 完整的响应结构：
- `TextBlock` — 文本内容
- `ThinkingBlock` — 思考链内容（当 `thinking_enable=True`）
- `ToolCallBlock` — 工具调用（修复后的 ID）
- `ChatUsage` — Token 用量统计

### 教学内容价值

这个模块是课程的实用亮点之一，"即使是最流行的框架也可能有 Bug，理解原理才能修复它"。
