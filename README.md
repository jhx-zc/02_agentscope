# 02_agentscope — 从 0 到 1 搭建你的第一个 Agent

> 面向初学者的 Agent 教学项目。基于 **AgentScope 框架**，用本地模型（Ollama）搭建一个能处理 Markdown 文件的智能助手。
>
> 理解了这个项目，你就理解了 Agent 的核心原理 —— **LLM + 工具 + 自主决策**。

---

## 一览

```
你输入                  Agent 思考圈                  你看到
────────              ─────────────                 ──────
                      ① LLM 理解任务
"帮我整理 Test.md"  →  ② 决定调用什么工具     →     🤖 实时回答
                      ③ 执行工具（读/写文件）        🔧 工具调用过程
                      ④ 看到结果，继续或结束          📝 最终结果
```

---

## 环境要求

- **Python 3.14+**（项目指定 `requires-python = ">=3.14"`）
- **Ollama**（本地运行大模型）
- 一个终端

---

## 📦 安装

### 1. 安装依赖

```bash
cd 02_agentscope

# 方式一：pip（通用）
pip install -r requirements.txt

# 方式二：uv（更快）
uv sync
```

### 2. 启动 Ollama

```bash
ollama serve                # 启动服务（默认 http://localhost:11434）
ollama pull qwen3.5:9b-mlx  # 下载默认模型（可换成你想要的模型）
```

> 如使用其他模型，修改 `config/agentscope.toml` 中的 `[model].model` 字段。

---

## 🚀 运行 Agent

```bash
# 方式一：快捷命令
uv run course-agent

# 方式二：Python 模块
python -m src.cli
```

看到以下界面说明启动成功：

```
==================================================
🤖 Agent已就绪 (输入 'quit' 退出)
🧾 Trace log: .agentscope_traces/20260608-xxxx-xxxxxxxx.summary.json
==================================================

🧑 You:
```

---

## 💬 基础使用示例

### 示例 1：自我介绍

```
🧑 You: 你好！请介绍一下你自己
```

Agent 会基于 system prompt 介绍自己的能力和限制。

### 示例 2：扫描文件

```
🧑 You: 看看当前目录下有哪些 Markdown 文件
```

Agent 调用 `markdown_scan_directory` 扫描，终端会实时显示：
```
🧰 Tool batch #1 · 1 call
🔧 [1/1] markdown_scan_directory · abc123...def
  args: {}
  status: finished
  result: success
```

### 示例 3：查看文档大纲

```
🧑 You: 帮我看看 Test.md 的大纲
```

Agent 调用 `markdown_outline` 分析文档结构，返回所有标题层级。

### 示例 4：读取指定章节

```
🧑 You: 读取 Test.md 的"背景"章节
```

Agent 调用 `markdown_get_section` 精确定位章节并返回内容。

### 示例 5：编辑文件

```
🧑 You: 在 Test.md 的"背景"后面插入一个新小节叫"新需求"
```

Agent 先扫描 → 获取大纲 → 确认位置 → 调用 `markdown_insert_after_heading` 插入。

### 示例 6：更新任务列表

```
🧑 You: 把 Test.md 的第 2 个任务标记为完成
```

Agent 调用 `markdown_list_tasks` 读取任务列表，然后用 `markdown_update_task_status` 更新勾选状态。

### 示例 7：让 Agent 记住偏好

```
🧑 You: 记住，我以后默认用英文回复
```

Agent 调用 `user_memory_save_preference` 保存偏好。下次启动时自动加载。

### 示例 8：格式化文档

```
🧑 You: 帮我格式化一下 Test.md
```

Agent 调用 `markdown_check_format` 检查格式，再调用 `markdown_format_file` 用 mdformat 排版。

---

## 🧪 完整任务演示

输入以下指令，观察 Agent 的完整工作流程：

```
帮我处理 Test.md，具体步骤：
1. 先查看文档结构
2. 读取"背景"章节
3. 在"背景"后面插入一个"新需求"小节
4. 把第 1 个任务标记为完成
5. 检查格式是否正确
```

你会看到 Agent 依次调用 5 个工具，并在终端实时展示每个步骤。

---

## 📂 项目结构快速导航

```
02_agentscope/
├── src/
│   ├── cli.py                         # 🚪 启动入口
│   ├── agentscope_course/             # 🧠 Agent 核心
│   │   ├── agent.py                   #    组装 Agent（大脑+工具）
│   │   ├── config.py                  #    加载配置
│   │   ├── console.py                 #    流式终端渲染
│   │   ├── conversation.py            #    对话循环
│   │   ├── trace.py                   #    运行追踪日志
│   │   └── models/ollama.py           #    模型补丁
│   └── agentscope_tools/              # 🛠️  工具系统
│       ├── agentscope_wrapper.py      #    工具注册中心
│       └── ori_tools/                 #    9 种工具实现
│           ├── scanner.py             #    目录扫描
│           ├── parser.py              #    Markdown 解析
│           ├── editor.py              #    Markdown 编辑
│           ├── formatter.py           #    Markdown 格式化
│           └── memory.py              #    用户偏好记忆
├── config/
│   └── agentscope.toml                # ⚙️  Agent 配置
├── docs/                              # 📖 模块级技术文档
│   └── modules/
│       ├── 01-cli-entry.md
│       ├── 02-agent-core.md
│       ├── 03-tools-system.md
│       ├── 04-configuration.md
│       ├── 05-architecture-overview.md
│       └── 06-data-flow.md
├── course-content.md                  # 📚 课程讲义（7 章）
└── AGENTS.md                          # 📋 教学说明
```

---

## ⚙️ 常见配置调整

### 修改模型

编辑 `config/agentscope.toml`：

```toml
[model]
model = "qwen3.5:9b-mlx"   # 换成你下载的模型
temperature = 0.1           # 0=严谨  1=平衡  2=创意
```

### 修改 Agent 人设

编辑 `config/agentscope.toml` 的 `[agent].system_prompt`。

### 修改模型地址

设置环境变量连接到远程 Ollama：

```bash
export OLLAMA_HOST=http://192.168.1.100:11434
uv run course-agent
```

---

## ❓ 常见问题

**Q: Agent 回答得很慢？**
Agent 不是直接问答，而是"理解→决策→调用工具→看结果→继续思考"的完整循环。每次工具调用都和 LLM 通信，这是正常现象。

**Q: 模型回答质量不好？**
可以换更大的模型（如 `qwen3.5:27b`）、降低 `temperature`、或优化 system prompt。

**Q: 工具调用失败？**
检查：文件路径是否正确（先用 `scan_directory` 获取完整路径）、标题名是否完全匹配（`outline` 的输出就是准确的标题名）。

**Q: 能用云 API 吗？**
项目默认用本地 Ollama。如需云 API（如 DeepSeek），需修改 `agent.py` 中的 `create_model()` 使用对应的 AgentScope 模型适配器。

---

## 📚 延伸阅读

- [模块级技术文档](docs/README.md) — 6 篇深度分析文档
- [课程讲义](course-content.md) — 7 章教学教程
- [AgentScope 官方文档](https://modelscope.github.io/agentscope/)

---

> **"最好的学习方法，就是亲手做一个。"**
>
> 这个项目就是你亲手运行一个 Agent 的起点。理解了这个项目，你就理解了小龙虾（Manus）这类产品背后的底层逻辑——LLM + 工具 + 自主决策。剩下的，只是不断加工具，扩展它的能力边界。
