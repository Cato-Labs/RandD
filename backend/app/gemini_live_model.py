"""Vantage's Gemini Live model.

Subclasses the published ``strands-agents`` BidiGeminiLiveModel rather than
vendoring a fork of it, so upstream fixes arrive with a version bump.

Three deltas are carried here because upstream (1.50.2) does not have them:

1. ``model_id`` defaults to ``gemini-3.1-flash-live-preview``.

2. Camera frames go through the realtime *video* channel
   (``send_realtime_input(video=Blob)``) instead of ``send(input=...)``.
   The inspector's camera is a live video source, and the realtime channel is
   the one Gemini expects for it.

3. Tool results are sent with the real tool *name*. Upstream sets
   ``name=tool_use_id`` ("Gemini uses name as identifier"), which puts the call
   ID where the function name belongs. We record the id -> name mapping when the
   tool call is parsed and use it when replying.

Everything else — history seeding, session resumption, audio, transcription —
is inherited unchanged.
"""

import base64
import logging
from typing import Any, cast

from google.genai import types as genai_types
from google.genai.types import LiveServerMessage
from strands.experimental.bidi.models.gemini_live import BidiGeminiLiveModel
from strands.experimental.bidi.types.events import BidiImageInputEvent, BidiOutputEvent
from strands.types.tools import ToolResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL_ID = "gemini-3.1-flash-live-preview"


class VantageGeminiLiveModel(BidiGeminiLiveModel):
    """Gemini Live with Vantage's camera and tool-result handling."""

    def __init__(self, model_id: str = DEFAULT_MODEL_ID, **kwargs: Any) -> None:
        """Initialize with the Vantage model default."""
        super().__init__(model_id=model_id, **kwargs)
        self._tool_names_by_id: dict[str, str] = {}

    def _convert_gemini_live_event(self, message: LiveServerMessage) -> list[BidiOutputEvent]:
        """Record tool-call id -> name before the event is converted."""
        if message.tool_call and message.tool_call.function_calls:
            for func_call in message.tool_call.function_calls:
                if func_call.id and func_call.name:
                    self._tool_names_by_id[func_call.id] = func_call.name
        return super()._convert_gemini_live_event(message)

    async def _send_image_content(self, image_input: BidiImageInputEvent) -> None:
        """Send camera frames through the realtime video input channel."""
        image_blob = genai_types.Blob(
            data=base64.b64decode(image_input.image),
            mime_type=image_input.mime_type,
        )
        await self._live_session.send_realtime_input(video=image_blob)

    async def _send_tool_result(self, tool_result: ToolResult) -> None:
        """Send a tool result using the tool's real name, not its id."""
        tool_use_id = cast(str, tool_result.get("toolUseId"))
        content = tool_result.get("content", [])

        for block in content:
            if "text" not in block and "json" not in block:
                raise ValueError(
                    f"tool_use_id=<{tool_use_id}>, content_types=<{list(block.keys())}> | "
                    f"Content type not supported by Gemini Live API"
                )

        if len(content) == 1:
            result_data = cast(dict[str, Any], content[0])
        else:
            result_data = {"result": content}

        tool_name = self._tool_names_by_id.pop(tool_use_id, tool_use_id)
        func_response = genai_types.FunctionResponse(
            id=tool_use_id,
            name=tool_name,
            response=result_data,
        )
        await self._live_session.send_tool_response(function_responses=[func_response])
