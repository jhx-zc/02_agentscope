---
name: plan-mode-task-management
description: Use this skill when task mode, plan mode, internal task tracking, or structured task execution is enabled or requested. This skill governs TaskCreate, TaskUpdate, and TaskList operations; it is not for Markdown task list editing. It enforces complete research and planning before task creation to prevent fragmented task creation during execution.
---

# Plan Mode Task Management Skill

This skill defines how to operate when task mode, plan mode, or structured task execution is enabled.

Plan mode means using the task management tools:

```text
TaskCreate
TaskUpdate
TaskList
```

Plan mode does **not** mean creating or editing Markdown task lists such as `- [ ]` or `- [x]`.

Tool activation uses `reset_tools`, whose arguments are the final active tool
state, not incremental changes. Before calling `reset_tools`, first read every
skill that is relevant to the current user turn.

If task management tools are not currently available, activate them together
with every other tool group that must remain available:

```text
reset_tools(task_management=true)
```

If the task also requires Markdown or memory tools, include those groups in the
same call, for example:

```text
reset_tools(task_management=true, markdown_read=true, memory=true)
```

If you call `reset_tools` again later, keep every still-needed group set to true.

Do not call `Skill` again for `plan-mode-task-management` after this skill has already been read in the current user turn.

## Core principle

When this skill is active, the agent must follow this sequence:

```text
Research fully → Plan completely → Create the complete task list → Execute tasks one by one → Verify completion
```

The agent must **not** create tasks before it has performed enough research and analysis to understand the full scope of the work.

The agent must **not** repeatedly create new tasks during execution simply because it failed to plan thoroughly at the beginning.

## When to use this skill

Use this skill when any of the following is true:

1. The user explicitly enables task mode or plan mode.
2. The user asks the agent to plan, track, manage, or execute work through internal tasks.
3. The system or runtime indicates that task mode is enabled.
4. The request is complex enough that the agent is expected to maintain task state with task management tools.

## Required workflow

### 1. Research and understand before creating tasks

Before calling `TaskCreate`, the agent must complete a research and analysis phase.

During this phase, the agent must:

- Read and understand the full user request.
- Identify the user's objective, expected output, constraints, success criteria, and implied requirements.
- Inspect relevant files, code, context, documentation, project structure, or external sources when needed.
- Determine dependencies, risks, unknowns, and execution order.
- Build a complete mental model of the work before task creation.

During this phase, the agent must **not** call:

```text
TaskCreate
TaskUpdate
TaskList
```

unless the runtime explicitly requires task tools to be used immediately.

If more information is needed and it can be obtained through available tools, the agent should gather it before creating tasks.

If information is unavailable, the agent should make a reasonable assumption, note it internally, and include a task that validates or handles that assumption.

### 2. Decide whether the plan is ready

Before creating tasks, the agent must verify that it can answer all of the following:

1. What is the final deliverable?
2. What are the major phases of work?
3. What must be investigated before implementation?
4. What must be implemented, edited, created, or executed?
5. What must be tested or verified?
6. What dependencies exist between subtasks?
7. What conditions indicate the work is complete?

If the answer to any of these is unclear, continue researching or analyzing before creating tasks.

### 3. Decompose the complete plan into subtasks

After research is complete, break the user's request into independent subtasks that can be executed and verified separately.

Each subtask must have:

- A concise title.
- A short description.
- A clear completion condition.
- Any important dependency information.

Do not create vague tasks such as:

- `handle request`
- `finish work`
- `continue implementation`
- `do remaining tasks`
- `miscellaneous fixes`

Tasks should represent stable units of work, not guesses made before understanding the problem.

### 4. Create the complete task list before execution

For each planned subtask, call `TaskCreate`.

The initial task list should cover the entire known scope of work, including:

- Research or inspection tasks already determined to be needed.
- Implementation or editing tasks.
- Testing, validation, review, or final verification tasks.
- Documentation or response preparation tasks, if required.

Immediately after creating each task, call `TaskUpdate` to set its status to:

```text
pending
```

The agent should create the complete task list before starting execution.

Do **not** create one task, execute it, discover the next task, create it, execute it, and repeat. That pattern indicates insufficient planning.

### 5. Verify task coverage before execution

After creating and initializing all tasks, call `TaskList`.

Check that the task list covers:

- The user's explicit requirements.
- The user's implied requirements.
- Required research and inspection.
- Required implementation or creation.
- Required testing and verification.
- Required final response or handoff.

If any required action is missing, create and initialize the missing task **before execution begins**.

Once execution begins, avoid adding new tasks unless a genuinely new requirement, blocker, or discovery appears that could not reasonably have been known during the initial research phase.

### 6. Execute tasks and synchronize status

Use `TaskList` to decide which task should be handled next.

Before starting a task, call `TaskUpdate` to set its status to:

```text
in_progress
```

After the task is actually finished, immediately call `TaskUpdate` to set its status to:

```text
completed
```

Do not mark a task as completed before its completion condition is satisfied.

Only one task should normally be `in_progress` at a time unless the task system explicitly supports parallel execution.

### 7. Handle dependencies

If a task depends on another task, use `add_blocked_by` through `TaskUpdate` to mark the dependency.

Prioritize completing blocking tasks before blocked tasks.

Do not start a blocked task until its dependencies are completed.

### 8. Adding tasks during execution

Adding tasks during execution is allowed only when one of the following is true:

1. A new requirement is discovered that could not reasonably have been identified during the initial research phase.
2. The user changes or expands the request.
3. A blocker requires a dedicated resolution task.
4. Verification reveals a concrete missing action required for correctness.

Before adding a task during execution, the agent must:

1. Explain internally why the task was not knowable earlier.
2. Call `TaskList` to inspect the current plan.
3. Create the new task with a specific title and completion condition.
4. Initialize it as `pending`.
5. Add dependencies if needed.

The agent must not add vague catch-up tasks to compensate for weak initial planning.

### 9. Final verification

Before producing the final response, call `TaskList` again.

Only finalize when every required task is marked:

```text
completed
```

If any task is still `pending`, `in_progress`, or blocked, continue execution instead of finalizing.

Also verify that:

- The final deliverable satisfies the user's request.
- The implementation or output has been tested or reviewed where applicable.
- No required action was silently omitted.
- No unnecessary tasks remain open.

## Final response rule

When all tasks are completed, the final response must begin with:

```text
✅ 所有任务已完成。
```

Then provide the integrated result, summary, file links, or handoff required by the user.

## Prohibited behavior

Do not treat plan mode as Markdown checklist editing.

Do not create Markdown task lists as a substitute for `TaskCreate`, `TaskUpdate`, and `TaskList`.

Do not call `TaskCreate` before completing sufficient research and analysis.

Do not create tasks one by one during execution as a substitute for upfront planning.

Do not begin execution before verifying task coverage with `TaskList`.

Do not skip `TaskList` verification before the final answer.

Do not output the final answer while any task remains incomplete.

Do not silently omit required actions from the task plan.

Do not create vague, generic, or placeholder tasks.

Do not mark a task as completed before its completion condition is actually met.

## Preferred behavior summary

The preferred behavior is:

```text
1. Fully investigate the request and relevant context.
2. Build a complete plan mentally.
3. Create all required tasks together.
4. Initialize every task as pending.
5. Verify task coverage with TaskList.
6. Execute tasks sequentially with status updates.
7. Add new tasks only for genuinely new or unknowable discoveries.
8. Verify all tasks are completed before final response.
```
