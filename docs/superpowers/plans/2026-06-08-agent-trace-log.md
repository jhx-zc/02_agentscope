# Agent Trace Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a structured trace log that links AgentScope stream events, tool execution, permissions, and file diffs for evaluation.

**Architecture:** Add `TraceRecorder` as a lightweight sidecar to the existing renderer and tool wrapper. Use `contextvars` so the tool wrapper can record execution while `reply_until_done` keeps the current turn active.

**Tech Stack:** Python standard library (`contextvars`, `dataclasses`, `difflib`, `hashlib`, `json`, `pathlib`), existing AgentScope/Rich stack.

---

### Task 1: Trace Recorder

**Files:**
- Create: `src/agentscope_course/trace.py`

- [ ] **Step 1: Create recorder types and JSONL writer**

Create `TraceRecorder`, `TraceContext`, file snapshot helpers, and append-only JSONL writing.

- [ ] **Step 2: Add turn lifecycle and summary writing**

Support `start_turn`, `end_turn`, `close`, and `set_current_recorder` context manager helpers.

- [ ] **Step 3: Add tool call and file diff helpers**

Support pending tool call registration, execution matching, candidate path detection, before/after snapshots, and unified diff generation.

### Task 2: Renderer and Conversation Wiring

**Files:**
- Modify: `src/agentscope_course/console.py`
- Modify: `src/agentscope_course/conversation.py`
- Modify: `src/agentscope_course/agent.py`

- [ ] **Step 1: Accept optional recorder in `StreamConsoleRenderer`**

Keep existing behavior unchanged when no recorder is provided.

- [ ] **Step 2: Record stream events and local decisions**

Forward important event metadata, permission decisions, confirmation responses, and unresolved tool calls to the recorder.

- [ ] **Step 3: Start and end trace turns in `ask_agent`**

Create one recorder per interactive run, start a turn per user input, set the context recorder during `reply_until_done`, and close the run on exit.

### Task 3: Tool Wrapper Execution Trace

**Files:**
- Modify: `src/agentscope_tools/agentscope_wrapper.py`

- [ ] **Step 1: Wrap tool execution with trace hooks**

Before calling the original function, ask the current recorder to start tool execution and capture before snapshots.

- [ ] **Step 2: Record successful tool results**

After successful execution, record the result and after snapshots with file diffs.

- [ ] **Step 3: Record tool errors**

On exception, record the error and any file changes observed before re-raising.

### Task 4: Verification

**Files:**
- Inspect: `src/agentscope_course/trace.py`
- Inspect: `src/agentscope_course/console.py`
- Inspect: `src/agentscope_course/agent.py`
- Inspect: `src/agentscope_tools/agentscope_wrapper.py`

- [ ] **Step 1: Compile the changed source**

Run: `uv run python -m compileall -q src`

- [ ] **Step 2: Import the main modules**

Run: `uv run python -c "from agentscope_course.trace import TraceRecorder; from agentscope_course.agent import create_agent; print('trace imports ok')"`

- [ ] **Step 3: Review git diff**

Run: `git diff -- docs/superpowers src`

