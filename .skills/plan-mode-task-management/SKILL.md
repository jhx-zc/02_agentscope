---
name: plan-mode-task-management
description: 当任务需要内部任务规划、任务状态跟踪、结构化执行，或用户明确要求 plan mode/task mode 时使用；不要用于编辑 Markdown 任务列表。
---

# Plan Mode Task Management Skill

这个 skill 规定何时以及如何使用 AgentScope 的任务管理工具。

## 工具组

- 内部任务创建、查看、列出、更新：`task_management`

如果任务管理工具尚不可用，按 system prompt 中的 `reset_tools` 最终状态协议激活工具组，并保留当前任务仍需使用的其他工具组。

## 使用边界

Plan mode 指使用：

```text
TaskCreate
TaskUpdate
TaskList
TaskGet
```

它不是 Markdown 清单编辑，不要用它替代 `- [ ]` 或 `- [x]` 的文档修改。

## 核心流程

1. 先读取当前回合其他相关 skills。
2. 完整理解用户目标、约束、交付物和完成条件。
3. 在创建任务前完成必要的文件、代码或上下文调查。
4. 一次性创建覆盖已知范围的任务列表，避免边做边零散补任务。
5. 每次只推进一个主要任务：开始前标记 `in_progress`，完成后标记 `completed`。
6. 使用 `TaskList` 检查任务覆盖和剩余状态。
7. 所有必要任务完成后，再给用户最终答复。

## 禁止行为

- 不要在充分调查前调用 `TaskCreate`。
- 不要创建含糊任务，例如 `handle request`、`finish work`、`miscellaneous fixes`。
- 不要把未完成任务标记为完成。
- 不要在仍有必要任务未完成时输出最终答复。
