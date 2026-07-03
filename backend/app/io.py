"""WebSocket IO channels for the vendored bidi agent harness.

Implements the vendored ``BidiInput``/``BidiOutput`` protocols
(strands-py ``strands.experimental.bidi.types.io``) so a browser WebSocket
plugs straight into ``BidiAgent.run()`` — the harness's own loop drives
input reading, event fan-out, task-group supervision, and ``stop_all``
cleanup. We do not hand-roll a bridge around ``send``/``receive``.
"""

import base64
import json
from typing import Any

from fastapi import WebSocket

from app import _vendor  # noqa: F401  (vendored bidi must shadow pip copy)
from strands.experimental.bidi.types.events import (
    BidiAudioInputEvent,
    BidiImageInputEvent,
    BidiInputEvent,
    BidiOutputEvent,
    BidiTextInputEvent,
)


def _sanitize(value: Any) -> Any:
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item) for item in value]
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


class BidiWebSocketInput:
    """BidiInput protocol: reads browser frames, yields vendored TypedEvents."""

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def start(self, agent: Any) -> None:  # noqa: ANN401 (protocol signature)
        return

    async def stop(self) -> None:
        return

    async def __call__(self) -> BidiInputEvent:
        while True:
            raw = await self._websocket.receive_text()
            data = json.loads(raw)
            if not isinstance(data, dict):
                continue
            event_type = data.pop("type", None)
            if event_type == "bidi_text_input":
                return BidiTextInputEvent(**data)
            if event_type == "bidi_audio_input":
                return BidiAudioInputEvent(**data)
            if event_type == "bidi_image_input":
                return BidiImageInputEvent(**data)


class BidiWebSocketOutput:
    """BidiOutput protocol: forwards every agent event to the browser as JSON.

    Enriches ``tool_result`` events with ``tool_name``/``tool_input`` (from the
    matching ``tool_use_stream``) and flattens ``bidi_usage`` token fields —
    the exact contract the frontend's useLiveAgent hook consumes.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket
        self._tool_uses: dict[str, dict[str, Any]] = {}

    async def start(self, agent: Any) -> None:  # noqa: ANN401 (protocol signature)
        return

    async def stop(self) -> None:
        return

    async def __call__(self, event: BidiOutputEvent) -> None:
        outgoing = _sanitize(dict(event))

        if outgoing.get("type") == "tool_use_stream":
            current = outgoing.get("current_tool_use") or {}
            if isinstance(current, dict) and current.get("toolUseId"):
                self._tool_uses[str(current["toolUseId"])] = {
                    "name": current.get("name"),
                    "input": current.get("input", {}),
                }

        if outgoing.get("type") == "tool_result":
            result = outgoing.get("tool_result") or {}
            tool_use_id = result.get("toolUseId") if isinstance(result, dict) else None
            prior = self._tool_uses.get(str(tool_use_id), {}) if tool_use_id else {}
            outgoing["tool_name"] = prior.get("name", "")
            outgoing["tool_input"] = prior.get("input", {})

        if outgoing.get("type") == "bidi_usage":
            outgoing["input_tokens"] = outgoing.get("input_tokens", outgoing.get("inputTokens", 0))
            outgoing["output_tokens"] = outgoing.get("output_tokens", outgoing.get("outputTokens", 0))
            outgoing["total_tokens"] = outgoing.get("total_tokens", outgoing.get("totalTokens", 0))

        await self._websocket.send_text(json.dumps(outgoing, default=str))
