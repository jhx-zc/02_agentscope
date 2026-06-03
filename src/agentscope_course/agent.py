"""AgentScope agent creation and orchestration for the course project."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import DeepSeekCredential
from agentscope.event import (
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultEndEvent,
    ToolResultStartEvent,
)
from agentscope.message import Msg, UserMsg
from agentscope.model import ChatModelBase, DeepSeekChatModel
from agentscope.tool import Toolkit

from agentscope_course.config import _maybe_number, load_config, load_dotenv


def create_model(config: dict[str, Any] | None = None) -> ChatModelBase:
    """Create the AgentScope DeepSeek chat model."""
    load_dotenv()
    model_config = config or {}
    model_name = os.getenv(
        "DEEPSEEK_MODEL",
        model_config.get("model", "deepseek-v4-flash"),
    )
    stream = bool(model_config.get("stream", True))
    temperature = _maybe_number(model_config.get("temperature"))
    max_tokens = _maybe_number(model_config.get("max_tokens"))
    thinking_enable = bool(model_config.get("thinking_enable", False))
    reasoning_effort = model_config.get("reasoning_effort")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing DEEPSEEK_API_KEY. Put it in the project-level .env file "
            "or set it in your shell."
        )

    parameters = DeepSeekChatModel.Parameters(
        temperature=temperature,
        max_tokens=max_tokens,
        thinking_enable=thinking_enable,
        reasoning_effort=reasoning_effort,
    )
    credential_kwargs = {"api_key": api_key}
    base_url = os.getenv("DEEPSEEK_BASE_URL") or model_config.get("base_url")
    if base_url:
        credential_kwargs["base_url"] = base_url
    credential = DeepSeekCredential(**credential_kwargs)
    return DeepSeekChatModel(
        credential=credential,
        model=model_name,
        parameters=parameters,
        stream=stream,
    )


def create_toolkit() -> Toolkit:
    """Create an empty toolkit; register project tools here in the next step."""
    return Toolkit()


def create_agent(config: dict[str, Any] | None = None) -> Agent:
    """Create the starter AgentScope agent."""
    loaded = config or load_config()
    agent_config = loaded.get("agent", {})

    return Agent(
        name=agent_config.get("name", "course_assistant"),
        system_prompt=agent_config.get(
            "system_prompt",
            "你是一个面向 AgentScope 课程项目的助教 agent。",
        ),
        model=create_model(loaded.get("model", {})),
        toolkit=create_toolkit(),
        react_config=ReActConfig(max_iters=agent_config.get("max_iters", 8)),
    )


async def ask_agent(config_path: str | Path | None = None) -> None:
    """Start an interactive conversation loop with the starter agent.

    Type 'quit' or press Ctrl-C to exit.
    """
    agent = create_agent(load_config(config_path))

    print("=" * 50)
    print("🤖 AgentScope 助教已就绪 (输入 'quit' 退出)")
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
            async for event in agent.reply_stream(
                UserMsg(name="user", content=user_input),
            ):
                if isinstance(event, ToolCallStartEvent):
                    print(f"\n🔧 [调用工具] {event.tool_call_name}")
                elif isinstance(event, ToolCallDeltaEvent):
                    print(f"   📥 参数: {event.delta}", end="", flush=True)
                elif isinstance(event, ToolCallEndEvent):
                    print()  # 工具调用参数结束后换行
                elif isinstance(event, ToolResultStartEvent):
                    print(f"   ⏳ 执行中 ...")
                elif isinstance(event, ToolResultEndEvent):
                    print(f"   ✅ 执行完成 (状态: {event.state})")
                elif isinstance(event, Msg):
                    print(f"\n Agent 回答: {event.get_text_content() or ''}")
    except (KeyboardInterrupt, EOFError):
        print("\n👋 再见！")
