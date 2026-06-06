---
name: plan-mode-task-management
description: Use this skill when task mode, plan mode, internal task tracking, or structured task execution is enabled or requested. This skill governs TaskCreate, TaskUpdate, and TaskList operations; it is not for Markdown task list editing.
---

# Plan Mode Task Management Skill

This skill defines how to operate when task mode, plan mode, or structured task execution is enabled.

Plan mode means using the task management tools:

```text
TaskCreate
TaskUpdate
TaskList
```

Plan mode does not mean creating or editing Markdown task lists such as `- [ ]` or `- [x]`.

## When to use this skill

Use this skill when any of the following is true:

1. The user explicitly enables task mode or plan mode.
2. The user asks the agent to plan, track, manage, or execute work through internal tasks.
3. The system or runtime indicates that task mode is enabled.
4. The request is complex enough that the agent is expected to maintain task state with task management tools.

## Core requirement

When this skill is active, maintain a clear internal task state with task management tools. Do not skip task creation, status initialization, status updates, or final verification.

Before finalizing the answer, verify through `TaskList` that every required action is covered by a task and that every task is completed.

## Required workflow

### 1. Decompose

Break the user's request into independent subtasks that can be executed and verified separately.

Each subtask should have:

- A concise title.
- A short description.
- A clear completion condition.

Do not create vague tasks such as "handle request" or "finish work".

### 2. Create tasks

For each subtask, call `TaskCreate`.

Only provide a concise title and description unless the tool schema requires more fields.

### 3. Initialize task status

Immediately after creating each task, call `TaskUpdate` to set its status to:

```text
pending
```

Do this for every newly created task.

### 4. Verify task coverage

After creating and initializing tasks, call `TaskList`.

Check that the task list covers every required step in the user's request.

If any required action is missing, create and initialize an additional task before execution begins.

### 5. Execute and synchronize status

Use `TaskList` to decide which task should be handled next.

Before starting a task, call `TaskUpdate` to set its status to:

```text
in_progress
```

After the task is finished, immediately call `TaskUpdate` to set its status to:

```text
completed
```

Do not mark a task as completed before its actual work is done.

### 6. Handle dependencies

If a task depends on another task, use `add_blocked_by` through `TaskUpdate` to mark the dependency.

Prioritize completing blocking tasks before blocked tasks.

Do not start a blocked task until its dependencies are completed.

### 7. Final verification

Before producing the final response, call `TaskList` again.

Only finalize when all subtasks are marked:

```text
completed
```

If any task is still `pending`, `in_progress`, or blocked, continue execution instead of finalizing.

## Final response rule

When all tasks are completed, the final response must begin with:

```text
✅ 所有任务已完成。
```

Then provide the integrated result.

## Prohibited behavior

Do not treat plan mode as Markdown checklist editing.

Do not create Markdown task lists as a substitute for `TaskCreate`, `TaskUpdate`, and `TaskList`.

Do not skip `TaskList` verification before the final answer.

Do not output the final answer while any task remains incomplete.

Do not silently omit required actions from the task plan.
