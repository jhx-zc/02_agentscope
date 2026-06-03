"""Conversation-turn orchestration for the AgentScope course CLI."""

from __future__ import annotations

from agentscope.agent import Agent
from agentscope.event import (
    ConfirmResult,
    RequireExternalExecutionEvent,
    RequireUserConfirmEvent,
    UserConfirmResultEvent,
)
from agentscope.message import Msg

from agentscope_course.console import StreamConsoleRenderer


async def _confirm_tool_calls(
    agent: Agent,
    event: RequireUserConfirmEvent,
) -> UserConfirmResultEvent:
    """Build a confirmation event for AgentScope tool calls."""
    confirm_results = []
    for tool_call in event.tool_calls:
        tool = await agent.toolkit.get_tool(tool_call.name)
        is_read_only = bool(getattr(tool, "is_read_only", False))

        if is_read_only:
            print(f"   permission: auto-approved read-only tool {tool_call.name}")
            confirmed = True
        else:
            print()
            print(f"⚠️  Tool permission required: {tool_call.name}")
            print(f"   args: {tool_call.input}")
            answer = input("   Allow this tool call? [y/N]: ").strip().lower()
            confirmed = answer in {"y", "yes"}

        confirm_results.append(
            ConfirmResult(
                confirmed=confirmed,
                tool_call=tool_call,
            ),
        )

    return UserConfirmResultEvent(
        reply_id=event.reply_id,
        confirm_results=confirm_results,
    )


async def reply_until_done(
    agent: Agent,
    user_msg: Msg,
    renderer: StreamConsoleRenderer,
) -> None:
    """Run one user turn, continuing through AgentScope confirmation events."""
    next_input: Msg | UserConfirmResultEvent | None = user_msg

    while next_input is not None:
        follow_up_event: UserConfirmResultEvent | None = None
        async for event in agent.reply_stream(next_input):
            renderer.render(event)

            if isinstance(event, RequireUserConfirmEvent):
                renderer.finish()
                follow_up_event = await _confirm_tool_calls(agent, event)

            elif isinstance(event, RequireExternalExecutionEvent):
                tool_names = ", ".join(
                    tool_call.name for tool_call in event.tool_calls
                )
                raise RuntimeError(
                    "This CLI cannot execute external tools yet: "
                    f"{tool_names}",
                )

        next_input = follow_up_event
