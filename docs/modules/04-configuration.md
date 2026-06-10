# 模块四：配置体系

## 配置文件总览

本项目使用两层配置机制：**TOML 配置文件** + **环境变量文件**。

```
项目根目录/
├── config/
│   ├── agentscope.toml           ← 默认配置（版本控制中）
│   └── agentscope.example.toml   ← 配置示例（版本控制中）
├── .env                          ← 环境变量（不提交到版本控制）
├── .env.example                  ← 环境变量模板（版本控制中）
└── pyproject.toml                ← 项目元数据 + 依赖
```

---

## 4.1 `config/agentscope.toml` — Agent 配置

### 完整配置

```toml
[agent]
name = "course_assistant"
system_prompt = """
你是一个面向 AgentScope 课程项目的助教 agent。
...（长段 system prompt）
"""
max_iters = 30

[model]
model = "qwen3.5:9b-mlx"
stream = true
temperature = 0.1
thinking_enable = false
```

### 配置项说明

#### `[agent]` 段

| 参数 | 默认值 | 类型 | 说明 |
|------|--------|------|------|
| `name` | `"course_assistant"` | string | Agent 名称 |
| `system_prompt` | `"..."` | string | 助教人设 + 工具使用规则 |
| `max_iters` | `30` | integer | 单次任务最大思考步数 |

#### `[model]` 段

| 参数 | 默认值 | 类型 | 说明 |
|------|--------|------|------|
| `model` | `"qwen3.5:9b-mlx"` | string | Ollama 模型名称 |
| `stream` | `true` | boolean | 是否启用流式输出 |
| `temperature` | `0.1` | float | 生成温度（0=严谨，1=平衡，2=创意） |
| `thinking_enable` | `false` | boolean | 是否启用思考链（CoT） |

### System Prompt 设计解析

当前的 system prompt 包含以下规则：

1. **技能优先**：非闲聊任务先检查 `<agent-skills>` 并匹配 description
2. **批量读取**：一个请求可能匹配多个 skills，先全部读取再 `reset_tools`
3. **最终状态语义**：`reset_tools` 不是增量更新，每次调用要把所有仍需的工具组都设为 `true`
4. **工具组映射**：`markdown_read` / `markdown_write` / `memory` / `task_management`
5. **保留已激活组**：新增工具组时不能关掉正在使用的组
6. **避免空调用**：除非读取了对应 skill，不要直接使用工具
7. **最少工具原则**：默认激活最少但完整的工具组集合

---

## 4.2 `.env` — 环境变量

### 通用环境变量

| 变量名 | 用途 | 示例值 |
|--------|------|--------|
| `OLLAMA_HOST` | Ollama 服务地址 | `http://localhost:11434` |
| `OLLAMA_MODEL` | 默认模型（可覆盖配置） | `qwen3.5:9b-mlx` |
| `AGENTSCOPE_CONFIG` | 配置文件路径覆盖 | `/path/to/custom.toml` |
| `AGENTSCOPE_TRACE_DIR` | 追踪日志目录 | `.agentscope_traces` |
| `AGENTSCOPE_TRACE_TEXT_CHARS` | 文本记录上限 | `20000` |
| `AGENTSCOPE_TRACE_DIFF_CHARS` | Diff 记录上限 | `30000` |
| `AGENTSCOPE_EVENT_LOG` | 事件日志文件 | `agentscope_events.jsonl` |

### 废弃环境变量

`.env.example` 中的 `DEEPSEEK_API_KEY` 和 `DEEPSEEK_BASE_URL` 是早期设计的残留，当前项目实际使用的是 Ollama 本地模型，这些变量不会被使用。

---

## 4.3 `pyproject.toml` — 项目元数据

### 依赖清单

| 包 | 版本要求 | 用途 |
|----|---------|------|
| `agentscope` | `>=2.0.0` | Agent 框架 |
| `markdown-it-py` | `>=4.2.0` | Markdown 解析 |
| `mdit-py-plugins` | `>=0.5.0` | Markdown-it 插件 |
| `mdformat` | `>=0.7.22` | Markdown 格式化 |
| `mdformat-gfm` | `>=0.4.1` | GitHub 风格格式化 |
| `python-dotenv` | `>=1.2.2` | 环境变量加载 |
| `ollama` | `>=0.6.2` | Ollama API 客户端 |
| `rich` | `>=15.0.0` | 终端美化 |

### 入口注册

```toml
[project.scripts]
course-agent = "cli:main"
```

### 构建打包

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/agentscope_course", "src/agentscope_tools"]
```

---

## 4.4 配置优先级与加载流程

```
load_config(config_path)
  │
  ├── load_dotenv()           ← 步骤 1: 加载 .env（不覆盖已有环境变量）
  │
  ├── 确定配置文件路径：
  │   ├── config_path 参数（来自 --config）    ← 优先级最高
  │   ├── AGENTSCOPE_CONFIG 环境变量           ← 优先级中等
  │   └── DEFAULT_CONFIG_PATH (config/agentscope.toml)  ← 优先级最低
  │
  ├── 文件不存在？ → 返回 {}
  │
  └── 文件存在？ → tomllib.load(file) → return dict
```

在 `create_model()` 内部的参数优先级：

```
环境变量（OLLAMA_MODEL, OLLAMA_HOST） → TOML 配置 → 代码默认值
```

---

## 4.5 项目根路径解析

```python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
```

路径计算：
- `__file__` = `src/agentscope_course/config.py`
- `.parents[0]` = `src/agentscope_course/`
- `.parents[1]` = `src/`
- `.parents[2]` = 项目根目录 `02_agentscope/`
