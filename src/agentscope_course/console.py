"""Console rendering helpers for AgentScope course agents."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentscope.event import (
    RequireUserConfirmEvent,
    TextBlockDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultDataDeltaEvent,
    ToolResultEndEvent,
    ToolResultStartEvent,
    ToolResultTextDeltaEvent,
)
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

_MAX_TOOL_OUTPUT_LINES = 24
_MAX_TOOL_OUTPUT_CHARS = 4_000
_EVENT_LOG_PATH = Path(
    os.environ.get("AGENTSCOPE_EVENT_LOG", "agentscope_events.jsonl"),
)
_EVENT_LOG_PREVIEW_CHARS = 1_000


@dataclass
class _ToolRenderState:
    """Console-facing state for one AgentScope tool call."""

    id: str
    name: str
    reply_id: str
    index: int
    args_parts: list[str] = field(default_factory=list)
    permission: str | None = None
    status: str = "collecting args"
    result: str | None = None
    output_parts: list[str] = field(default_factory=list)
    data_lines: list[str] = field(default_factory=list)
    call_done: bool = False
    requires_confirmation: bool = False

    @property
    def args(self) -> str:
        return "".join(self.args_parts).strip()

    @property
    def output(self) -> str:
        return "".join(self.output_parts)

    @property
    def done(self) -> bool:
        return self.result is not None

    @property
    def unresolved(self) -> bool:
        return self.call_done and self.result is None


@dataclass
class _ToolBatchState:
    """A group of tool calls emitted by the same AgentScope reply."""

    number: int
    reply_id: str
    tools: dict[str, _ToolRenderState] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)

    def get_or_create(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
    ) -> _ToolRenderState:
        if tool_call_id not in self.tools:
            self.order.append(tool_call_id)
            self.tools[tool_call_id] = _ToolRenderState(
                id=tool_call_id,
                name=tool_name,
                reply_id=self.reply_id,
                index=len(self.order),
            )
        elif tool_name and self.tools[tool_call_id].name in {"", "unknown"}:
            self.tools[tool_call_id].name = tool_name
        return self.tools[tool_call_id]

    @property
    def done(self) -> bool:
        return bool(self.tools) and all(
            self.tools[tool_id].done for tool_id in self.order
        )


class StreamConsoleRenderer:
    """Render AgentScope stream events without breaking text deltas."""

    def __init__(self) -> None:
        self._console = Console()
        self._has_output = False
        self._needs_assistant_label = True
        self._line_open = False
        self._batch_number = 0
        self._event_sequence = 0
        self._renderer_id = uuid.uuid4().hex
        self._event_log_path = _EVENT_LOG_PATH
        self._event_log_failed = False
        self._active_batch: _ToolBatchState | None = None
        self._live: Live | None = None

    def render(self, event: Any) -> None:
        """Print one stream event in a compact, Codex-like transcript."""
        self._log_agent_event(event)
        if isinstance(event, TextBlockDeltaEvent):
            self._render_text(event.delta)
        elif isinstance(event, ToolCallStartEvent):
            self._render_tool_start(event)
        elif isinstance(event, ToolCallDeltaEvent):
            self._render_tool_args(event)
        elif isinstance(event, ToolCallEndEvent):
            self._render_tool_call_end(event)
        elif isinstance(event, RequireUserConfirmEvent):
            self._render_tool_confirmation_request(event)
        elif isinstance(event, ToolResultStartEvent):
            self._render_tool_result_start(event)
        elif isinstance(event, ToolResultTextDeltaEvent):
            self._collect_tool_output(event)
        elif isinstance(event, ToolResultDataDeltaEvent):
            self._render_tool_data(event)
        elif isinstance(event, ToolResultEndEvent):
            self._render_tool_result_end(event)

    def record_tool_permission(
        self,
        tool_call_id: str,
        permission: str,
        *,
        confirmed: bool,
    ) -> None:
        """Attach permission information to the matching live tool block."""
        self._log_local_event(
            "permission_decision",
            {
                "tool_call_id": tool_call_id,
                "permission": permission,
                "confirmed": confirmed,
            },
        )
        tool = self._find_tool(tool_call_id)
        if tool is None:
            return
        tool.permission = permission
        tool.status = "approved" if confirmed else "denied"
        if not confirmed:
            tool.result = "denied"
        self._refresh_live()

    def record_confirmation_response(
        self,
        reply_id: str,
        confirm_results: list[Any],
    ) -> None:
        """Log the confirmation event sent back to AgentScope."""
        self._log_local_event(
            "user_confirm_result",
            {
                "reply_id": reply_id,
                "confirm_results": [
                    {
                        "tool_call_id": result.tool_call.id,
                        "tool_call_name": result.tool_call.name,
                        "confirmed": result.confirmed,
                        "input_len": len(result.tool_call.input or ""),
                        "input": self._preview(result.tool_call.input),
                    }
                    for result in confirm_results
                ],
                "confirm_result_count": len(confirm_results),
            },
        )

    def pause_live(self) -> None:
        """Temporarily stop live rendering before blocking terminal input."""
        if self._live is None:
            return
        self._live.update(self._render_active_batch(), refresh=True)
        self._live.stop()
        self._live = None

    def finish(self) -> None:
        """End the current response cleanly before the next prompt."""
        self._stop_live()
        self._finish_open_line()

    def close_turn(self) -> None:
        """Finalize any tool calls that did not reach execution this turn."""
        batch = self._active_batch
        changed = False
        if batch is not None:
            for tool_id in batch.order:
                tool = batch.tools[tool_id]
                if tool.unresolved and not tool.requires_confirmation:
                    tool.status = "not executed this turn"
                    self._log_local_event(
                        "unresolved_tool_call",
                        {
                            "reply_id": tool.reply_id,
                            "tool_call_id": tool.id,
                            "tool_name": tool.name,
                            "status": tool.status,
                            "args": self._preview(tool.args),
                        },
                    )
                    changed = True
            if changed:
                self._refresh_live()
        self.finish()

    def _render_text(self, delta: str | None) -> None:
        if not delta:
            return
        self._stop_live()
        if self._needs_assistant_label:
            if self._has_output:
                self._console.print()
            self._console.print(
                "🤖 Assistant: ",
                end="",
                soft_wrap=True,
                markup=False,
            )
            self._needs_assistant_label = False
            self._has_output = True
        self._console.print(delta, end="", soft_wrap=True, markup=False)
        self._line_open = not delta.endswith("\n")

    def _render_tool_start(self, event: ToolCallStartEvent) -> None:
        tool = self._ensure_tool(
            reply_id=event.reply_id,
            tool_call_id=event.tool_call_id,
            tool_name=event.tool_call_name,
        )
        tool.status = "collecting args"
        self._refresh_live()
        self._has_output = True
        self._needs_assistant_label = True
        self._line_open = False

    def _render_tool_args(self, event: ToolCallDeltaEvent) -> None:
        if not event.delta:
            return
        tool = self._ensure_tool(
            reply_id=event.reply_id,
            tool_call_id=event.tool_call_id,
            tool_name="unknown",
        )
        tool.args_parts.append(event.delta)
        self._refresh_live()

    def _render_tool_call_end(self, event: ToolCallEndEvent) -> None:
        tool = self._ensure_tool(
            reply_id=event.reply_id,
            tool_call_id=event.tool_call_id,
            tool_name="unknown",
        )
        tool.call_done = True
        tool.status = "ready"
        self._refresh_live()

    def _render_tool_confirmation_request(
        self,
        event: RequireUserConfirmEvent,
    ) -> None:
        for tool_call in event.tool_calls:
            tool = self._ensure_tool(
                reply_id=event.reply_id,
                tool_call_id=tool_call.id,
                tool_name=tool_call.name,
            )
            if tool_call.input and not tool.args:
                tool.args_parts.append(tool_call.input)
            tool.requires_confirmation = True
            tool.status = "waiting approval"
            self._refresh_live()

    def _render_tool_result_start(self, event: ToolResultStartEvent) -> None:
        tool = self._ensure_tool(
            reply_id=event.reply_id,
            tool_call_id=event.tool_call_id,
            tool_name=event.tool_call_name,
        )
        tool.status = "running"
        self._refresh_live()

    def _collect_tool_output(self, event: ToolResultTextDeltaEvent) -> None:
        if not event.delta:
            return
        tool = self._ensure_tool(
            reply_id=event.reply_id,
            tool_call_id=event.tool_call_id,
            tool_name="unknown",
        )
        tool.output_parts.append(event.delta)
        self._refresh_live()

    def _render_tool_data(self, event: ToolResultDataDeltaEvent) -> None:
        tool = self._ensure_tool(
            reply_id=event.reply_id,
            tool_call_id=event.tool_call_id,
            tool_name="unknown",
        )
        location = event.url or ""
        if not location and event.data:
            location = event.data[:120]
            if len(event.data) > 120:
                location += "..."
        suffix = f" {location}" if location else ""
        tool.data_lines.append(f"{event.media_type}{suffix}")
        self._refresh_live()

    def _render_tool_result_end(self, event: ToolResultEndEvent) -> None:
        tool = self._ensure_tool(
            reply_id=event.reply_id,
            tool_call_id=event.tool_call_id,
            tool_name="unknown",
        )
        state = getattr(event.state, "value", event.state)
        tool.status = "finished"
        tool.result = str(state)
        self._refresh_live()
        # if self._active_batch and self._active_batch.done:
        #     self._stop_live()
        self._needs_assistant_label = True

    def _finish_open_line(self) -> None:
        if self._line_open:
            self._console.print()
        self._line_open = False

    def _log_agent_event(self, event: Any) -> None:
        if 'DELTA' in str(event.__class__.__name__).upper():
            return
        fields = self._event_fields(event)
        record = {
            "source": "agentscope",
            "event_class": event.__class__.__name__,
            **fields,
        }
        self._write_event_log(record)

    def _log_local_event(self, name: str, fields: dict[str, Any]) -> None:
        self._write_event_log(
            {
                "source": "local",
                "event_class": name,
                **fields,
            },
        )

    def _write_event_log(self, record: dict[str, Any]) -> None:
        if self._event_log_failed:
            return

        self._event_sequence += 1
        payload = {
            "seq": self._event_sequence,
            "renderer_id": self._renderer_id,
            "ts": datetime.now(UTC).isoformat(),
            **record,
        }
        try:
            self._event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._event_log_path.open("a", encoding="utf-8") as log_file:
                log_file.write(
                    json.dumps(payload, ensure_ascii=False, default=str),
                )
                log_file.write("\n")
        except OSError:
            self._event_log_failed = True

    def _event_fields(self, event: Any) -> dict[str, Any]:
        fields = {
            "event_type": self._value(getattr(event, "type", None)),
            "event_id": getattr(event, "id", None),
            "reply_id": getattr(event, "reply_id", None),
            "created_at": getattr(event, "created_at", None),
        }

        if isinstance(event, TextBlockDeltaEvent):
            fields.update(self._delta_fields(event.delta))
        elif isinstance(event, ToolCallStartEvent):
            fields.update(
                {
                    "tool_call_id": event.tool_call_id,
                    "tool_call_name": event.tool_call_name,
                },
            )
        elif isinstance(event, ToolCallDeltaEvent):
            fields.update(
                {
                    "tool_call_id": event.tool_call_id,
                    **self._delta_fields(event.delta),
                },
            )
        elif isinstance(event, ToolCallEndEvent):
            fields["tool_call_id"] = event.tool_call_id
        elif isinstance(event, RequireUserConfirmEvent):
            fields["tool_calls"] = [
                self._tool_call_fields(tool_call)
                for tool_call in event.tool_calls
            ]
            fields["tool_call_count"] = len(event.tool_calls)
        elif isinstance(event, ToolResultStartEvent):
            fields.update(
                {
                    "tool_call_id": event.tool_call_id,
                    "tool_call_name": event.tool_call_name,
                },
            )
        elif isinstance(event, ToolResultTextDeltaEvent):
            fields.update(
                {
                    "tool_call_id": event.tool_call_id,
                    **self._delta_fields(event.delta),
                },
            )
        elif isinstance(event, ToolResultDataDeltaEvent):
            fields.update(
                {
                    "tool_call_id": event.tool_call_id,
                    "block_id": event.block_id,
                    "media_type": event.media_type,
                    "data_len": len(event.data or ""),
                    "data": self._preview(event.data),
                    "url": event.url,
                },
            )
        elif isinstance(event, ToolResultEndEvent):
            fields.update(
                {
                    "tool_call_id": event.tool_call_id,
                    "state": self._value(event.state),
                },
            )

        return {key: value for key, value in fields.items() if value is not None}

    def _tool_call_fields(self, tool_call: Any) -> dict[str, Any]:
        tool_input = getattr(tool_call, "input", None)
        suggested_rules = getattr(tool_call, "suggested_rules", None) or []
        return {
            "id": getattr(tool_call, "id", None),
            "name": getattr(tool_call, "name", None),
            "input_len": len(tool_input or ""),
            "input": self._preview(tool_input),
            "state": self._value(getattr(tool_call, "state", None)),
            "suggested_rule_count": len(suggested_rules),
        }

    def _delta_fields(self, delta: str | None) -> dict[str, Any]:
        return {
            "delta_len": len(delta or ""),
            "delta": self._preview(delta),
        }

    def _preview(self, text: str | None) -> str:
        if not text:
            return ""
        if len(text) <= _EVENT_LOG_PREVIEW_CHARS:
            return text
        return f"{text[:_EVENT_LOG_PREVIEW_CHARS]}..."

    def _value(self, value: Any) -> Any:
        return getattr(value, "value", value)

    def _ensure_tool(
        self,
        *,
        reply_id: str,
        tool_call_id: str,
        tool_name: str,
    ) -> _ToolRenderState:
        if (
            self._active_batch is None
            or self._active_batch.reply_id != reply_id
            # or self._active_batch.done
        ):
            self._stop_live()
            self._batch_number += 1
            self._active_batch = _ToolBatchState(
                number=self._batch_number,
                reply_id=reply_id,
            )
        return self._active_batch.get_or_create(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
        )

    def _find_tool(self, tool_call_id: str) -> _ToolRenderState | None:
        if self._active_batch is None:
            return None
        return self._active_batch.tools.get(tool_call_id)

    def _start_live(self) -> None:
        if self._live is not None:
            return
        self._finish_open_line()
        if self._has_output:
            self._console.print()
        self._live = Live(
            self._render_active_batch(),
            console=self._console,
            refresh_per_second=8,
            transient=False,
            vertical_overflow="visible",
        )
        self._live.start(refresh=True)

    def _refresh_live(self) -> None:
        if self._active_batch is None:
            return
        self._start_live()
        if self._live is not None:
            self._live.update(self._render_active_batch(), refresh=True)

    def _stop_live(self) -> None:
        if self._live is None:
            return
        self._live.update(self._render_active_batch(), refresh=True)
        self._live.stop()
        self._live = None
        self._has_output = True

    def _render_active_batch(self) -> Panel:
        if self._active_batch is None:
            return Panel(Text("No active tools"), title="Tool batch")

        batch = self._active_batch
        count = len(batch.order)
        title = f"Tool batch #{batch.number} · {count} call"
        if count != 1:
            title += "s"

        tree = Tree(Text(f"🧰 {title}"))
        for pos, tool_id in enumerate(batch.order, start=1):
            tool = batch.tools[tool_id]
            branch = tree.add(
                Text(
                    f"🔧 [{pos}/{count}] {tool.name} · {self._short_id(tool.id)}",
                ),
            )
            branch.add(Text(f"args: {tool.args or '...'}"))
            if tool.permission:
                branch.add(Text(f"permission: {tool.permission}"))
            branch.add(Text(f"status: {tool.status}"))
            for data_line in tool.data_lines:
                branch.add(Text(f"data: {data_line}"))
            if tool.output_parts:
                output = branch.add(Text("output:"))
                preview, omitted_lines, omitted_chars = self._tool_output_preview(
                    tool.output,
                )
                for line in preview:
                    output.add(Text(f"   {line}"))
                if omitted_lines or omitted_chars:
                    output.add(
                        Text(
                            "   ... omitted "
                            f"{self._omission_text(omitted_lines, omitted_chars)} "
                            "from console preview",
                        ),
                    )
            if tool.result is not None:
                branch.add(Text(f"result: {tool.result}"))

        return Panel(tree, border_style="cyan")

    def _short_id(self, tool_call_id: str) -> str:
        if len(tool_call_id) <= 10:
            return tool_call_id
        return f"{tool_call_id[:6]}...{tool_call_id[-4:]}"

    def _omission_text(self, omitted_lines: int, omitted_chars: int) -> str:
        details = []
        if omitted_lines:
            details.append(f"{omitted_lines} lines")
        if omitted_chars:
            details.append(f"{omitted_chars} chars")
        return ", ".join(details)

    def _tool_output_preview(self, text: str) -> tuple[list[str], int, int]:
        lines = text.splitlines()
        total_chars = len(text)
        preview_text = text[:_MAX_TOOL_OUTPUT_CHARS]
        preview_lines = preview_text.splitlines()

        omitted_chars = max(0, total_chars - len(preview_text))
        omitted_lines = max(0, len(lines) - len(preview_lines))

        if len(preview_lines) > _MAX_TOOL_OUTPUT_LINES:
            omitted_lines += len(preview_lines) - _MAX_TOOL_OUTPUT_LINES
            preview_lines = preview_lines[:_MAX_TOOL_OUTPUT_LINES]

        return preview_lines or [""], omitted_lines, omitted_chars
