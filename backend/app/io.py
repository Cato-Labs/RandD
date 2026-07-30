"""WebSocket transport adapters for the published Strands BidiAgent.

Implements the documented ``BidiInput``/``BidiOutput`` protocols so a browser
WebSocket plugs straight into ``BidiAgent.run()`` — the SDK's loop drives
input reading, event fan-out, task-group supervision, and ``stop_all``
cleanup. We do not hand-roll a bridge around ``send``/``receive``.
"""

import asyncio
import base64
from io import BytesIO
import json
from pathlib import Path
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any

from fastapi import WebSocket

from app import browser_camera
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
    """BidiInput protocol: reads browser frames and yields native typed events."""

    def __init__(
        self,
        websocket: WebSocket,
        *,
        session_id: str,
        approval_resolver: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        browser_control_resolver: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self._websocket = websocket
        self._session_id = session_id
        self._approval_resolver = approval_resolver
        self._browser_control_resolver = browser_control_resolver

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
            if event_type == "user_message":
                text = str(data.get("text") or "").strip()
                if text:
                    return BidiTextInputEvent(text=text)
                continue
            if event_type == "approval_resolved":
                if self._approval_resolver is not None:
                    await self._approval_resolver(data)
                continue
            if event_type == "browser_control":
                if self._browser_control_resolver is not None:
                    await self._browser_control_resolver(data)
                continue
            if event_type == "camera_capture":
                encoded = data.get("dataUrl")
                if not isinstance(encoded, str) or not encoded:
                    continue
                mime_type = str(data.get("mimeType") or "image/jpeg")
                if encoded.startswith("data:") and "," in encoded:
                    header, encoded = encoded.split(",", 1)
                    if ";base64" in header:
                        mime_type = header[5:].split(";", 1)[0] or mime_type
                browser_camera.add_frame(self._session_id, encoded)
                return BidiImageInputEvent(image=encoded, mime_type=mime_type)
            if event_type == "bidi_text_input":
                return BidiTextInputEvent(**data)
            if event_type == "bidi_audio_input":
                return BidiAudioInputEvent(**data)
            if event_type == "bidi_image_input":
                # Tee the frame so capture tools (take_photo/take_video) can
                # grab the device camera's view server-side.
                if isinstance(data.get("image"), str):
                    browser_camera.add_frame(self._session_id, data["image"])
                return BidiImageInputEvent(**data)


class BidiWebSocketOutput:
    """BidiOutput protocol: forwards every agent event to the browser as JSON.

    Enriches ``tool_result`` events with ``tool_name``/``tool_input`` (from the
    matching ``tool_use_stream``) and flattens ``bidi_usage`` token fields —
    the exact contract the frontend's useLiveAgent hook consumes.
    """

    def __init__(self, websocket: WebSocket, *, session_id: str) -> None:
        self._websocket = websocket
        self._session_id = session_id
        self._tool_uses: dict[str, dict[str, Any]] = {}
        self._send_lock = asyncio.Lock()
        self._detection_task: asyncio.Task[None] | None = None
        self._detection_offsets: dict[Path, int] = {
            (Path.cwd() / ".yolo_detections" / "detections.jsonl").resolve(): 0
        }

    async def start(self, agent: Any) -> None:  # noqa: ANN401 (protocol signature)
        self._detection_task = asyncio.create_task(self._forward_yolo_detections())

    async def stop(self) -> None:
        if self._detection_task is None:
            return
        self._detection_task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await self._detection_task
        self._detection_task = None

    async def _send(self, payload: dict[str, Any]) -> None:
        async with self._send_lock:
            await self._websocket.send_text(json.dumps(payload, default=str))

    async def _forward_yolo_detections(self) -> None:
        while True:
            await asyncio.sleep(0.25)
            for path, offset in list(self._detection_offsets.items()):
                entries, next_offset = await asyncio.to_thread(
                    self._read_detection_entries, path, offset
                )
                self._detection_offsets[path] = next_offset
                for entry in entries:
                    dimensions = self._live_frame_dimensions()
                    if dimensions is None:
                        continue
                    width, height = dimensions
                    await self._send({
                        "type": "yolo_detections",
                        "width": width,
                        "height": height,
                        "timestamp": entry.get("timestamp"),
                        "detections": entry.get("objects", []),
                    })

    @staticmethod
    def _read_detection_entries(path: Path, offset: int) -> tuple[list[dict[str, Any]], int]:
        if not path.exists():
            return [], 0
        size = path.stat().st_size
        if size < offset:
            offset = 0
        entries: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            handle.seek(offset)
            for line in handle:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    entries.append(value)
            return entries, handle.tell()

    @staticmethod
    def _live_frame_dimensions() -> tuple[int, int] | None:
        try:
            from PIL import Image

            frame = browser_camera.latest_frame(self._session_id)
            if frame is None:
                return None
            with Image.open(BytesIO(frame.jpeg)) as image:
                return int(image.width), int(image.height)
        except Exception:
            return None

    async def __call__(self, event: BidiOutputEvent) -> None:
        outgoing = _sanitize(dict(event))

        if outgoing.get("type") == "tool_use_stream":
            current = outgoing.get("current_tool_use") or {}
            if isinstance(current, dict) and current.get("toolUseId"):
                self._tool_uses[str(current["toolUseId"])] = {
                    "name": current.get("name"),
                    "input": current.get("input", {}),
                }
                if current.get("name") == "yolo_vision":
                    tool_input = current.get("input", {})
                    if isinstance(tool_input, dict):
                        save_dir = tool_input.get("save_dir", ".yolo_detections")
                        detection_path = Path(str(save_dir)).expanduser()
                        if not detection_path.is_absolute():
                            detection_path = Path.cwd() / detection_path
                        self._detection_offsets.setdefault(
                            (detection_path / "detections.jsonl").resolve(), 0
                        )

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

        await self._send(outgoing)
