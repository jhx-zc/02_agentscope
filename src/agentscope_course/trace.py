"""Structured trace recording for AgentScope course runs."""

from __future__ import annotations

import contextvars
import difflib
import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1
DEFAULT_TRACE_DIR = Path(
    os.environ.get("AGENTSCOPE_TRACE_DIR", ".agentscope_traces"),
)
MAX_RECORDED_TEXT_CHARS = int(os.environ.get("AGENTSCOPE_TRACE_TEXT_CHARS", "20000"))
MAX_DIFF_CHARS = int(os.environ.get("AGENTSCOPE_TRACE_DIFF_CHARS", "30000"))

_CURRENT_RECORDER: contextvars.ContextVar[TraceRecorder | None] = (
    contextvars.ContextVar("agentscope_trace_recorder", default=None)
)


@dataclass
class FileSnapshot:
    """A before/after file state used to compute trace diffs."""

    path: Path
    exists: bool
    sha256: str | None
    size: int
    text: str | None


@dataclass
class ToolExecution:
    """In-flight tool execution state held by the wrapper."""

    execution_id: str
    tool_name: str
    args: dict[str, Any]
    tool_call_id: str | None
    before: dict[Path, FileSnapshot]


@dataclass
class PendingToolCall:
    """Tool call metadata assembled from AgentScope stream events."""

    tool_call_id: str
    tool_name: str
    reply_id: str | None
    args_text: str = ""
    matched: bool = False


def current_trace_recorder() -> TraceRecorder | None:
    """Return the recorder active in this async context, if any."""
    return _CURRENT_RECORDER.get()


@contextmanager
def trace_recorder_context(recorder: TraceRecorder | None) -> Iterator[None]:
    """Make a recorder visible to tool wrappers for one logical turn."""
    token = _CURRENT_RECORDER.set(recorder)
    try:
        yield
    finally:
        _CURRENT_RECORDER.reset(token)


