---
name: user-memory-preferences
description: Use this skill when the task requires reading, applying, or saving user preferences through the user memory tools.
---

# User Memory Preferences Skill

This skill defines how to safely read and save user preferences.

## Core rule

Always inspect the memory outline before loading specific memory values.

Call:

```text
user_memory_outline
```

before calling any preference retrieval tool.

## Reading preferences

Use this sequence:

1. Call `user_memory_outline`.
2. Identify the specific preference keys that are relevant to the current task.
3. Call `user_memory_get_preference` only for the specific keys needed.
4. Apply the retrieved preferences only when they are relevant to the user's current request.

Do not bulk-load unrelated preferences.

## Saving preferences

Use `user_memory_save_preference` only when the user explicitly asks to remember, save, record, or apply a preference in the future.

Examples of explicit save requests:

```text
Remember that I prefer concise answers.
Save this preference for next time.
Record that I like Markdown tables.
Apply this preference in future conversations.
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
