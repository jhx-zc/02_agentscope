"""AgentScope FunctionTool wrappers for course tools and built-in Task tools.

Each regular Python tool from ``ori_tools`` is wrapped via ``FunctionTool``, which
automatically extracts ``name``, ``description`` and ``input_schema`` from
the function's type hints and docstring. Built-in task planning tools
(``TaskCreate``, ``TaskGet``, ``TaskList``, ``TaskUpdate``) are included
directly as ``ToolBase`` instances.

Usage::

    from agentscope_tools.agentscope_wrapper import create_markdown_toolkit

    toolkit = create_markdown_toolkit()
    agent = Agent(name="editor", model=model, toolkit=toolkit)
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from agentscope.message import TextBlock, ToolResultState
from agentscope.tool import (
    FunctionTool,
    TaskCreate,
    TaskGet,
    TaskList,
    TaskUpdate,
    ToolChunk,
    ToolGroup,
    Toolkit,
)

from agentscope_tools.ori_tools import (
    WORKSPACE_ROOT,
    SKILLS_ROOTS,
    markdown_check_format,
    markdown_format_file,
    markdown_get_section,
    markdown_insert_after_heading,
    markdown_list_tasks,
    markdown_outline,
    markdown_replace_section,
    markdown_scan_directory,
    markdown_update_task_status,
    user_memory_clear_preferences,
    user_memory_delete_preference,
    user_memory_get_preference,
    user_memory_list_preferences,
    user_memory_outline,
    user_memory_save_preference,
    hard_user_memories,
)


def _format_tool_result(result: Any) -> str:
    """Format regular Python tool output for AgentScope tool results."""
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def _wrap_tool_result(func: Callable[..., Any]) -> Callable[..., ToolChunk]:
    """Adapt ordinary Python return values to AgentScope 2.0 ToolChunk."""

    @wraps(func)
    def wrapped(**kwargs: Any) -> ToolChunk:
        result = func(**kwargs)
        return ToolChunk(
            content=[TextBlock(text=_format_tool_result(result))],
            state=ToolResultState.SUCCESS,
        )

    setattr(wrapped, "__signature__", inspect.signature(func))
    return wrapped


def _function_tool(func: Callable[..., Any], *, is_read_only: bool) -> FunctionTool:
    """Create an AgentScope FunctionTool for a regular Python function."""
    return FunctionTool(_wrap_tool_result(func), is_read_only=is_read_only)


def init_user_memory():
    memory_outline = user_memory_outline()
    hard_memories = hard_user_memories()
    return [TextBlock(text='User Memory outline:'), TextBlock(text=_format_tool_result(memory_outline)),
             TextBlock(text='User Hard Memories:'), TextBlock(text=_format_tool_result(hard_memories))]

# ── Read-only (parser) tools ────────────────────────────────────────────

_READ_ONLY_TOOLS = [
    _function_tool(markdown_scan_directory, is_read_only=True),
    _function_tool(markdown_outline, is_read_only=True),
    _function_tool(markdown_get_section, is_read_only=True),
    # _function_tool(markdown_list_tasks, is_read_only=True),
    _function_tool(markdown_check_format, is_read_only=True),
]

# ── Mutable (editor / formatter) tools ──────────────────────────────────

_MUTABLE_TOOLS = [
    _function_tool(markdown_replace_section, is_read_only=False),
    _function_tool(markdown_insert_after_heading, is_read_only=False),
    # _function_tool(markdown_update_task_status, is_read_only=False),
    _function_tool(markdown_format_file, is_read_only=False),
]

# ── Mutable JSON user preference memory tools ───────────────────────────

_MEMORY_TOOLS = [
    _function_tool(user_memory_outline, is_read_only=True),
    _function_tool(user_memory_save_preference, is_read_only=False),
    _function_tool(user_memory_get_preference, is_read_only=True),
    _function_tool(user_memory_list_preferences, is_read_only=True),
    _function_tool(user_memory_delete_preference, is_read_only=False),
    _function_tool(user_memory_clear_preferences, is_read_only=False),
]

# ── Built-in task planning tools ────────────────────────────────────────

_TASK_TOOLS = [
    TaskCreate(),
    TaskGet(),
    TaskList(),
    TaskUpdate(),
]

# _TASK_TOOLS = []


def create_markdown_toolkit() -> Toolkit:
    """Create an AgentScope ``Toolkit``
    """
    workspace_hint = f"The current workspace is {WORKSPACE_ROOT}. "
    return Toolkit(
        tools=[],
        skills_or_loaders=SKILLS_ROOTS,
        tool_groups=[
            ToolGroup(
                name="markdown_read",
                description=(
                    "Use when the task requires scanning, reading, "
                    "outlining, or checking Markdown files. Activate this "
                    "after reading the markdown-workspace skill."
                ),
                instructions=(
                    workspace_hint
                    + "Before using these tools, you must have read the "
                    "`markdown-workspace` skill with the `Skill` tool. "
                    "`reset_tools` uses final-state semantics, so every "
                    "reset call must keep all still-needed groups set to "
                    "true. Start with `markdown_scan_directory`."
                ),
                tools=_READ_ONLY_TOOLS,
            ),
            ToolGroup(
                name="markdown_write",
                description=(
                    "Use when the task requires editing or formatting "
                    "Markdown files. Activate this after reading the "
                    "markdown-workspace skill."
                ),
                instructions=(
                    workspace_hint
                    + "Before using these tools, you must have read the "
                    "`markdown-workspace` skill with the `Skill` tool. "
                    "`reset_tools` uses final-state semantics, so every "
                    "reset call must keep all still-needed groups set to "
                    "true. "
                    "Use exact file paths returned by "
                    "`markdown_scan_directory`."
                ),
                tools=_MUTABLE_TOOLS,
            ),
            ToolGroup(
                name="memory",
                description=(
                    "Use when the task requires reading, saving, updating, "
                    "or applying user preferences. Activate this after "
                    "reading the user-memory-preferences skill."
                ),
                instructions=(
                    "Before using these tools, you must have read the "
                    "`user-memory-preferences` skill with the `Skill` tool. "
                    "`reset_tools` uses final-state semantics, so every "
                    "reset call must keep all still-needed groups set to "
                    "true. "
                    "Always inspect outline before loading specific values."
                ),
                tools=_MEMORY_TOOLS,
            ),
            ToolGroup(
                name="task_management",
                description=(
                    "Use when the task requires internal task planning, task "
                    "tracking, or structured execution. Activate this after "
                    "reading the plan-mode-task-management skill."
                ),
                instructions=(
                    "Before using these tools, you must have read the "
                    "`plan-mode-task-management` skill with the `Skill` tool. "
                    "`reset_tools` uses final-state semantics, so every "
                    "reset call must keep all still-needed groups set to true."
                ),
                tools=_TASK_TOOLS,
            ),
        ],
    )
