---
name: markdown-workspace
description: Use this skill when the task involves finding, reading, editing, or operating on Markdown files in the current workspace.
---

# Markdown Workspace Skill

This skill defines how to work with Markdown files in the current workspace.

## Core rule

Before using any Markdown file-specific tool, first discover the available Markdown files.

Call:

```text
markdown_scan_directory
```

without passing a path.

## Procedure

1. Call `markdown_scan_directory` without a path to scan the current workspace.
2. Inspect the returned file path values.
3. When calling other Markdown tools, use the exact file path values returned by `markdown_scan_directory`.
4. Do not invent, normalize, shorten, or rewrite file paths manually.
5. If the needed Markdown file is not returned by the scan, report that it was not found instead of guessing a path.

## When not to use this skill

Do not use this skill for non-Markdown files unless the user explicitly asks to locate Markdown files as part of the task.
