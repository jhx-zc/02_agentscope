# 02 Agentscope

本项目用于借助 AgentScope 构建教学课程。

## Notes

- [AgentScope Markdown 工具设计](docs/markdown-tools-for-agentscope.md)

## AgentScope starter

依赖已在 `pyproject.toml` 中声明：

```bash
uv sync
```

创建本地配置：

```bash
cp config/agentscope.example.toml config/agentscope.toml
cp .env.example .env
```

`config/agentscope.toml` 用来配置 DeepSeek 模型参数；项目根目录 `.env`
用来放密钥，并已加入 `.gitignore`。

在 `.env` 中填写：

```bash
DEEPSEEK_API_KEY="your-api-key"
# 可选：DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

然后运行：

```bash
uv run course-agent "请介绍一下你现在能做什么"
```

DeepSeek 的 thinking 参数和 `reasoning_content` 解析使用 AgentScope 内置的
`DeepSeekChatModel` 适配；需要开启时在 `config/agentscope.toml` 中设置
`thinking_enable = true`。

当前 agent 入口在 `src/agentscope_course/agent.py`。工具注册点是
`create_toolkit()`，下一步可以把已有的 `markdown_*` 函数逐个挂到
AgentScope 的 `Toolkit` 里。
