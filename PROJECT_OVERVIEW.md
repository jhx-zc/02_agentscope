# 02_agentscope — 从0到1搭建你的第一个 Agent

> 面向初学者的 Agent 教学项目。基于 **AgentScope 框架**，用本地模型（Ollama）搭建一个能处理 Markdown 文件的智能助手。
>
> **一句话定位**：这门课教你理解 Agent 的核心原理，亲手运行一个"会思考、能动手"的 AI 智能体。认识企业级项目需要什么样的日志系统、如何分析和优化，在遇到第三方库BUG该如何优雅的解决。

---

## 目录

1. [项目概述](#1-项目概述)
2. [快速上手](#2-快速上手)
3. [项目结构总览](#3-项目结构总览)
4. [模块详解](#4-模块详解)
   - [模块一：CLI 入口 — `cli.py`](#模块一cli-入口---clipy)
   - [模块二：Agent 核心 — `agentscope_course/`](#模块二agent-核心---agentscope_course)
   - [模块三：工具系统 — `agentscope_tools/`](#模块三工具系统---agentscope_tools)
   - [模块四：工具实现 — `ori_tools/`](#模块四工具实现---ori_tools)
5. [运行流程一张图](#5-运行流程一张图)
6. [配置说明](#6-配置说明)
7. [常见问题](#7-常见问题)

---

## 1. 项目概述

### 1.1 这是什么项目？

这是一个**教学项目**，目标是让你：

1. **理解 Agent 的核心原理**（LLM + 工具 + 自主决策）
2. **亲手运行一个真正的 Agent**（不是模拟器，是真的在干活）
3. **看到 Agent 的完整工作过程**（每步都展示给你看）

### 1.2 它能做什么？

这个 Agent 是一个 **Markdown 文件助手**，可以：

| 功能 | 说明 | 像什么 |
|------|------|--------|
| 扫描文件 | 查看目录下有哪些 Markdown 文件 | 🧐 眼睛 |
| 提取大纲 | 分析文档的标题结构 | 📋 快速浏览 |
| 读取章节 | 读取指定章节的内容 | 📖 翻到某一页 |
| 替换章节 | 替换某个章节的全部内容 | ✏️ 撕掉一页重写 |
| 插入内容 | 在标题后插入新内容 | ➕ 加一页 |
| 更新任务 | 修改任务列表的勾选状态 | ✅ 勾选待办 |
| 格式化 | 自动排版 Markdown 文件 | 🎨 排版工人 |
| 记忆偏好 | 记住你的使用偏好 | 🧠 短期记忆 |

### 1.3 和小龙虾（Manus）有什么区别？

**原理一模一样，只是工具数量不同。**

```
                小龙虾（Manus）              我们的 Agent
工具数量：      几十个                        9 个
能力范围：      研究、编程、数据分析             Markdown 文件处理
核心原理：      LLM + 工具 + 自主决策            LLM + 工具 + 自主决策
```

理解了这个项目，你就理解了小龙虾这类产品背后的底层逻辑。

---

## 2. 快速上手

### 2.1 环境要求

- **Python 3.10+**（推荐 3.12 或 3.14）
- **Ollama**（本地运行大模型）
- 一个终端（命令行窗口）

### 2.2 安装步骤

```bash
# 1. 进入项目目录
cd 02_agentscope

# 2. 安装依赖
pip install -r requirements.txt
# 或用 uv（更快）：
# uv sync

# 3. 确认 Ollama 服务运行中
ollama serve

# 4. 下载默认模型
ollama pull qwen3.5:4b-mlx
```

### 2.3 运行 Agent

```bash
# 方式一：Python 模块
python -m src.cli

# 方式二：快捷命令
uv run course-agent
```

看到以下界面就说明启动成功了：

```
==================================================
🤖 Agent已就绪 (输入 'quit' 退出)
==================================================

🧑 You:
```

### 2.4 试试这些命令

```
🧑 You: 你好！请介绍一下你自己
🧑 You: 看看当前目录下有哪些 Markdown 文件
🧑 You: 帮我看看 Test.md 的大纲
🧑 You: 把 Test.md 第5个任务标记为完成
```

---

## 3. 项目结构总览

```
02_agentscope/
│
├── src/                                    # 源代码
│   ├── cli.py                             # 🚪 CLI 入口（启动 Agent）
│   │
│   ├── agentscope_course/                 # 🧠 Agent 核心逻辑
│   │   ├── __init__.py                    # 包声明
│   │   ├── agent.py                       # 创建 Agent（大脑+工具）
│   │   ├── config.py                      # 配置加载（TOML + 环境变量）
│   │   ├── console.py                     # 终端渲染（流式输出+工具展示）
│   │   ├── conversation.py                # 对话循环（处理确认请求）
│   │   ├── trace.py                       # 追踪日志（记录每次运行）
│   │   └── models/                        # 模型适配
│   │       ├── __init__.py
│   │       └── ollama.py                  # Ollama 模型补丁
│   │
│   └── agentscope_tools/                  # 🛠️ 工具系统
│       ├── __init__.py
│       ├── agentscope_wrapper.py          # 工具包装（注册到 AgentScope）
│       ├── editor.py                      # 编辑器（兼容重导出）
│       ├── formatter.py                   # 格式化（兼容重导出）
│       ├── markdown.py                    # 解析器（兼容重导出）
│       ├── memory.py                      # 记忆工具（兼容重导出）
│       ├── parser.py                      # 解析器（兼容重导出）
│       │
│       └── ori_tools/                     # 📦 工具原始实现
│           ├── __init__.py                # 统一导出
│           ├── parser.py                  # Markdown 解析（大纲/章节/任务）
│           ├── editor.py                  # Markdown 编辑（替换/插入/更新）
│           ├── formatter.py               # Markdown 格式化（mdformat）
│           ├── scanner.py                 # 目录扫描器
│           └── memory.py                  # JSON 用户记忆
│
├── config/                                # ⚙️ 配置文件
│   ├── agentscope.toml                    # Agent 配置（默认）
│   └── agentscope.example.toml            # 配置示例
│
├── .env.example                           # 环境变量模板
├── course-content.md                      # 📚 课程讲义（7章）
├── pyproject.toml                         # 项目元数据和依赖
├── AGENTS.md                              # 教学说明
├── task_demo.md                           # 课堂演示场景设计
├── Test.md                                # 演示用测试文档
└── README.md
```

---

## 4. 模块详解

### 模块一：CLI 入口 — `cli.py`

**作用**：程序启动的第一个入口。解析命令行参数，启动 Agent 对话。

```python
def main():
    # 1. 解析 --config 参数（指定配置文件路径）
    # 2. 调用 ask_agent() 启动交互循环
    # 3. 你在终端看到的就是这个循环
```

**对应章节**：第 1 章《Hello Agent! — 让你的第一个 Agent 跑起来》

**关键理解**：这个文件只有 26 行，因为它只负责"启动"——真正的逻辑在其他模块里。

---

### 模块二：Agent 核心 — `agentscope_course/`

#### `agent.py` — 创建 Agent

**作用**：把"大脑"（模型）和"双手"（工具）组装在一起，生成一个完整的 Agent。

```
create_model()      → 连接 Ollama 本地模型（大脑）
create_toolkit()    → 注册 Markdown 工具（双手）
create_agent()      → 组装成 Agent（完整的人）
ask_agent()         → 进入对话循环（开始工作）
```

**对应章节**：第 2 章《Agent 的大脑 — 大语言模型在思考什么》

**关键参数**（来自 `config/agentscope.toml`）：

| 参数 | 默认值 | 作用 |
|------|--------|------|
| `model` | `qwen3.5:4b-mlx` | 使用的模型 |
| `temperature` | `0.1` | 创意程度（0=严谨，1=平衡，2=创意） |
| `max_iters` | `30` | 单次任务最大思考步数 |
| `system_prompt` | 见配置文件 | Agent 的"人设" |

#### `config.py` — 配置加载

**作用**：加载 `config/agentscope.toml` 和 `.env` 环境变量。

- 配置文件路径：项目根目录的 `config/agentscope.toml`
- 环境变量文件：项目根目录的 `.env`
- 支持通过 `--config` 参数指定自定义配置

#### `console.py` — 终端渲染器

**作用**：把 Agent 的"思考过程"实时展示在终端上。这是实现 **Codex/Claude Code 风格交互** 的核心。

**对应章节**：第 5 章《看得见的思考 — Codex 风格交互体验》

它处理四种事件：

```
🤖 Assistant: 你好！           ← 文字流式输出（TextBlockDeltaEvent）
🔧 Tool: scan_directory        ← 工具调用开始（ToolCallStartEvent）
   args: {...}                 ← 参数实时流入（ToolCallDeltaEvent）
   result: success             ← 工具执行完成（ToolResultEndEvent）
⚠️ 需要你确认：允许吗？        ← 权限请求（RequireUserConfirmEvent）
```

**设计亮点**：

- **实时性**：文字"流"出来，不是等全部生成再显示
- **透明性**：工具调用、参数、结果全部展示
- **区分度**：🤖 表示回答，🔧 表示工具，⚠️ 表示权限请求

#### `conversation.py` — 对话循环

**作用**：管理 Agent 和用户之间的完整对话流程。

```
用户输入 → Agent 回复（可能调用多个工具）
         → 处理确认请求 → 继续回复
         → 检查任务是否完成 → 继续或结束
```

**特殊机制**：

1. **工具确认**：写操作工具需要确认（当前版本自动放行，可配置为手动确认）
2. **任务延续**：如果 Agent 有未完成的任务，会自动触发继续执行
3. **错误处理**：捕获异常、记录日志、安全退出

#### `trace.py` — 追踪日志

**作用**：记录 Agent 每次运行的完整过程，生成 JSONL 日志文件。

```
每次运行生成两个文件：
  .agentscope_traces/20260608-081705-xxxx.jsonl      ← 完整事件流
  .agentscope_traces/20260608-081705-xxxx.summary.json ← 摘要
```

**记录内容**：

- 每轮对话的用户输入
- Agent 的文本输出（限制 20000 字符）
- 每次工具调用的参数和结果
- 文件修改的前后对比（diff）
- 错误信息

#### `models/ollama.py` — 模型补丁

**作用**：修复 AgentScope 官方 Ollama 适配器的一个 bug —— 当同一轮回复中多次调用同一个工具时，工具调用 ID 会重复。

**修复方式**：用 `response_id + 序号 + 工具名` 生成唯一的工具调用 ID，确保不冲突。

---

### 模块三：工具系统 — `agentscope_tools/`

#### `agentscope_wrapper.py` — 工具注册中心

**作用**：把普通的 Python 函数包装成 Agent 能用的"工具"，注册到 AgentScope。

**工具分组**：

| 工具组 | 包含工具 | 类型 | 作用 |
|--------|---------|------|------|
| `markdown_read` | 扫描、大纲、章节读取、检查格式 | 📖 只读 | 安全，不需要确认 |
| `markdown_write` | 替换章节、插入内容、格式化 | ✏️ 写操作 | 需要用户确认 |
| `memory` | 保存/读取/删除偏好 | 🧠 记忆 | 读取自动，写入需确认 |
| `task_management` | TaskCreate/TaskGet/TaskList/TaskUpdate | 📋 任务管理 | Agent 内部使用 |

**为什么分组？**

- 更清晰：Agent 根据任务激活对应的工具组
- 更安全：写操作工具不会和只读工具混在一起
- 更高效：Agent 不需要从一堆工具里筛选

---

### 模块四：工具实现 — `ori_tools/`

这里是 9 个工具的**原始实现**，每个工具就是一个普通的 Python 函数加上类型注解和文档字符串。

#### `parser.py` — 解析器

| 工具 | 作用 | 技术要点 |
|------|------|---------|
| `markdown_outline` | 提取文档大纲（标题树） | 用 `markdown-it` 解析，用栈构建树结构 |
| `markdown_get_section` | 读取指定章节内容 | 支持同标题出现多次（`occurrence` 参数） |
| `markdown_list_tasks` | 列出所有任务项 | 正则匹配 `[x]` 和 `[ ]` 格式 |
| `iter_outline` | 把大纲树展平为列表 | 深度优先遍历 |

**技术亮点**：

- 使用 `markdown-it-py`（专业的 Markdown 解析器）而不是正则
- 支持标题层级嵌套，精确计算每个章节的起止行号
- 支持同标题名多次出现（通过 `occurrence` 参数定位）

#### `editor.py` — 编辑器

| 工具 | 作用 |
|------|------|
| `markdown_replace_section` | 替换某个章节的全部内容 |
| `markdown_insert_after_heading` | 在指定标题后插入新内容 |
| `markdown_update_task_status` | 修改任务列表的勾选状态 |

**设计原则**：

- 基于**行号**操作，不是全文正则替换
- 保持文件其他部分不变（最小修改原则）
- 返回详细的修改信息（行号范围、差异统计）

#### `formatter.py` — 格式化器

| 工具 | 作用 |
|------|------|
| `markdown_format_file` | 用 `mdformat` 格式化文件 |
| `markdown_check_format` | 检查文件是否已格式化 |

**为什么单独放**：`mdformat` 可能重写整篇文档的空白、表格对齐和列表间距，不应和局部读写混在一起。

#### `scanner.py` — 扫描器

| 工具 | 作用 |
|------|------|
| `markdown_scan_directory` | 扫描目录中的 Markdown 文件 |

**关键设计**：

- 默认扫描 `.md` 和 `.markdown` 后缀
- 默认跳过隐藏文件/目录（以 `.` 开头）
- 返回绝对路径，供其他工具直接使用

#### `memory.py` — 用户记忆

| 工具 | 作用 |
|------|------|
| `user_memory_save_preference` | 保存偏好 |
| `user_memory_get_preference` | 读取偏好 |
| `user_memory_list_preferences` | 列出所有偏好 |
| `user_memory_delete_preference` | 删除偏好 |
| `user_memory_clear_preferences` | 清空所有偏好 |
| `user_memory_outline` | 查看偏好概览（不加载完整内容） |
| `hard_user_memories` | 获取硬性规则记忆 |

**存储方式**：JSON 文件 `.agentscope_memory/user_preferences.json`

**安全设计**：
- `clear_preferences` 需要 `confirm=True` 参数防误操作
- 保存时用临时文件 + 原子替换，防止写中断导致数据损坏
- `outline` 默认不返回完整值，保护隐私

---

## 5. 运行流程一张图

```
你输入："帮我把 Test.md 整理一下"
            │
            ▼
┌───────────────────────────────────────┐
│            Agent 循环                 │
│                                       │
│  ① 感知 cli.py                        │
│     接收你的输入                        │
│      ↓                                │
│  ② 思考 agent.py → ollama.py          │
│     LLM 理解任务，决定做什么             │
│      ↓                                │
│  ③ 决策                               │
│     ├─ 不需要工具 → 直接生成回答         │
│     └─ 需要工具 →                      │
│          ├─ 选工具（大纲/章节/替换...）  │
│          ├─ 填参数                     │
│          ├─ 确认（写操作需要你点头）      │
│          ├─ 执行（ori_tools 里的函数）   │
│          ├─ 记录（trace.py 写日志）     │
│          └─ 回到 ②（继续思考）          │
│      ↓                                │
│  ④ 输出 console.py                    │
│     实时显示文字和工具调用               │
│      ↓                                │
│  ⑤ 收尾 conversation.py               │
│     检查任务是否全部完成                 │
│     没完成 → 继续循环                   │
│     全完成 → 等待你的下一句话            │
│                                       │
└───────────────────────────────────────┘
            │
            ▼
你看到：Agent 的回答和工具调用过程
```

---

## 6. 配置说明

### 6.1 主要配置项（`config/agentscope.toml`）

```toml
[agent]
name = "course_assistant"        # Agent 名字
system_prompt = "..."            # Agent 人设
max_iters = 30                   # 最大思考步数

[model]
model = "qwen3.5:4b-mlx"        # 模型名称
stream = true                     # 是否流式输出
temperature = 0.1                # 创意程度
thinking_enable = false          # 是否启用思考链
```

### 6.2 环境变量（`.env`）

```
# Ollama 服务地址（默认连接本机）
OLLAMA_HOST=http://localhost:11434

# 默认模型（可覆盖配置文件）
OLLAMA_MODEL=qwen3.5:9b-mlx

# 追踪日志配置
AGENTSCOPE_TRACE_DIR=.agentscope_traces
AGENTSCOPE_TRACE_TEXT_CHARS=20000
AGENTSCOPE_TRACE_DIFF_CHARS=30000

# 事件日志
AGENTSCOPE_EVENT_LOG=agentscope_events.jsonl
```

---

## 7. 常见问题

### Q：为什么 Agent 回答得很慢？

因为 Agent 不是直接回答，而是要经历"思考→决策→调用工具→读取结果→再思考"的完整循环。每次工具调用都需要和 LLM 通信，所以比纯聊天慢。这是正常现象。

### Q：为什么不用云 API 而用本地模型？

教学目的。本地模型：
- 不需要注册云服务、不需要 API Key
- 零成本运行
- 适合反复试验和调试

### Q：模型回答质量不好怎么办？

可以：
1. 换更大的模型（如 `qwen3.6:27b-mlx`）
2. 降低 `temperature` 让回答更严谨
3. 优化 `system_prompt` 给出更清晰的指令

### Q：工具调用失败怎么办？

检查：
1. 文件路径是否正确（用 `scan_directory` 获取完整路径）
2. 标题名称是否完全匹配（`markdown_outline` 的输出就是准确的标题名）
3. 是否有权限访问文件

### Q：这个项目能用来做什么？

- 🎓 **学习 Agent 原理**：通过实际运行理解核心概念
- 🛠️ **日常 Markdown 处理**：整理文档、管理任务列表
- 🚀 **扩展基础**：加更多工具，就能做更多事

---

> **"最好的学习方法，就是亲手做一个。"**
>
> 这个项目就是你亲手运行一个 Agent 的起点。理解了这个项目，你就理解了 Agent 的核心原理——LLM + 工具 + 自主决策。剩下的，只是不断加工具，扩展它的能力边界。
