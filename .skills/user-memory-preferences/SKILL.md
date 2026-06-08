---
name: user-memory-preferences
description: Use this skill when the current task may depend on the user's stored preferences, long-running choices, prior instructions, or when the user explicitly asks to remember, save, record, update, forget, or apply a preference in the future.
---

# User Memory Preferences Skill

This skill defines when and how to safely read and save user preferences.

## When to check memory

Check memory when stored preferences or prior user choices could materially affect the current response.

Use `user_memory_outline` before answering when the task involves any of these cases:

1. The user asks for a personalized output, such as writing style, formatting style, coding style, language preference, workflow preference, or project convention.
2. The user refers to an existing preference, prior choice, saved setting, usual workflow, or something they expect the agent to already know.
3. The task continues a long-running project, document, codebase, workspace, research thread, or repeated workflow where saved preferences may affect decisions.
4. The user asks to apply previous preferences, remember something, save something, record something, update memory, or use it in the future.
5. The response could be better or more accurate if a known preference is applied, and the relevant preference key can be identified from the memory outline.

Do not check memory for every ordinary request. Only check it when memory is likely to be relevant.

## When not to check memory

Do not call memory tools when:

1. The request is a one-off factual question, calculation, translation, or simple explanation with no personalization need.
2. The user provides all required preferences directly in the current message.
3. The task can be completed without relying on prior user-specific information.
4. The only reason to check memory is curiosity or broad context gathering.

## Core rule

Always inspect the memory outline before loading specific memory values.

Tool activation uses `reset_tools`, whose arguments are the final active tool
state, not incremental changes. Before calling `reset_tools`, first read every
skill that is relevant to the current user turn.

If memory tools are not currently available, activate them together with every
other tool group that must remain available:

```text
reset_tools(memory=true)
```

If the task also requires Markdown or task management tools, include those
groups in the same call, for example:

```text
reset_tools(memory=true, markdown_read=true, task_management=true)
```

If you call `reset_tools` again later, keep every still-needed group set to true.

Do not call `Skill` again for `user-memory-preferences` after this skill has already been read in the current user turn.

Call:

```text
user_memory_outline
```

before calling any preference retrieval tool.

## Reading preferences

Use this sequence:

1. Decide whether memory is relevant using the "When to check memory" section above.
2. If memory is relevant, call `user_memory_outline`.
3. Identify only the specific preference keys that are relevant to the current task.
4. Call `user_memory_get_preference` only for those specific keys.
5. Apply the retrieved preferences only when they are relevant to the user's current request.

Do not bulk-load unrelated preferences.

## Saving preferences

Use `user_memory_save_preference` only when the user explicitly asks to remember, save, record, update, or apply a preference in the future.

Examples of explicit save requests:

```text
Remember that I prefer concise answers.
Save this preference for next time.
Record that I like Markdown tables.
Apply this preference in future conversations.
Use this coding style from now on.
```

Do not save preferences based only on ordinary conversation.

Incorrect:

```text
User says: "I like concise answers."
Action: silently save this as a long-term preference.
```

Correct:

```text
User says: "I like concise answers."
Action: use that preference for the current response only, unless the user explicitly asks to remember it.
```

## Safety rules

Do not infer and save long-term preferences silently.

Do not save sensitive, private, or identity-related information unless the user explicitly asks and the memory system policy allows it.

If the user's intent to save is ambiguous, ask for confirmation before calling `user_memory_save_preference`.
