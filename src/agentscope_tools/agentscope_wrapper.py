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
    Toolkit,
)

from agentscope_tools.ori_tools import (
    WORKSPACE_ROOT,
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
    _function_tool(markdown_list_tasks, is_read_only=True),
    _function_tool(markdown_check_format, is_read_only=True),
]

# ── Mutable (editor / formatter) tools ──────────────────────────────────

_MUTABLE_TOOLS = [
    _function_tool(markdown_replace_section, is_read_only=False),
    _function_tool(markdown_insert_after_heading, is_read_only=False),
    _function_tool(markdown_update_task_status, is_read_only=False),
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


def create_markdown_toolkit() -> Toolkit:
    """Create an AgentScope ``Toolkit`` with Markdown, Memory, and Task tools.

    Returns:
        A ``Toolkit`` instance containing Markdown tools, JSON-backed user
        preference memory tools, and 4 built-in task planning tools
        (TaskCreate, TaskGet, TaskList, TaskUpdate).
    """
    instructions = (
        f"The current workspace is {WORKSPACE_ROOT}. "
        "Use markdown_scan_directory without a path to scan this workspace. "
        "Use the returned file path values when calling the other Markdown tools. "
        "Use user_memory_outline before loading memory values, then call "
        "user_memory_get_preference for the specific keys needed. Use "
        "user_memory_save_preference only when the user explicitly asks to "
        "remember, save, record, or apply a preference in the future. Do not "
        "silently infer and save preferences from ordinary conversation."
    )
    toolkit = Toolkit(
        tools=_TASK_TOOLS + _READ_ONLY_TOOLS + _MUTABLE_TOOLS + _MEMORY_TOOLS
    )
    toolkit.tool_groups[0].instructions = instructions
    return toolkit
