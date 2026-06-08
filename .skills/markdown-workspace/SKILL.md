---
name: markdown-workspace
description: 当任务涉及查找、读取、编辑、整理当前工作区中的 Markdown 文件时使用。
---

# Markdown Workspace Skill

这个 skill 规定如何处理当前工作区中的 Markdown 文件。

## 工具组

- 只读扫描、读取、提纲、格式检查：`markdown_read`
- 编辑或格式化 Markdown：`markdown_read` + `markdown_write`

如果所需工具尚不可用，按 system prompt 中的 `reset_tools` 最终状态协议激活工具组，并保留当前任务仍需使用的其他工具组。

## 核心规则

使用任何具体 Markdown 文件工具前，必须先调用：

```text
markdown_scan_directory
```

不要传入 path 参数。

## 流程

1. 先读取当前回合其他相关 skills。
2. 激活当前任务需要的完整工具组集合。
3. 调用 `markdown_scan_directory` 扫描工作区 Markdown 文件。
4. 后续 Markdown 工具必须使用扫描结果返回的完整 path。
5. 不要手写、改写、缩短或猜测文件路径。
6. 如果目标文件不在扫描结果中，直接说明未找到，不要猜路径。

## 不使用场景

任务不涉及 Markdown 文件时不要使用本 skill，除非用户明确要求定位 Markdown 文件。
