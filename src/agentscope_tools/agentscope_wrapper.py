"""AgentScope FunctionTool wrappers for the Markdown tools.

Each tool from ``org_tools`` is wrapped via ``FunctionTool``, which
automatically extracts ``name``, ``description`` and ``input_schema`` from
the function's type hints and docstring.

Usage::

    from agentscope_tools.agentscope_wrapper import create_markdown_toolkit

    toolkit = create_markdown_toolkit()
    agent = Agent(name="editor", model=model, toolkit=toolkit)
"""

from __future__ import annotations

from agentscope.tool import FunctionTool, Toolkit

from agentscope_tools.org_tools import (
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
)

# ── Read-only (parser) tools ────────────────────────────────────────────

_READ_ONLY_TOOLS = [
    FunctionTool(markdown_scan_directory, is_read_only=True),
    FunctionTool(markdown_outline, is_read_only=True),
    FunctionTool(markdown_get_section, is_read_only=True),
    FunctionTool(markdown_list_tasks, is_read_only=True),
    FunctionTool(markdown_check_format, is_read_only=True),
]

# ── Mutable (editor / formatter) tools ──────────────────────────────────

_MUTABLE_TOOLS = [
    FunctionTool(markdown_replace_section, is_read_only=False),
    FunctionTool(markdown_insert_after_heading, is_read_only=False),
    FunctionTool(markdown_update_task_status, is_read_only=False),
    FunctionTool(markdown_format_file, is_read_only=False),
]


def create_markdown_toolkit() -> Toolkit:
    """Create an AgentScope ``Toolkit`` with all Markdown tools registered.

    Returns:
        A ``Toolkit`` instance containing 9 tools in the ``"basic"`` tool
        group: 5 read-only (scanner / parser / checker) and 4 mutable
        (editor / formatter).
    """
    instructions = (
        f"The current workspace is {WORKSPACE_ROOT}. "
        "Use markdown_scan_directory without a path to scan this workspace. "
        "Use the returned file path values when calling the other Markdown tools."
    )
    toolkit = Toolkit(tools=_READ_ONLY_TOOLS + _MUTABLE_TOOLS)
    toolkit.tool_groups[0].instructions = instructions
    return toolkit
