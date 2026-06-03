"""Markdown Editor 工具。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from agentscope_tools.org_tools.parser import (
    markdown_get_section,
    markdown_list_tasks,
)


def _read_lines(path: str) -> list[str]:
    """Read a file as UTF-8 while preserving line endings.

    Args:
        path: Path to the Markdown file.

    Returns:
        File lines including their newline characters.
    """
    return Path(path).read_text(encoding="utf-8").splitlines(keepends=True)


def _write_lines(path: str, lines: list[str]) -> None:
    """Write UTF-8 lines back to a Markdown file.

    Args:
        path: Path to the Markdown file.
        lines: Lines to write, normally created by ``_read_lines`` and edited
            with slice replacement.
    """
    Path(path).write_text("".join(lines), encoding="utf-8")


def _content_lines(content: str) -> list[str]:
    """Normalize inserted or replacement Markdown content to line chunks.

    Args:
        content: Markdown text to insert or replace. A final newline is added
            when missing so subsequent Markdown keeps a clean line boundary.

    Returns:
        A list of newline-preserving lines suitable for slice assignment.
    """
    if content and not content.endswith("\n"):
        content += "\n"
    return content.splitlines(keepends=True)


def markdown_replace_section(
    path: str,
    heading: str,
    content: str,
    occurrence: int = 1,
) -> dict[str, Any]:
    """Replace a whole Markdown section, including its heading line.

    Args:
        path: Path to the Markdown file to modify.
        heading: Exact heading title used to find the section.
        content: Replacement Markdown text. It should include the desired
            heading line if the section should still have one.
        occurrence: 1-based heading occurrence when titles repeat.

    Returns:
        A dictionary describing the edit:
        ``path``: Modified file path.
        ``heading``: Heading used for lookup.
        ``old_range``: Old 1-based inclusive section range.
        ``new_range``: New 1-based inclusive section range.
        ``line_delta``: Number of lines added or removed.

    Raises:
        ValueError: If the requested heading occurrence cannot be found.
    """
    section = markdown_get_section(path, heading, occurrence)
    lines = _read_lines(path)
    replacement = _content_lines(content)
    old_start = section["section_start"]
    old_end = section["section_end"]

    # Python 切片右边界是排他的；这里保存的行号范围是 1-based 且包含结束行。
    lines[old_start - 1 : old_end] = replacement
    _write_lines(path, lines)

    new_end = old_start + len(replacement) - 1
    return {
        "path": path,
        "heading": heading,
        "old_range": {"start": old_start, "end": old_end},
        "new_range": {"start": old_start, "end": new_end},
        "line_delta": len(replacement) - (old_end - old_start + 1),
    }


def markdown_insert_after_heading(
    path: str,
    heading: str,
    content: str,
    occurrence: int = 1,
) -> dict[str, Any]:
    """Insert Markdown content immediately after a heading line.

    Args:
        path: Path to the Markdown file to modify.
        heading: Exact heading title used to find the insertion point.
        content: Markdown text to insert after the heading line.
        occurrence: 1-based heading occurrence when titles repeat.

    Returns:
        A dictionary containing ``path``, ``heading``, ``insert_after_line``,
        and ``inserted_lines``.

    Raises:
        ValueError: If the requested heading occurrence cannot be found.
    """
    section = markdown_get_section(path, heading, occurrence)
    lines = _read_lines(path)
    insert_at = section["line_end"]
    insertion = _content_lines(content)

    # insert_at 来自 1-based 标题结束行；作为切片下标时刚好表示"标题行之后"的插入点。
    lines[insert_at:insert_at] = insertion
    _write_lines(path, lines)

    return {
        "path": path,
        "heading": heading,
        "insert_after_line": insert_at,
        "inserted_lines": len(insertion),
    }


def markdown_update_task_status(path: str, task_index: int, done: bool) -> dict[str, Any]:
    """Update only the checkbox state for a task list item.

    Args:
        path: Path to the Markdown file to modify.
        task_index: 1-based task index from ``markdown_list_tasks``.
        done: Desired checkbox state. ``True`` writes ``[x]`` and ``False``
            writes ``[ ]``.

    Returns:
        A dictionary containing the modified ``path``, ``task_index``, source
        ``line``, old/new completion state, and task ``text``.

    Raises:
        ValueError: If ``task_index`` is less than 1 or the requested task does
        not exist.
    """
    if task_index < 1:
        raise ValueError("task_index must be greater than or equal to 1")

    tasks = markdown_list_tasks(path)
    if len(tasks) < task_index:
        raise ValueError(f"task index {task_index} was not found")

    task = tasks[task_index - 1]
    lines = _read_lines(path)
    line_index = task["line"] - 1
    old_line = lines[line_index]
    new_state = "x" if done else " "
    # 只替换 checkbox 标记；缩进、列表符号和任务文本都原样保留。
    lines[line_index] = (
        old_line.replace("[x]", f"[{new_state}]", 1)
        .replace("[X]", f"[{new_state}]", 1)
        .replace("[ ]", f"[{new_state}]", 1)
    )
    _write_lines(path, lines)

    return {
        "path": path,
        "task_index": task_index,
        "line": task["line"],
        "old_done": task["done"],
        "new_done": done,
        "text": task["text"],
    }