class TraceRecorder:
    """Append structured run, turn, tool, and file-diff records."""

    def __init__(self, trace_dir: str | Path | None = None) -> None:
        self.run_id = uuid.uuid4().hex
        self._trace_dir = Path(trace_dir or DEFAULT_TRACE_DIR)
        self._started_at = _now()
        self._seq = 0
        self._turn_id: str | None = None
        self._turn_index = 0
        self._pending_tool_calls: list[PendingToolCall] = []
        self._assistant_parts: list[str] = []
        self._turn_file_changes: dict[Path, dict[str, Any]] = {}
        self._turns: list[dict[str, Any]] = []
        filename_prefix = f"{_stamp()}-{self.run_id[:8]}"
        self.jsonl_path = self._trace_dir / f"{filename_prefix}.jsonl"
        self.summary_path = self._trace_dir / f"{filename_prefix}.summary.json"
        self._write(
            "run_start",
            {
                "cwd": str(Path.cwd().resolve()),
                "jsonl_path": str(self.jsonl_path),
                "summary_path": str(self.summary_path),
            },
        )

    def start_turn(self, user_input: str) -> str:
        """Start a new user turn and return its trace id."""
        self._turn_index += 1
        self._turn_id = uuid.uuid4().hex
        self._pending_tool_calls = []
        self._assistant_parts = []
        self._turn_file_changes = {}
        self._write(
            "turn_start",
            {
                "turn_index": self._turn_index,
                "user_input": user_input,
            },
        )
        return self._turn_id

    def end_turn(self) -> None:
        """Finish the active turn and write a compact turn summary."""
        if self._turn_id is None:
            return

        assistant_text = "".join(self._assistant_parts)
        pending = [
            {
                "tool_call_id": call.tool_call_id,
                "tool_name": call.tool_name,
                "matched": call.matched,
            }
            for call in self._pending_tool_calls
            if not call.matched
        ]
        turn_summary = {
            "turn_id": self._turn_id,
            "turn_index": self._turn_index,
            "assistant_text": _limit_text(assistant_text),
            "assistant_text_len": len(assistant_text),
            "file_changes": list(self._turn_file_changes.values()),
            "unmatched_tool_calls": pending,
        }
        self._turns.append(turn_summary)
        self._write("turn_end", turn_summary)
        self._turn_id = None

    def close(self) -> None:
        """Write run end and summary records."""
        if self._turn_id is not None:
            self.end_turn()

        summary = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "started_at": self._started_at,
            "ended_at": _now(),
            "jsonl_path": str(self.jsonl_path),
            "turn_count": len(self._turns),
            "turns": self._turns,
        }
        self._write("run_end", {"turn_count": len(self._turns)})
        self._write_json(self.summary_path, summary)

    def record_agent_event(self, event_class: str, fields: dict[str, Any]) -> None:
        """Record a renderer-observed AgentScope event."""
        self._write(
            "agent_event",
            {
                "event_class": event_class,
                **_jsonable(fields),
            },
        )

    def record_text_delta(self, delta: str | None) -> None:
        """Collect assistant text while keeping the event stream compact."""
        if not delta:
            return
        self._assistant_parts.append(delta)
        self._write(
            "assistant_text_delta",
            {
                "delta": _limit_text(delta),
                "delta_len": len(delta),
            },
        )

    def record_tool_call_start(
        self,
        *,
        reply_id: str | None,
        tool_call_id: str,
        tool_name: str,
    ) -> None:
        """Register an AgentScope tool call before execution."""
        self._pending_tool_calls.append(
            PendingToolCall(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                reply_id=reply_id,
            ),
        )
        self._write(
            "tool_call_start",
            {
                "reply_id": reply_id,
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
            },
        )

    def record_tool_call_args_delta(self, tool_call_id: str, delta: str | None) -> None:
        """Append streamed tool arguments to the matching pending call."""
        if not delta:
            return
        call = self._find_pending_by_id(tool_call_id)
        if call is not None:
            call.args_text += delta

    def record_tool_call_ready(self, tool_call_id: str) -> None:
        """Record that AgentScope finished streaming a tool call request."""
        call = self._find_pending_by_id(tool_call_id)
        self._write(
            "tool_call_ready",
            {
                "tool_call_id": tool_call_id,
                "tool_name": call.tool_name if call else None,
                "args": _parse_args(call.args_text) if call else None,
                "args_text": _limit_text(call.args_text) if call else "",
            },
        )

    def record_confirmation_request(self, reply_id: str | None, tool_calls: list[Any]) -> None:
        """Record tool calls that require user confirmation."""
        calls = []
        for tool_call in tool_calls:
            tool_call_id = getattr(tool_call, "id", None)
            tool_name = getattr(tool_call, "name", None)
            tool_input = getattr(tool_call, "input", None) or ""
            if tool_call_id and tool_name:
                call = self._find_pending_by_id(tool_call_id)
                if call is None:
                    self._pending_tool_calls.append(
                        PendingToolCall(
                            tool_call_id=tool_call_id,
                            tool_name=tool_name,
                            reply_id=reply_id,
                            args_text=tool_input,
                        ),
                    )
                elif tool_input and not call.args_text:
                    call.args_text = tool_input
            calls.append(
                {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "args": _parse_args(tool_input),
                    "args_text": _limit_text(tool_input),
                },
            )
        self._write(
            "confirmation_request",
            {
                "reply_id": reply_id,
                "tool_calls": calls,
                "tool_call_count": len(calls),
            },
        )

    def record_local_event(self, name: str, fields: dict[str, Any]) -> None:
        """Record local renderer/conversation events."""
        self._write(name, _jsonable(fields))

    def begin_tool_execution(self, tool_name: str, args: dict[str, Any]) -> ToolExecution:
        """Record tool execution start and capture before snapshots."""
        tool_call_id = self._match_tool_call(tool_name, args)
        paths = _candidate_paths(tool_name, args=args, result=None)
        before = {path: _snapshot(path) for path in paths}
        execution = ToolExecution(
            execution_id=uuid.uuid4().hex,
            tool_name=tool_name,
            args=args,
            tool_call_id=tool_call_id,
            before=before,
        )
        self._write(
            "tool_execution_start",
            {
                "execution_id": execution.execution_id,
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "args": _jsonable(args),
                "candidate_paths": [str(path) for path in paths],
            },
        )
        return execution

    def end_tool_execution(
        self,
        execution: ToolExecution,
        *,
        status: str,
        result: Any = None,
        error: BaseException | None = None,
    ) -> None:
        """Record tool execution end, including file diffs."""
        paths = set(execution.before)
        paths.update(_candidate_paths(execution.tool_name, args=execution.args, result=result))
        before = dict(execution.before)
        for path in paths:
            before.setdefault(path, _snapshot(path, force_missing=True))

        file_changes = []
        for path in sorted(paths, key=lambda item: str(item)):
            change = _diff_snapshots(before[path], _snapshot(path))
            if change["change_type"] != "unchanged":
                file_changes.append(change)
                self._turn_file_changes[path] = change

        payload: dict[str, Any] = {
            "execution_id": execution.execution_id,
            "tool_call_id": execution.tool_call_id,
            "tool_name": execution.tool_name,
            "status": status,
            "result": _jsonable(result),
            "file_changes": file_changes,
            "file_change_count": len(file_changes),
        }
        if error is not None:
            payload["error"] = {
                "type": error.__class__.__name__,
                "message": str(error),
            }
        self._write("tool_execution_end", payload)

    def _match_tool_call(self, tool_name: str, args: dict[str, Any]) -> str | None:
        canonical_args = _canonical(args)
        fallback: PendingToolCall | None = None
        for call in self._pending_tool_calls:
            if call.matched or call.tool_name != tool_name:
                continue
            if fallback is None:
                fallback = call
            parsed = _parse_args(call.args_text)
            if isinstance(parsed, dict) and _canonical(parsed) == canonical_args:
                call.matched = True
                return call.tool_call_id
        if fallback is not None:
            fallback.matched = True
            return fallback.tool_call_id
        return None

    def _find_pending_by_id(self, tool_call_id: str) -> PendingToolCall | None:
        for call in self._pending_tool_calls:
            if call.tool_call_id == tool_call_id:
                return call
        return None

    def _write(self, event: str, fields: dict[str, Any]) -> None:
        self._seq += 1
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "turn_id": self._turn_id,
            "seq": self._seq,
            "ts": _now(),
            "event": event,
            **_jsonable(fields),
        }
        self._write_jsonl(self.jsonl_path, payload)

    def _write_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=False, default=str))
            file.write("\n")

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )


