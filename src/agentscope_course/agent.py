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
    print("=" * 50)
    print("🤖 Agent已就绪 (输入 'quit' 退出)")
    print("=" * 50)

    try:
        while True:
            user_input = input("\n🧑 You: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "quit":
                print("👋 再见！")
                break

            print()  # 换行，准备输出 agent 的流式响应
            renderer = StreamConsoleRenderer()
            await reply_until_done(
                agent,
                UserMsg(name="user", content=user_input),
                renderer,
            )
            renderer.finish()
    except (KeyboardInterrupt, EOFError):
        print("\n👋 再见！")
