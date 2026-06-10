# 模块一：CLI 入口 — `cli.py`

## 文件定位

- **路径**: `src/cli.py`
- **行数**: 26 行
- **依赖**: `agentscope_course.agent`
- **包注册**: `pyproject.toml` → `project.scripts` → `course-agent = "cli:main"`

## 职责

命令行启动入口。负责解析 `--config` 参数并启动 Agent 异步对话循环。

## 源码分析

```python
def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the starter AgentScope agent.")
    parser.add_argument("--config", default=None, help="Path to an AgentScope TOML config file")
    args = parser.parse_args()
    print(asyncio.run(ask_agent(args.config)))
```

### 执行流程

```
main()
  ├── 解析 --config（可选，指定自定义 TOML 配置文件路径）
  ├── asyncio.run(ask_agent(config_path))
  │     └── 进入 agent.py 定义的交互循环
  └── 打印返回值
```

### 关键设计点

1. **最小职责原则** — 只做"解析参数 + 启动循环"两件事，所有业务逻辑委托给下层模块。
2. **异步架构** — 使用 `asyncio.run()` 包装整个 Agent 循环，为流式输出和并发事件处理提供基础。
3. **无状态设计** — 所有状态在 Agent 运行时构造，CLI 入口本身不持有任何全局状态。
4. **命令行入口** — 通过 `pyproject.toml` 的 `[project.scripts]` 注册，支持 `uv run course-agent` 直接调用。

### 重要注释

- `--config` 参数可选，不传时使用默认路径 `config/agentscope.toml`。
- 如果 `load_config(config_path)` 返回空字典（文件不存在），Agent 使用所有默认值运行。

## 运行时调用链

```
uv run course-agent                     # pyproject.toml 入口
  → cli.py:main()                      # 当前模块
    → agent.py:ask_agent(config_path)  # 核心循环启动
      → agent.py:create_agent(config)  # 组装 Agent
        → config.py:load_config()      # 加载配置
        → agent.py:create_model()      # 创建 LLM 模型
        → agent.py:create_toolkit()    # 创建工具集
      → conversation.py:reply_until_done()  # 对话循环开始
```

## 测试与调试

```bash
# 默认运行
uv run course-agent

# 指定自定义配置
uv run course-agent --config /path/to/custom.toml

# 直接 Python 调用
python -m src.cli
```

## 与课程内容的关联

- **第 1 章《Hello Agent!》** — 学生第一个接触的文件
- **第 2 章《Agent 的大脑》** — 通过 `agent.py` 向下深入模型创建
- **第 5 章《看得见的思考》** — 通过 `console.py` 实现流式输出展示
