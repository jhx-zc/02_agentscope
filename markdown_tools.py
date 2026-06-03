from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt


def markdown_outline(path: str) -> list[dict[str, Any]]:
    """Return a nested heading outline for a Markdown file.

    Line numbers are 1-based and inclusive. ``section_end`` is the line before
    the next same-level or higher-level heading, or the last line of the file.
    """
    markdown_path = Path(path)
    text = markdown_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tokens = MarkdownIt("commonmark").parse(text)

    flat_headings: list[dict[str, Any]] = []

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

    for index, heading in enumerate(flat_headings):
        for next_heading in flat_headings[index + 1 :]:
            if next_heading["level"] <= heading["level"]:
                heading["section_end"] = next_heading["line_start"] - 1
                break

    outline: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []

    for heading in flat_headings:
        while stack and stack[-1]["level"] >= heading["level"]:
            stack.pop()

        if stack:
            stack[-1]["children"].append(heading)
        else:
            outline.append(heading)

        stack.append(heading)

    return outline


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a Markdown heading outline as JSON.")
    parser.add_argument("path", help="Path to the Markdown file")
    args = parser.parse_args()

    print(json.dumps(markdown_outline(args.path), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
