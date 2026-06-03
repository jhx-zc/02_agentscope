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

_MAX_TOOL_OUTPUT_LINES = 24
_MAX_TOOL_OUTPUT_CHARS = 4_000


class StreamConsoleRenderer:
    """Render AgentScope stream events without breaking text deltas."""

    def __init__(self) -> None:
        self._has_output = False
        self._needs_assistant_label = True
        self._line_open = False
        self._tool_args_open = False
        self._tool_output_parts: list[str] = []

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
            self._collect_tool_output(event.delta)
        elif isinstance(event, ToolResultDataDeltaEvent):
            self._render_tool_data(event)
        elif isinstance(event, ToolResultEndEvent):
            self._flush_tool_output()
            self._finish_open_line()
            state = getattr(event.state, "value", event.state)
            print(f"   result: {state}")
            self._needs_assistant_label = True

    def finish(self) -> None:
        """End the current response cleanly before the next prompt."""
        self._flush_tool_output()
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

    def _collect_tool_output(self, delta: str | None) -> None:
        if not delta:
            return
        self._tool_output_parts.append(delta)

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

    def _flush_tool_output(self) -> None:
        if not self._tool_output_parts:
            return

        text = "".join(self._tool_output_parts)
        self._tool_output_parts.clear()
        preview, omitted_lines, omitted_chars = self._tool_output_preview(text)

        self._finish_open_line()
        print("   output:")
        for line in preview:
            print(f"      {line}")
        if omitted_lines or omitted_chars:
            details = []
            if omitted_lines:
                details.append(f"{omitted_lines} lines")
            if omitted_chars:
                details.append(f"{omitted_chars} chars")
            print(f"      ... omitted {', '.join(details)} from console preview")

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
