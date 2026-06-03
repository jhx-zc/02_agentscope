"""Markdown Parser 工具。

本模块只读取 Markdown 文件，不写回磁盘。Editor 工具应复用这里的解析结果，
避免重复实现标题范围、代码块范围和任务索引逻辑。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt


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
    tokens = _markdown_parser().parse(text)

    flat_headings: list[dict[str, Any]] = []

    # 第一遍：从 token 中提取标题，并记录源码行号范围。
    # markdown-it-py 会把块级元素的行号范围放在 token.map 中。
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or not token.map:
            continue

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

    outline: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []

    # 第二遍：用栈把扁平标题列表组织成父子树。
    for heading in flat_headings:
        while stack and stack[-1]["level"] >= heading["level"]:
            stack.pop()

        if stack:
            stack[-1]["children"].append(heading)
        else:
            outline.append(heading)

        stack.append(heading)

    return outline


def iter_outline(outline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten a nested outline while preserving document order.

    Args:
        outline: A heading tree returned by ``markdown_outline``.

    Returns:
        A flat list of heading dictionaries in the order they appear in the
        Markdown document.
    """
    headings: list[dict[str, Any]] = []

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
    if occurrence < 1:
        raise ValueError("occurrence must be greater than or equal to 1")

    text = _read_markdown(path)
    lines = text.splitlines(keepends=True)
    # 复用 outline，让所有按章节工作的工具共享同一套章节范围定义。
    matches = [
        item
        for item in iter_outline(markdown_outline(path))
        if item["title"] == heading
    ]

    if len(matches) < occurrence:
        raise ValueError(f"heading {heading!r} occurrence {occurrence} was not found")

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


def markdown_list_code_blocks(path: str, language: str | None = None) -> list[dict[str, Any]]:
    """List fenced and indented code blocks from a Markdown file.

    Args:
        path: Path to the Markdown file.
        language: Optional language filter. For fenced blocks this matches the
            first word after the opening fence, such as ``python`` in
            `````python``.

    Returns:
        A list of code block dictionaries. Each item contains:
        ``index``: 1-based index after applying the optional language filter.
        ``type``: markdown-it token type, either ``fence`` or ``code_block``.
        ``language``: Parsed fenced language, or ``None``.
        ``info``: Full fenced info string.
        ``content``: Code block body text.
        ``line_start`` / ``line_end``: 1-based inclusive block range including
        fences for fenced blocks.
        ``content_start`` / ``content_end``: 1-based inclusive body range used
        by editor tools.
        ``section``: The containing heading section, or ``None``.
    """
    text = _read_markdown(path)
    tokens = _markdown_parser().parse(text)
    headings = iter_outline(markdown_outline(path))
    blocks: list[dict[str, Any]] = []

    # markdown-it-py 用 "fence" 表示围栏代码块，用 "code_block" 表示缩进代码块。
    # 两类 token 都会包含 token.content 和 token.map。
    for token in tokens:
        if token.type not in {"fence", "code_block"} or not token.map:
            continue

        info = token.info.strip() if token.type == "fence" else ""
        block_language = info.split(maxsplit=1)[0] if info else None
        if language is not None and block_language != language:
            continue

        line_start = token.map[0] + 1
        line_end = token.map[1]
        section = _containing_section(line_start, headings)
        block: dict[str, Any] = {
            "index": len(blocks) + 1,
            "type": token.type,
            "language": block_language,
            "info": info,
            "content": token.content,
            "line_start": line_start,
            "line_end": line_end,
            "section": section,
        }

        # 围栏代码块的 token.map 包含起止 fence 行，token.content 只包含中间代码正文。
        if token.type == "fence":
            block["content_start"] = line_start + 1
            block["content_end"] = max(line_start, line_end - 1)
        else:
            block["content_start"] = line_start
            block["content_end"] = line_end

        blocks.append(block)

    return blocks


TASK_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>[-+*])\s+\[(?P<state>[ xX])\]\s+(?P<text>.*)$")


def markdown_list_tasks(path: str) -> list[dict[str, Any]]:
    """List standard Markdown task list items.

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


def markdown_word_count(path: str) -> dict[str, Any]:
    """Count Markdown words and estimate reading time.

    Args:
        path: Path to the Markdown file.

    Returns:
        A dictionary with:
        ``word_count``: Count from ``mdit-py-plugins`` when available, otherwise
        a local fallback count.
        ``reading_time_minutes``: Estimated reading time using 200 words per
        minute, with a minimum of 1 minute.
        ``plugin_wordcount``: Raw plugin value, or ``None`` when unavailable.
    """
    text = _read_markdown(path)
    env: dict[str, Any] = {}
    plugin_result: Any = None

    try:
        from mdit_py_plugins.wordcount import wordcount_plugin
    except ImportError:
        wordcount_plugin = None

    if wordcount_plugin:
        MarkdownIt("commonmark").use(wordcount_plugin).render(text, env)
        plugin_result = env.get("wordcount")

    # 兜底统计规则：每个中日韩字符算一个单位，连续英文/数字词算一个单位。
    # 这样即使插件不可用，函数仍然可以返回可用结果。
    fallback_units = re.findall(r"[\u4e00-\u9fff]|[A-Za-z0-9_]+(?:[-'][A-Za-z0-9_]+)*", text)
    word_count = plugin_result if isinstance(plugin_result, int) else len(fallback_units)

    return {
        "word_count": word_count,
        "reading_time_minutes": max(1, round(word_count / 200)),
        "plugin_wordcount": plugin_result,
    }


def markdown_render_html(path: str, plugins: list[str] | None = None) -> str:
    """Render Markdown to HTML.

    Args:
        path: Path to the Markdown file.
        plugins: Optional plugin names to enable. Supported values are
            ``"tasklists"`` and ``"wordcount"``.

    Returns:
        Rendered HTML string.

    Raises:
        ValueError: If an unsupported plugin name is provided.
    """
    md = MarkdownIt("commonmark")

    # 插件按需启用，默认渲染保持 CommonMark 行为，避免给普通 HTML 预览引入额外差异。
    for plugin in plugins or []:
        if plugin == "tasklists":
            from mdit_py_plugins.tasklists import tasklists_plugin

            md.use(tasklists_plugin)
        elif plugin == "wordcount":
            from mdit_py_plugins.wordcount import wordcount_plugin

            md.use(wordcount_plugin)
        else:
            raise ValueError(f"unsupported plugin: {plugin}")

    return md.render(_read_markdown(path))
