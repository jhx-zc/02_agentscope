"""Backward-compatible re-export — source has moved to ``ori_tools/parser.py``."""

from agentscope_tools.ori_tools.parser import (  # noqa: F401
    _containing_section,
    _markdown_parser,
    _read_markdown,
    iter_outline,
    markdown_get_section,
    markdown_list_tasks,
    markdown_outline,
)
