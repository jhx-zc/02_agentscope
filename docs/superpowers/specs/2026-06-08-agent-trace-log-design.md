# Agent Trace Log Design

## Goal

Build a LangGraph-like trace log for the AgentScope course agent so each user turn can be evaluated by both process and outcome: which tools ran, what they returned, what permissions were applied, and what files changed.

## Architecture

The existing console renderer stays responsible for streaming terminal output and the existing `agentscope_events.jsonl` remains a low-level event log. A new `TraceRecorder` writes higher-level structured records to `.agentscope_traces/`, with one JSONL stream per interactive run and one summary JSON per run.

The trace has two capture points:

- `StreamConsoleRenderer` records AgentScope stream events, tool call metadata, permission decisions, unresolved calls, and turn boundaries.
- `agentscope_wrapper._wrap_tool_result` records real tool execution, return values, exceptions, and file changes before and after each tool call.

The tool wrapper cannot receive AgentScope `tool_call_id` directly, so trace correlation uses a context-local recorder plus pending tool calls captured by the renderer. Matching is by tool name first and canonicalized arguments when available.

## Data Model

Each trace record includes:

- `schema_version`
- `run_id`
- `turn_id`
- `seq`
- `ts`
- `event`

Tool execution records also include:

- `tool_call_id`
- `tool_name`
- `args`
- `status`
- `result` or `error`
- `file_changes`

File change records include:

- `path`
- `relative_path`
- `change_type`
- `before_sha256`
- `after_sha256`
- `before_size`
- `after_size`
- `line_delta`
- `unified_diff`
- `diff_truncated`

## Trace Files

Default output directory:

```text
.agentscope_traces/
```

Per run outputs:

```text
<timestamp>-<run_id>.jsonl
<timestamp>-<run_id>.summary.json
```

The JSONL file is the authoritative stream for evaluation. The summary JSON gives a compact run-level view for quick inspection.

## File Change Capture

Candidate affected files are detected from:

- `path` arguments passed to Markdown tools.
- `path` fields returned by tools.
- Memory write tools, which affect `.agentscope_memory/user_preferences.json`.

Each candidate path is snapshotted before and after execution. Diffs are generated with Python's `difflib.unified_diff`, avoiding a dependency on git or shell commands.

## Scope

First version includes:

- JSONL trace recorder.
- Run and turn lifecycle records.
- Tool call metadata and permission decisions.
- Tool execution records with result/error.
- Per-tool file diffs.
- Run summary JSON.

First version excludes:

- Visual UI.
- LangSmith/OpenTelemetry export.
- Test code, because this course project explicitly does not require tests.

