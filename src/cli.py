"""Command-line entry point for the AgentScope course agent."""

from __future__ import annotations

import argparse
import asyncio

from agentscope_course.agent import ask_agent


def main() -> None:
    """Run a one-shot AgentScope chat from the command line."""
    parser = argparse.ArgumentParser(
        description="Ask the starter AgentScope agent.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to an AgentScope TOML config file",
    )
    args = parser.parse_args()
    print(asyncio.run(ask_agent(args.config)))


if __name__ == "__main__":
    main()