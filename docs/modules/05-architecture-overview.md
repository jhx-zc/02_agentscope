# 模块五：架构总览

## 整体架构层次图

```
┌─────────────────────────────────────────────────────────────┐
│                   Layer 1: CLI 入口                          │
│                         cli.py                               │
│             解析 --config → asyncio.run()                    │
├─────────────────────────────────────────────────────────────┤
│                   Layer 2: Agent 核心                        │
│                    agentscope_course/                        │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ agent.py │  │ config.py│  │console.py│  │conversation. │  │
│  │ 组装工厂  │  │ 配置加载  │  │ 流式渲染  │  │py 对话循环   │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘  │
│       │             │             │               │         │
│  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴──────┐   │
│  │trace.py  │  │models/   │  │          │  │           │   │
│  │追踪日志   │  │ollama.py │  │          │  │           │   │
│  └──────────┘  │模型补丁   │  │          │  │           │   │
│                └──────────┘  │          │  │           │   │
├──────────────────────────────┴──────────┴──────────────┤
│                   Layer 3: 工具系统                      │
│                    agentscope_tools/                     │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │          agentscope_wrapper.py                    │   │
│  │   FunctionTool 注册中心 + 追踪装饰器               │   │
│  └──────────┬───────────────────────────┬───────────┘   │
│             │                           │               │
│     ┌───────┴──────────┐      ┌────────┴────────┐      │
│     │   ori_tools/     │      │  AgentScope 内建  │      │
│     │  原始工具实现     │      │  Task 工具        │      │
│     │                  │      │                  │      │
│     │ scanner.py  📂   │      │ TaskCreate       │      │
│     │ parser.py   📋   │      │ TaskGet          │      │
│     │ editor.py   ✏️   │      │ TaskList         │      │
│     │ formatter.py 🎨  │      │ TaskUpdate       │      │
│     │ memory.py   🧠   │      │                  │      │
│     └──────────────────┘      └──────────────────┘      │
├─────────────────────────────────────────────────────────┤
│                   Layer 4: 基础设施                      │
│                                                         │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────┐  │
│  │ config/  │  │ pyproject │  │ .env     │  │Ollama │  │
│  │ TOML 配置 │  │ .toml     │  │ 环境变量  │  │ 本地模型│  │
│  └──────────┘  └───────────┘  └──────────┘  └───────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 模块间依赖图

```
                    cli.py
                       │
                       ▼
                   agent.py
                  ┌───┴───┐
                  │       │
                  ▼       ▼
             config.py  models/ollama.py
                             │
                             ▼
                       AgentScope SDK
                     (agentscope 包)
                  ┌────────┼────────┐
                  │        │        │
                  ▼        ▼        ▼
           conversation.py  console.py  agentscope_wrapper.py
                │              │               │
                │              │               ▼
                │              │          ori_tools/*
                │              │          ┌───┬───┬───┬───┐
                │              │          │   │   │   │   │
                │              │     scanner/parser/editor/formatter/memory
                │              │
                └──────┬───────┘
                       ▼
                   trace.py
                       │
                       ▼
               .agentscope_traces/
               agentscope_events.jsonl
```

---

## 模块职责矩阵

| 层次 | 模块 | 文件 | 核心职责 | 行数 | 外部依赖 |
|------|------|------|---------|------|---------|
| 入口 | CLI | `cli.py` | 参数解析 + 启动循环 | 26 | `agent.py` |
| 核心 | 组装 | `agent.py` | Agent 创建 + 主循环 | 203 | `config`, `models`, `tools`, `trace` |
| 核心 | 配置 | `config.py` | TOML + .env 加载 | 51 | `tomllib`, `dotenv` |
| 核心 | 渲染 | `console.py` | 流式终端 UI | 678 | `rich` |
| 核心 | 对话 | `conversation.py` | 事件循环 + 确认 | 119 | `agentscope.event` |
| 核心 | 追踪 | `trace.py` | JSONL 日志 + diff | 538 | 标准库 |
| 核心 | 模型 | `models/ollama.py` | Ollama Bug 修复 | 141 | `agentscope.model` |
| 工具 | 注册 | `agentscope_wrapper.py` | 工具包装 + 分组 | 219 | `agentscope.tool` |
| 工具 | 扫描 | `ori_tools/scanner.py` | 目录扫描 | 89 | 标准库 |
| 工具 | 解析 | `ori_tools/parser.py` | Markdown 解析 | 241 | `markdown-it-py` |
| 工具 | 编辑 | `ori_tools/editor.py` | Markdown 编辑 | 183 | `parser` |
| 工具 | 格式化 | `ori_tools/formatter.py` | mdformat | 70 | `mdformat` |
| 工具 | 记忆 | `ori_tools/memory.py` | JSON 偏好存储 | 336 | 标准库 |

---

## 核心数据流：一次用户请求的完整路径

```
┌──────────────────────────────────────────────────────────┐
│ ① 用户输入                                               │
│ "帮我把 Test.md 整理一下"                                 │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ ② cli.py: ask_agent()                                    │
│    trace_recorder.start_turn(user_input)                 │
│    StreamConsoleRenderer(trace_recorder)                 │
│    reply_until_done(agent, UserMsg(user_input), renderer)│
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ ③ conversation.py: reply_until_done()                    │
│    for event in agent.reply_stream(next_input):          │
│      renderer.render(event)                               │
│                                                          │
│    事件流 → 控制台渲染 + 追踪记录                          │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ ④ agent.py: Agent.reply_stream()                         │
│    AgentScope 内部 ReAct 循环                             │
│                                                          │
│    思考: LLM 理解用户需求                                  │
│       ↓                                                  │
│    决策: 需要调用工具?                                     │
│       ├── 否 → 直接 LLM 回答                               │
│       └── 是 → 选择工具组 → 选择工具 → 填充参数             │
│              ↓                                            │
│    确认: RequireUserConfirmEvent                          │
│       └── conversation.py 自动放行 (confirmed=True)        │
│              ↓                                            │
│    执行: agentscope_wrapper.py 包装器                      │
│       ├── trace_recorder.begin_tool_execution()           │
│       ├── ori_tools 中的实际函数                           │
│       └── trace_recorder.end_tool_execution()             │
│              ↓                                            │
│    反馈: 工具结果 → LLM 继续思考                           │
│              ↓                                            │
│    输出: LLM 生成最终回答                                  │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ ⑤ console.py: StreamConsoleRenderer                      │
│    TextBlockDeltaEvent → 流式打印 🤖 Assistant: ...      │
│    ToolCallStartEvent → 🔧 Tool: name                    │
│    ToolCallDeltaEvent → args: 参数实时流入                │
│    ToolResultEndEvent → result: success                  │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│ ⑥ trace.py                                              │
│    agent.reply_stream 结束后:                             │
│    ├── 还有未完成任务? → UserMsg("继续")                   │
│    └── 全部完成 → 等待下一轮输入                           │
│    trace_recorder.end_turn() → 摘要更新                   │
└──────────────────────────────────────────────────────────┘
```

---

## AgentScope 事件流全览

```
agent.reply_stream() 产生的事件:
                        │
   ┌────────────────────┼────────────────────┐
   │                    │                    │
   ▼                    ▼                    ▼
TextBlockDelta      ToolCallStart        RequireUserConfirm
   │                    │                    │
   ▼                    ▼                    ▼
   ...              ToolCallDelta        UserConfirmResult
   │                    │                    │
   ▼                    ▼                    ▼
   ...              ToolCallEnd           ToolResultStart
                                            │
                                            ▼
                                        ToolResultTextDelta
                                            │
                                            ▼
                                        ToolResultDataDelta
                                            │
                                            ▼
                                        ToolResultEnd
```

LLM 可能在一轮回复中多次调用工具：
- 每次工具调用都走完整的事件序列
- 确认事件只在写操作前触发
- 所有事件都由 console.py 的 `render()` 方法路由到对应的渲染函数

---

## 上下文变量（ContextVar）机制

项目中通过 Python 的 `contextvars` 实现了异步上下文中的隐式参数传递：

```python
# trace.py 中定义
_CURRENT_RECORDER = contextvars.ContextVar("agentscope_trace_recorder")

# agent.py 中设置
with trace_recorder_context(trace_recorder):
    await reply_until_done(agent, msg, renderer)

# agentscope_wrapper.py 中读取
def wrapped(**kwargs):
    recorder = current_trace_recorder()
    if recorder is not None:
        execution = recorder.begin_tool_execution(func.__name__, kwargs)
    ...
```

**为什么用 ContextVar 而不是参数传递？**

- 工具包装器 `_wrap_tool_result` 是函数级装饰器，签名被 AgentScope 框架固定
- 无法向包装后的函数注入额外参数
- ContextVar 提供了不修改函数签名的上下文传递机制

---

## 边界与安全考量

### 文件操作安全

- **原子写入**：memory 使用临时文件 + `Path.replace()` 实现原子写入
- **仅操作 .md 文件**：scanner 过滤后缀，editor 也假设输入是 .md 文件
- **无网络操作**：所有文件操作限于本地文件系统

### 模型调用安全

- 本地 Ollama，无外部 API 调用
- 通过 `OLLAMA_HOST` 环境变量限制连接地址
- 无自动工具执行跨网络请求的路径

### 日志保护

- 文本截断保护（20000 字符文本 / 30000 字符 diff）
- 事件日志写入容错（OSError 时静默降级）
- 不记录密码等敏感信息（当前无认证凭据需要记录）
