"""Parser 工具的兼容 CLI 入口。

真正的 Parser、Editor、Formatter 实现在各自文件中：
``agentscope_tools.parser``、``agentscope_tools.editor``、``agentscope_tools.formatter``。
这个模块只保留之前手动测试用的命令行入口。
"""

import argparse
import json

from agentscope_tools.parser import markdown_get_section, markdown_outline


def main() -> None:
    """Run the small JSON CLI for outlines or a single section.

    Args:
        None. Arguments are read from the command line.

    Returns:
        None. The selected outline or section is printed as JSON.
    """
    parser = argparse.ArgumentParser(description="Work with Markdown sections.")
    parser.add_argument("--path", default='Test.md', help="Path to the Markdown file")
    parser.add_argument("--heading", help="Heading text to return as a section")
    parser.add_argument("--occurrence", type=int, default=1, help="1-based heading occurrence")
    args = parser.parse_args()

    if args.heading:
        result = markdown_get_section(args.path, args.heading, args.occurrence)
    else:
        result = markdown_outline(args.path)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


__all__ = ["markdown_get_section", "markdown_outline"]
