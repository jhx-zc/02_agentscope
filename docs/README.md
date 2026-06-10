# 02_agentscope — 模块文档

> 基于 AgentScope 框架的 Agent 教学项目模块级技术文档。

## 文档目录

| 文档 | 说明 |
|------|------|
| [🔧 模块一：CLI 入口](modules/01-cli-entry.md) | 命令行启动入口 |
| [🧠 模块二：Agent 核心](modules/02-agent-core.md) | 大脑、配置、渲染、对话、追踪、模型补丁 |
| [🛠️ 模块三：工具系统](modules/03-tools-system.md) | 工具注册中心 + 9 种 Markdown 工具原始实现 |
| [⚙️ 模块四：配置体系](modules/04-configuration.md) | TOML 配置、环境变量、资源路径 |
| [🏗️ 模块五：架构总览](modules/05-architecture-overview.md) | 整体架构、模块依赖、运行时数据流 |
| [📊 模块六：数据流与事件追踪](modules/06-data-flow.md) | 事件类型、追踪记录、日志体系 |

## 项目全景速览

```
User Input
    │
    ▼
┌────────────────────────────┐
│ 01 CLI 入口  (cli.py)      │  ── 解析 --config 参数，启动循环
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ 02 Agent 核心              │  ── 大脑(LLM) + 双手(工具) + 感知(事件)
│  ┌──────────────────────┐  │
│  │ agent.py            │  │  ── 组装 Agent
│  │ config.py           │  │  ── 加载配置
│  │ console.py          │  │  ── 流式渲染
│  │ conversation.py     │  │  ── 对话循环
│  │ trace.py            │  │  ── 追踪日志
│  │ models/ollama.py    │  │  ── 模型补丁
│  └──────────────────────┘  │
└─────────┬──────────────────┘
          │
          ▼
┌────────────────────────────┐
│ 03 工具系统                │  ── Agent 的"双手"
│  ┌──────────────────────┐  │
│  │ agentscope_wrapper   │  │  ── 注册中心 + 追踪装饰器
│  │ ori_tools/           │  │  ── 工具原始实现
│  │  ├─ scanner.py      │  │     📂 目录扫描
│  │  ├─ parser.py       │  │     📋 Markdown 解析
│  │  ├─ editor.py       │  │     ✏️  Markdown 编辑
│  │  ├─ formatter.py    │  │     🎨 Markdown 格式化
│  │  └─ memory.py       │  │     🧠 用户偏好记忆
│  └──────────────────────┘  │
└────────────────────────────┘
          │
          ▼
      Trace Log (.agentscope_traces/)
```
