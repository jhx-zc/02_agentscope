"""Markdown Formatter 工具。

格式化工具单独放置，因为 mdformat 可能重写整篇文档中的空白、表格对齐和列表间距，
不应和 Parser/Editor 的局部读写逻辑混在一起。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def markdown_format_file(path: str, extensions: list[str] | None = None) -> dict[str, Any]:
    """Format a Markdown file in place with mdformat.

    Args:
        path: Path to the Markdown file to format.
        extensions: Optional mdformat extension names. Defaults to ``["gfm"]``
            so GitHub-flavored tables and task lists are handled consistently.

    Returns:
        A dictionary with:
        ``path``: Formatted file path.
        ``changed``: Whether mdformat changed the file contents.
        ``extensions``: Sorted extension names used for formatting.
    """
    import mdformat

    markdown_path = Path(path)
    selected_extensions = set(extensions or ["gfm"])
    before = markdown_path.read_text(encoding="utf-8")

    # mdformat.file 会直接原地改写文件；前后对比用于告诉调用方是否真的发生变化。
    mdformat.file(str(markdown_path), extensions=selected_extensions)

    after = markdown_path.read_text(encoding="utf-8")
    return {
        "path": str(markdown_path),
        "changed": before != after,
        "extensions": sorted(selected_extensions),
    }


def markdown_check_format(path: str, extensions: list[str] | None = None) -> dict[str, Any]:
    """Check whether a Markdown file already matches mdformat output.

    Args:
        path: Path to the Markdown file to check.
        extensions: Optional mdformat extension names. Defaults to ``["gfm"]``.

    Returns:
        A dictionary with:
        ``path``: Checked file path.
        ``formatted``: ``True`` if the current text equals mdformat output.
        ``extensions``: Sorted extension names used for the check.
    """
    import mdformat

    markdown_path = Path(path)
    selected_extensions = set(extensions or ["gfm"])
    text = markdown_path.read_text(encoding="utf-8")
    # 检查模式使用 mdformat.text，不调用 mdformat.file，确保不会写入源文件。
    formatted = mdformat.text(text, extensions=selected_extensions)

    return {
        "path": str(markdown_path),
        "formatted": text == formatted,
        "extensions": sorted(selected_extensions),
    }
