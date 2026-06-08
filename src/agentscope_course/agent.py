"""AgentScope agent creation and orchestration for the course project."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import OllamaCredential
from agentscope.message import UserMsg
from agentscope.model import ChatModelBase
from agentscope.tool import Toolkit

from agentscope_course.console import StreamConsoleRenderer
from agentscope_course.config import _maybe_number, load_config, load_dotenv
from agentscope_course.conversation import reply_until_done
from agentscope_course.models import PatchedOllamaChatModel
from agentscope_course.trace import TraceRecorder, trace_recorder_context

from agentscope_tools import init_user_memory


def create_model(config: dict[str, Any] | None = None) -> ChatModelBase:
    """Create the AgentScope Ollama chat model."""
    load_dotenv()
    model_config = config or {}
    model_name = os.getenv(
        "OLLAMA_MODEL",
        model_config.get("model", "qwen3.5:4b-mlx"),
    )
    stream = bool(model_config.get("stream", True))
    temperature = (
        _maybe_number(model_config["temperature"])
        if "temperature" in model_config
        else None
    )
    max_tokens = (
        _maybe_number(model_config["max_tokens"])
        if "max_tokens" in model_config
        else None
    )
    thinking_enable = bool(model_config.get("thinking_enable", False))

    parameters = PatchedOllamaChatModel.Parameters(
        temperature=temperature,
        max_tokens=max_tokens,
        thinking_enable=thinking_enable,
    )

    host = os.getenv("OLLAMA_HOST") or model_config.get("host")
    credential = OllamaCredential(host=host) if host else OllamaCredential()
    return PatchedOllamaChatModel(
        credential=credential,
        model=model_name,
        parameters=parameters,
        stream=stream,
    )


def create_toolkit() -> Toolkit:
    """Create a toolkit with Markdown tools registered."""
    from agentscope_tools.agentscope_wrapper import create_markdown_toolkit

    return create_markdown_toolkit()


def create_agent(config: dict[str, Any] | None = None) -> Agent:
    """Create the starter AgentScope agent."""
    loaded = config or load_config()
    agent_config = loaded.get("agent", {})
    agent = Agent(
        name=agent_config.get("name", "course_assistant"),
        system_prompt=agent_config.get(
            "system_prompt",
            "你是一个面向 AgentScope 课程项目的助教 agent。",
        ),
        model=create_model(loaded.get("model", {})),
        toolkit=create_toolkit(),
        react_config=ReActConfig(max_iters=agent_config.get("max_iters", 20)),
    )
    agent.state.context.append(UserMsg(name="user", content=init_user_memory()))
    return agent


async def ask_agent(config_path: str | Path | None = None) -> None:
    """Start an interactive conversation loop with the starter agent.

    Type 'quit' or press Ctrl-C to exit.
    """
    agent = create_agent(load_config(config_path))
    trace_recorder = TraceRecorder()
    print("=" * 50)
    print("🤖 Agent已就绪 (输入 'quit' 退出)")
    print(f"🧾 Trace log: {trace_recorder.jsonl_path}")
    print("=" * 50)

    user_input = """
查看记忆中我当前打开的 Markdown 文件。你现在需要把它整理成一个基础可验收版本。

请使用 Plan Mode 解决问题，不要一开始就直接修改文件。

具体要求如下：

1. 先读取并理解文档整体结构，简单说明你识别到的主要章节。
2. 不要修改以下章节的正文内容：

   * `## 1. 背景`
   * `## 7. FAQ`
3. 读取并确认以下章节内容：

   * `### 3.3 插入新章节`
   * `## 4. 数据来源`
   * `## 5. 风险`
   * `## 6. 待办清单`
4. 重写 `## 5. 风险` 章节，但保留 `## 5. 风险` 这个标题。

   * 重写后保留 3 条风险。
   * 每条风险都要包含：

     * `风险：`
     * `缓解方式：`
   * 风险描述要比原文更清楚。
5. 在 `### 3.3 插入新章节` 后插入一个新小节：

   * 标题：`#### 本次修改要点`
   * 内容简要说明本次修改包括：重写风险章节、插入数据更新频率说明、更新待办清单。
6. 在 `## 4. 数据来源` 后插入一个新小节：

   * 标题：`### 4.1 数据更新频率`
   * 用一个简单表格说明不同数据来源的更新频率。
   * 表格包含三列：

     * 数据来源
     * 更新频率
     * 说明
7. 更新 `## 6. 待办清单` 中的任务状态：

   * 将“支持替换风险章节”标记为已完成。
   * 将“支持插入数据更新频率说明”标记为已完成。
   * 其他任务状态保持不变。
8. 最后检查 Markdown 格式：

   * 标题前后保留空行。
   * 表格格式保持规范。
   * 任务列表格式保持规范。
9. 修改完成后，告诉我：

   * 读取了哪些章节。
   * 修改了哪个章节。
   * 插入了哪些新小节。
   * 更新了哪些任务状态。
   * 确认没有修改哪些受保护章节。

注意：

* 不要全文重写。
* 不要修改背景和 FAQ。
* 不要使用全局字符串替换。
* 尽量基于标题路径或 section 范围进行修改。

"""

    try:
        while True:
            if not user_input:
                user_input = input("\n🧑 You: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "quit":
                print("👋 再见！")
                break

            print()  # 换行，准备输出 agent 的流式响应
            trace_recorder.start_turn(user_input)
            renderer = StreamConsoleRenderer(trace_recorder=trace_recorder)
            try:
                with trace_recorder_context(trace_recorder):
                    await reply_until_done(
                        agent,
                        UserMsg(name="user", content=user_input),
                        renderer,
                    )
            except Exception as exc:
                trace_recorder.record_local_event(
                    "turn_error",
                    {
                        "error_type": exc.__class__.__name__,
                        "message": str(exc),
                    },
                )
                raise
            finally:
                user_input = ""
                renderer.finish()
                trace_recorder.end_turn()
    except (KeyboardInterrupt, EOFError):
        print("\n👋 再见！")
    finally:
        trace_recorder.close()