def _candidate_paths(
    tool_name: str,
    *,
    args: dict[str, Any],
    result: Any,
) -> set[Path]:
    paths: set[Path] = set()
    _add_path(paths, args.get("path"))
    if isinstance(result, dict):
        _add_path(paths, result.get("path"))

    if tool_name in {
        "user_memory_save_preference",
        "user_memory_delete_preference",
        "user_memory_clear_preferences",
    }:
        paths.add(Path.cwd().resolve() / ".agentscope_memory" / "user_preferences.json")
    return paths


def _add_path(paths: set[Path], value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        return
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    paths.add(path.resolve())


def _snapshot(path: Path, *, force_missing: bool = False) -> FileSnapshot:
    if force_missing or not path.exists():
        return FileSnapshot(
            path=path,
            exists=False,
            sha256=None,
            size=0,
            text=None,
        )
    if not path.is_file():
        return FileSnapshot(
            path=path,
            exists=True,
            sha256=None,
            size=0,
            text=None,
        )
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    return FileSnapshot(
        path=path,
        exists=True,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        text=text,
    )


def _diff_snapshots(before: FileSnapshot, after: FileSnapshot) -> dict[str, Any]:
    if not before.exists and after.exists:
        change_type = "created"
    elif before.exists and not after.exists:
        change_type = "deleted"
    elif before.sha256 != after.sha256:
        change_type = "modified"
    else:
        change_type = "unchanged"

    diff = ""
    diff_truncated = False
    if change_type != "unchanged" and before.text is not None and after.text is not None:
        diff = "".join(
            difflib.unified_diff(
                before.text.splitlines(keepends=True),
                after.text.splitlines(keepends=True),
                fromfile=f"a/{_relative_path(before.path)}",
                tofile=f"b/{_relative_path(after.path)}",
            ),
        )
        if len(diff) > MAX_DIFF_CHARS:
            diff = diff[:MAX_DIFF_CHARS]
            diff_truncated = True

    return {
        "path": str(after.path),
        "relative_path": _relative_path(after.path),
        "change_type": change_type,
        "before_sha256": before.sha256,
        "after_sha256": after.sha256,
        "before_size": before.size,
        "after_size": after.size,
        "line_delta": _line_count(after.text) - _line_count(before.text),
        "unified_diff": diff,
        "diff_truncated": diff_truncated,
    }


def _line_count(text: str | None) -> int:
    if text is None:
        return 0
    return len(text.splitlines())


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)


def _parse_args(args_text: str | None) -> Any:
    if not args_text:
        return None
    try:
        return json.loads(args_text)
    except json.JSONDecodeError:
        return args_text


def _canonical(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, default=str)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _jsonable(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str):
        return _limit_text(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    return _limit_text(str(value))


def _limit_text(text: str) -> str:
    if len(text) <= MAX_RECORDED_TEXT_CHARS:
        return text
    return f"{text[:MAX_RECORDED_TEXT_CHARS]}...[truncated {len(text) - MAX_RECORDED_TEXT_CHARS} chars]"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
