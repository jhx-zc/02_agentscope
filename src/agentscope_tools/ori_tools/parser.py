"""Markdown Parser 工具。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token


def _read_markdown(path: str) -> str:
    """Read a Markdown file as UTF-8 text.

    Args:
        path: Path to the Markdown file.

    Returns:
        The raw Markdown text.
    """
    return Path(path).read_text(encoding="utf-8")


def _markdown_parser() -> MarkdownIt:
    """Create the Markdown parser used by all parser tools.

    Returns:
        A CommonMark-compatible ``MarkdownIt`` parser.
    """
    return MarkdownIt("commonmark")


def markdown_outline(path: str) -> list[dict[str, Any]]:
    """Build a nested heading outline for a Markdown file.

    Args:
        path: Path to the Markdown file.

    Returns:
        A heading tree. Each heading dict contains:
        ``level``: Heading level from 1 to 6.
        ``title``: Parsed heading text.
        ``line_start``: 1-based heading start line.
        ``line_end``: 1-based heading end line.
        ``section_start``: 1-based start line of the full section.
        ``section_end``: 1-based inclusive end line before the next same-level
        or higher-level heading.
        ``children``: Nested child heading dictionaries.
    """
    text = _read_markdown(path)
    lines = text.splitlines()
    # 使用MarkdownIt工具解析markdown格式的文本
    tokens: list[Token] = _markdown_parser().parse(text)

    flat_headings: list[dict[str, Token]] = []

    # 第一遍：从 token 中提取标题，并记录源码行号范围。
    # markdown-it-py 会把块级元素的行号范围放在 token.map 中。
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or not token.map:
            continue
        # Head token之后下一个就是它的内容token， 表示该标题内容
        inline_token = tokens[index + 1] if index + 1 < len(tokens) else None
        title = inline_token.content if inline_token and inline_token.type == "inline" else ""
        level = int(token.tag.removeprefix("h"))
        line_start = token.map[0] + 1
        line_end = token.map[1]

        flat_headings.append(
            {
                "level": level,
                "title": title,
                "line_start": line_start,
                "line_end": line_end,
                "section_start": line_start,
                "section_end": len(lines),
                "children": [],
            }
        )

    # 一个章节会在下一个同级或更高级标题前结束。
    for index, heading in enumerate(flat_headings):
        for next_heading in flat_headings[index + 1 :]:
            if next_heading["level"] <= heading["level"]:
                heading["section_end"] = next_heading["line_start"] - 1
                break

    outline: list[dict[str, Token]] = []
    stack: list[dict[str, Token]] = []

    # 第二遍：用栈把扁平标题列表组织成父子树。子标题全部归纳到父标题下
    for heading in flat_headings:
        while stack and stack[-1]["level"] >= heading["level"]:
            stack.pop()

        if stack:
            stack[-1]["children"].append(heading)
        else:
            outline.append(heading)

        stack.append(heading)

    return outline


def iter_outline(outline: list[dict[str, Token]]) -> list[dict[str, Token]]:
    """Flatten a nested outline while preserving document order.

    Args:
        outline: A heading tree returned by ``markdown_outline``.

    Returns:
        A flat list of heading dictionaries in the order they appear in the
        Markdown document.
    """
    headings: list[dict[str, Token]] = []

    for heading in outline:
        headings.append(heading)
        headings.extend(iter_outline(heading["children"]))

    return headings


def markdown_get_section(path: str, heading: str, occurrence: int = 1) -> dict[str, Any]:
    """Return the original Markdown text for a heading section.

    Args:
        path: Path to the Markdown file.
        heading: Exact heading title to match, using the parsed title text. For
            example, a heading written as ``### `name` `` is matched by
            ``"`name`"``.
        occurrence: 1-based occurrence when the same heading title appears more
            than once.

    Returns:
        A section dictionary containing heading metadata plus ``content``, the
        raw Markdown text from ``section_start`` through ``section_end``.

    Raises:
        ValueError: If ``occurrence`` is less than 1 or the requested heading
        occurrence cannot be found.
    """

    # 目标title的层级
    if occurrence < 1:
        raise ValueError("occurrence must be greater than or equal to 1")

    text = _read_markdown(path)
    lines = text.splitlines(keepends=True)
    headings = iter_outline(markdown_outline(path))
    # 获取全部标题中匹配到的这个
    matches = [
        item
        for item in headings
        if item["title"] == heading
    ]

    if len(matches) < occurrence:
        raise ValueError(f"heading {heading!r} occurrence {occurrence} was not found")

    # 在计算机里 从0开始计算
    selected = matches[occurrence - 1]
    section_start = selected["section_start"]
    section_end = selected["section_end"]

    return {
        "level": selected["level"],
        "title": selected["title"],
        "line_start": selected["line_start"],
        "line_end": selected["line_end"],
        "section_start": section_start,
        "section_end": section_end,
        "content": "".join(lines[section_start - 1 : section_end]),
    }


def _containing_section(line_number: int, headings: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the most specific heading section that contains a line.

    Args:
        line_number: 1-based source line number.
        headings: Flat list of heading dictionaries.

    Returns:
        The deepest heading section containing ``line_number``, or ``None`` if
        the line is outside every heading section.
    """
    matches = [
        heading
        for heading in headings
        if heading["section_start"] <= line_number <= heading["section_end"]
    ]
    if not matches:
        return None
    return max(matches, key=lambda heading: heading["level"])


TASK_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>[-+*])\s+\[(?P<state>[ xX])\]\s+(?P<text>.*)$")


def markdown_list_tasks(path: str) -> list[dict[str, Any]]:
    """List standard task list items in the markdown file.

    Args:
        path: Path to the Markdown file.

    Returns:
        A list of task dictionaries. Each item contains:
        ``index``: 1-based task index.
        ``done``: ``True`` for ``[x]`` or ``[X]``, otherwise ``False``.
        ``text``: Task text after the checkbox.
        ``line``: 1-based source line number.
        ``marker``: List marker, such as ``-`` or ``*``.
        ``section``: The containing heading section, or ``None``.
    """
    lines = _read_markdown(path).splitlines()
    headings = iter_outline(markdown_outline(path))
    tasks: list[dict[str, Any]] = []

    # 任务状态适合按原始文本行处理；解析器负责定位结构，checkbox 本身是文本状态。
    for line_index, line in enumerate(lines, start=1):
        match = TASK_RE.match(line)
        if not match:
            continue

        section = _containing_section(line_index, headings)
        tasks.append(
            {
                "index": len(tasks) + 1,
                "done": match.group("state").lower() == "x",
                "text": match.group("text"),
                "line": line_index,
                "marker": match.group("marker"),
                "section": section,
            }
        )

    return tasks
