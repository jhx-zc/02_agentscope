"""Parser 工具的兼容 CLI 入口（已迁移至 ``org_tools/cli.py``）。

保留此文件仅为向后兼容。
"""

from agentscope_tools.org_tools.cli import main, markdown_get_section, markdown_outline

__all__ = ["main", "markdown_get_section", "markdown_outline"]
