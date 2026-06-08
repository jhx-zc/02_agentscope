---
name: markdown-workspace
description: Use this skill when the task involves finding, reading, editing, or operating on Markdown files in the current workspace.
---

# Markdown Workspace Skill

This skill defines how to work with Markdown files in the current workspace.

## Core rule

Before using any Markdown file-specific tool, first discover the available Markdown files.

Tool activation uses `reset_tools`, whose arguments are the final active tool
state, not incremental changes. Before calling `reset_tools`, first read every
skill that is relevant to the current user turn.

If Markdown tools are not currently available, activate Markdown tools together
with every other tool group that must remain available.

For Markdown reading only:

```text
reset_tools(markdown_read=true)
```

For Markdown editing or formatting:

```text
reset_tools(markdown_read=true, markdown_write=true)
```

If the task also requires memory or task management, include those groups in the
same call, for example:

```text
reset_tools(markdown_read=true, markdown_write=true, memory=true, task_management=true)
```

If you call `reset_tools` again later, keep every still-needed group set to true.

Do not call `Skill` again for `markdown-workspace` after this skill has already been read in the current user turn.

Call:

```text
markdown_scan_directory
```

without passing a path.

## Procedure

1. Read all other skills that are relevant to the current user turn.
2. If Markdown tools are not available, activate the needed Markdown tool groups plus every other still-needed group with one `reset_tools` call.
3. Call `markdown_scan_directory` without a path to scan the current workspace.
4. Inspect the returned file path values.
5. When calling other Markdown tools, use the exact file path values returned by `markdown_scan_directory`.
6. Do not invent, normalize, shorten, or rewrite file paths manually.
7. If the needed Markdown file is not returned by the scan, report that it was not found instead of guessing a path.

## When not to use this skill

Do not use this skill for non-Markdown files unless the user explicitly asks to locate Markdown files as part of the task.
