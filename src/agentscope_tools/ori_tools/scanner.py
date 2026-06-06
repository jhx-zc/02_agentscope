"""Markdown directory scanner tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

MARKDOWN_SUFFIXES = {".md", ".markdown"}
WORKSPACE_ROOT = Path.cwd().resolve()
SKILLS_ROOTS = [f'{(WORKSPACE_ROOT / ".skills" / "markdown-workspace").resolve()}',
                 f'{(WORKSPACE_ROOT / ".skills" / "plan-mode-task-management").resolve()}',
                   f'{(WORKSPACE_ROOT / ".skills" / "user-memory-preferences").resolve()}']

for SKILLS_ROOT in SKILLS_ROOTS:
    if not Path(SKILLS_ROOT).is_dir():
        raise NotADirectoryError(f"Expected skills directory at: {SKILLS_ROOT}")


def _is_hidden_path(path: Path) -> bool:
    """Return whether any relative path component is hidden."""
    return any(part.startswith(".") for part in path.parts)


def markdown_scan_directory(
    path: str | None = None,
    recursive: bool = True,
    include_hidden: bool = False,
) -> dict[str, Any]:
    """Scan a directory for Markdown files.

    Args:
        path: Path to the directory to scan. When omitted, scans the workspace
            directory captured from the app startup directory.
        recursive: Whether to scan nested directories. Defaults to ``True``.
        include_hidden: Whether to include hidden files and directories whose
            names start with ``.``. Defaults to ``False``.

    Returns:
        A dictionary containing:
        ``root``: Absolute scanned directory path.
        ``recursive``: Whether nested directories were scanned.
        ``include_hidden``: Whether hidden paths were included.
        ``extensions``: Markdown suffixes included in the scan.
        ``count``: Number of Markdown files found.
        ``files``: Sorted file entries. Each entry contains ``path`` as an
        absolute path that can be passed to other Markdown tools,
        ``relative_path``, ``name`` and ``size_bytes``.

    Raises:
        ValueError: If ``path`` is not an existing directory.
    """
    root = Path(path).expanduser().resolve() if path else WORKSPACE_ROOT
    if not root.is_dir():
        raise ValueError(f"path must be an existing directory: {path}")

    candidates = root.rglob("*") if recursive else root.iterdir()
    files: list[dict[str, Any]] = []

    for candidate in candidates:
        if not candidate.is_file():
            continue

        relative_path = candidate.relative_to(root)
        if not include_hidden and _is_hidden_path(relative_path):
            continue
        if candidate.suffix.lower() not in MARKDOWN_SUFFIXES:
            continue

        files.append(
            {
                "path": str(candidate.resolve()),
                "relative_path": relative_path.as_posix(),
                "name": candidate.name,
                "size_bytes": candidate.stat().st_size,
            }
        )

    files.sort(key=lambda item: item["relative_path"])

    return {
        "root": str(root),
        "workspace": str(WORKSPACE_ROOT),
        "recursive": recursive,
        "include_hidden": include_hidden,
        "extensions": sorted(MARKDOWN_SUFFIXES),
        "count": len(files),
        "files": files,
    }
