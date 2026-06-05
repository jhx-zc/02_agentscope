"""Project-local Ollama model fixes for AgentScope course demos."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from agentscope.message import TextBlock, ThinkingBlock, ToolCallBlock
from agentscope.model import ChatResponse, ChatUsage, OllamaChatModel


class PatchedOllamaChatModel(OllamaChatModel):
    """Ollama model with stable, reply-unique tool call ids.

    AgentScope's bundled Ollama adapter builds ids from ``idx`` and tool name,
    which collides when the same tool is called more than once in one reply.
    """

    async def _parse_stream_response(
        self,
        start_datetime: datetime,
        response: Any,
    ) -> AsyncGenerator[ChatResponse, None]:
        response_id = getattr(response, "id", None) or uuid.uuid4().hex
        acc_text = TextBlock(text="")
        acc_thinking = ThinkingBlock(thinking="")
        acc_tool_calls: dict[str, dict[str, str]] = {}
        usage = None

        async for chunk in response:
            delta_content: list[TextBlock | ThinkingBlock | ToolCallBlock] = []
            msg = chunk.message

            chunk_thinking = getattr(msg, "thinking", None)
            if chunk_thinking:
                acc_thinking.thinking += chunk_thinking
                delta_content.append(
                    ThinkingBlock(id=acc_thinking.id, thinking=chunk_thinking),
                )

            if msg.content:
                acc_text.text += msg.content
                delta_content.append(
                    TextBlock(id=acc_text.id, text=msg.content),
                )

            for idx, tool_call in enumerate(msg.tool_calls or []):
                function = tool_call.function
                tool_id = f"{response_id}_{idx}_{function.name}"
                input_str = json.dumps(function.arguments)
                acc_tool_calls[tool_id] = {
                    "name": function.name,
                    "input": input_str,
                }
                delta_content.append(
                    ToolCallBlock(
                        id=tool_id,
                        name=function.name,
                        input=input_str,
                    ),
                )

            current_time = (datetime.now() - start_datetime).total_seconds()
            usage = ChatUsage(
                input_tokens=getattr(chunk, "prompt_eval_count", 0) or 0,
                output_tokens=getattr(chunk, "eval_count", 0) or 0,
                time=current_time,
            )

            if delta_content:
                yield ChatResponse(
                    id=response_id,
                    content=delta_content,
                    is_last=False,
                    usage=usage,
                )

        final_content: list[TextBlock | ThinkingBlock | ToolCallBlock] = []
        if acc_thinking.thinking:
            final_content.append(acc_thinking)
        if acc_text.text:
            final_content.append(acc_text)
        for tool_id, tool_call in acc_tool_calls.items():
            final_content.append(
                ToolCallBlock(
                    id=tool_id,
                    name=tool_call["name"],
                    input=tool_call["input"],
                ),
            )

        yield ChatResponse(
            id=response_id,
            content=final_content,
            is_last=True,
            usage=usage,
        )

    async def _parse_completion_response(
        self,
        start_datetime: datetime,
        response: Any,
    ) -> ChatResponse:
        response_id = getattr(response, "id", None) or uuid.uuid4().hex
        content_blocks: list[TextBlock | ToolCallBlock | ThinkingBlock] = []

        message_thinking = getattr(response.message, "thinking", None)
        if message_thinking:
            content_blocks.append(ThinkingBlock(thinking=message_thinking))

        if response.message.content:
            content_blocks.append(TextBlock(text=response.message.content))

        for idx, tool_call in enumerate(response.message.tool_calls or []):
            content_blocks.append(
                ToolCallBlock(
                    id=f"{response_id}_{idx}_{tool_call.function.name}",
                    name=tool_call.function.name,
                    input=json.dumps(tool_call.function.arguments),
                ),
            )

        usage = None
        prompt_eval = getattr(response, "prompt_eval_count", None)
        eval_count = getattr(response, "eval_count", None)
        if prompt_eval is not None and eval_count is not None:
            usage = ChatUsage(
                input_tokens=prompt_eval,
                output_tokens=eval_count,
                time=(datetime.now() - start_datetime).total_seconds(),
            )

        return ChatResponse(
            id=response_id,
            content=content_blocks,
            is_last=True,
            usage=usage,
        )
