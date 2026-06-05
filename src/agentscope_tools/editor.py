"""Backward-compatible re-export — source has moved to ``ori_tools/editor.py``."""

from agentscope_tools.ori_tools.editor import (  # noqa: F401
    _content_lines,
    _read_lines,
    _write_lines,
    markdown_insert_after_heading,
    markdown_replace_section,
    markdown_update_task_status,
)
