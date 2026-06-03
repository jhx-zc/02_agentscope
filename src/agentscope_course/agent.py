"""Initial AgentScope agent setup for the course project."""

from __future__ import annotations

import argparse
import asyncio
import os
import tomllib
from pathlib import Path
from typing import Any

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import DeepSeekCredential
from agentscope.message import UserMsg
from agentscope.model import ChatModelBase, DeepSeekChatModel
from agentscope.tool import Toolkit

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config/agentscope.toml"
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


def load_dotenv(path: str | Path | None = None) -> None:
    """Load project-level environment variables without overriding the shell."""
    env_path = Path(path or DEFAULT_ENV_PATH)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load the optional TOML config for the starter agent."""
    load_dotenv()
    config_path = Path(path or os.getenv("AGENTSCOPE_CONFIG", DEFAULT_CONFIG_PATH))
    if not config_path.exists():
        return {}

    with config_path.open("rb") as file:
        return tomllib.load(file)


def _maybe_number(value: Any) -> Any:
    """Keep only configured numeric values for model parameters."""
    return value if value is not None else None


def create_model(config: dict[str, Any] | None = None) -> ChatModelBase:
    """Create the AgentScope DeepSeek chat model."""
    load_dotenv()
    model_config = config or {}
    model_name = os.getenv(
        "DEEPSEEK_MODEL",
        model_config.get("model", "deepseek-chat"),
    )
    stream = bool(model_config.get("stream", True))
    temperature = _maybe_number(model_config.get("temperature"))
    max_tokens = _maybe_number(model_config.get("max_tokens"))
    top_p = _maybe_number(model_config.get("top_p"))
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
        top_p=top_p,
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


async def ask_agent(prompt: str, config_path: str | Path | None = None) -> str:
    """Send one user prompt to the starter agent and return plain text."""
    agent = create_agent(load_config(config_path))
    reply = await agent.reply(UserMsg(name="user", content=prompt))
    return reply.get_text_content() or ""


def main() -> None:
    """Run a one-shot AgentScope chat from the command line."""
    parser = argparse.ArgumentParser(
        description="Ask the starter AgentScope agent.",
    )
    parser.add_argument("prompt", nargs="?", help="User message for the agent")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to an AgentScope TOML config file",
    )
    args = parser.parse_args()

    prompt = args.prompt or input("You: ")
    print(asyncio.run(ask_agent(prompt, args.config)))


if __name__ == "__main__":
    main()
