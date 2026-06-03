"""Console rendering helpers for AgentScope course agents."""

from __future__ import annotations

from typing import Any

from agentscope.event import (
    TextBlockDeltaEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultDataDeltaEvent,
    ToolResultEndEvent,
    ToolResultStartEvent,
    ToolResultTextDeltaEvent,
)


class StreamConsoleRenderer:
    """Render AgentScope stream events without breaking text deltas."""

    def __init__(self) -> None:
        self._has_output = False
        self._needs_assistant_label = True
        self._line_open = False
        self._tool_args_open = False
        self._tool_output_open = False
        self._tool_output_line_start = True

    def render(self, event: Any) -> None:
        """Print one stream event in a compact, Codex-like transcript."""
        if isinstance(event, TextBlockDeltaEvent):
            self._render_text(event.delta)
        elif isinstance(event, ToolCallStartEvent):
            self._render_tool_start(event.tool_call_name)
        elif isinstance(event, ToolCallDeltaEvent):
            self._render_tool_args(event.delta)
        elif isinstance(event, ToolCallEndEvent):
            self._finish_open_line()
        elif isinstance(event, ToolResultStartEvent):
            self._finish_open_line()
            print("   status: running")
        elif isinstance(event, ToolResultTextDeltaEvent):
            self._render_tool_output(event.delta)
        elif isinstance(event, ToolResultDataDeltaEvent):
            self._render_tool_data(event)
        elif isinstance(event, ToolResultEndEvent):
            self._finish_open_line()
            state = getattr(event.state, "value", event.state)
            print(f"   result: {state}")
            self._needs_assistant_label = True

    def finish(self) -> None:
        """End the current response cleanly before the next prompt."""
        self._finish_open_line()

    def _render_text(self, delta: str | None) -> None:
        if not delta:
            return
        if self._needs_assistant_label:
            if self._has_output:
                print()
            print("🤖 Assistant: ", end="", flush=True)
            self._needs_assistant_label = False
            self._has_output = True
        print(delta, end="", flush=True)
        self._line_open = not delta.endswith("\n")

    def _render_tool_start(self, tool_name: str) -> None:
        self._separate_block()
        print(f"🔧 Tool: {tool_name}")
        print("   args: ", end="", flush=True)
        self._has_output = True
        self._line_open = True
        self._tool_args_open = True

    def _render_tool_args(self, delta: str | None) -> None:
        if not delta:
            return
        if not self._tool_args_open:
            print("   args: ", end="", flush=True)
            self._tool_args_open = True
        print(delta, end="", flush=True)
        self._line_open = not delta.endswith("\n")

    def _render_tool_output(self, delta: str | None) -> None:
        if not delta:
            return
        if not self._tool_output_open:
            self._finish_open_line()
            self._tool_output_open = True
            self._tool_output_line_start = True
        self._write_tool_output(delta)
        self._line_open = not delta.endswith("\n")

    def _render_tool_data(self, event: ToolResultDataDeltaEvent) -> None:
        self._finish_open_line()
        location = event.url or ""
        if not location and event.data:
            location = event.data[:120]
            if len(event.data) > 120:
                location += "..."
        suffix = f" {location}" if location else ""
        print(f"   data: {event.media_type}{suffix}")

    def _separate_block(self) -> None:
        self._finish_open_line()
        if self._has_output:
            print()

    def _finish_open_line(self) -> None:
        if self._line_open:
            print()
        self._line_open = False
        self._tool_args_open = False
        self._tool_output_open = False
        self._tool_output_line_start = True

    def _write_tool_output(self, delta: str) -> None:
        for part in delta.splitlines(keepends=True):
            if self._tool_output_line_start:
                print("   output: ", end="", flush=True)
            print(part, end="", flush=True)
            self._tool_output_line_start = part.endswith("\n")
