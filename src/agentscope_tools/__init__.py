"""Agentscope Tools — Markdown parser, editor, formatter, and CLI utilities."""

from agentscope_tools.parser import (
    iter_outline,
    markdown_get_section,
    markdown_list_code_blocks,
    markdown_list_tasks,
    markdown_outline,
    markdown_render_html,
    markdown_word_count,
)
from agentscope_tools.editor import (
    markdown_insert_after_heading,
    markdown_replace_section,
    markdown_update_code_block,
    markdown_update_task,
)
from agentscope_tools.formatter import (
    markdown_check_format,
    markdown_format_file,
)

__all__ = [
    # Parser
    "iter_outline",
    "markdown_get_section",
    "markdown_list_code_blocks",
    "markdown_list_tasks",
    "markdown_outline",
    "markdown_render_html",
    "markdown_word_count",
    # Editor
    "markdown_insert_after_heading",
    "markdown_replace_section",
    "markdown_update_code_block",
    "markdown_update_task",
    # Formatter
    "markdown_check_format",
    "markdown_format_file",
]
