"""Console output channel for the Gemini Live agent.

``ConsoleOutput`` implements the :class:`~strands.experimental.bidi.types.io.BidiOutput`
protocol and renders streaming events to the terminal: transcripts (with an
``assistant (preview)`` prefix for partial output), tool usage, interruptions,
connection lifecycle, usage, and errors.

This is a display-only sink. For microphone/speaker audio and interactive
terminal input use the SDK-provided ``BidiAudioIO`` and ``BidiTextIO`` channels
directly (they require the ``strands-agents[bidi-io]`` extra).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from strands.experimental.bidi.types.events import (
    BidiConnectionCloseEvent,
    BidiConnectionRestartEvent,
    BidiConnectionStartEvent,
    BidiErrorEvent,
    BidiInterruptionEvent,
    BidiResponseCompleteEvent,
    BidiTranscriptStreamEvent,
    BidiUsageEvent,
)

if TYPE_CHECKING:
    from strands.experimental.bidi import BidiAgent
    from strands.experimental.bidi.types.events import BidiOutputEvent

# Tool use events reuse the standard streaming event.
try:  # pragma: no cover - import shape depends on SDK version.
    from strands.types._events import ToolUseStreamEvent
except ImportError:  # pragma: no cover
    ToolUseStreamEvent = None  # type: ignore[assignment,misc]


class ConsoleOutput:
    """Render bidirectional streaming events to the console.

    Args:
        show_audio: When ``True``, print a note for each audio chunk received.
            Off by default to avoid noisy output.
        show_usage: When ``True``, print token-usage updates.
    """

    def __init__(self, show_audio: bool = False, show_usage: bool = False) -> None:
        self.show_audio = show_audio
        self.show_usage = show_usage
        self._last_preview_role: str | None = None

    async def start(self, agent: "BidiAgent") -> None:
        """Announce that the console output is ready."""
        print("[console] output channel ready")

    async def stop(self) -> None:
        """Nothing to tear down for console output."""
        return

    async def __call__(self, event: "BidiOutputEvent") -> None:
        """Dispatch an output event to the appropriate renderer."""
        if isinstance(event, BidiTranscriptStreamEvent):
            self._on_transcript(event)
        elif ToolUseStreamEvent is not None and isinstance(event, ToolUseStreamEvent):
            self._on_tool_use(event)
        elif isinstance(event, BidiInterruptionEvent):
            print(f"\n[interrupted] {event.reason}")
        elif isinstance(event, BidiConnectionStartEvent):
            print(f"[connected] model={event['model']} connection={event['connection_id']}")
        elif isinstance(event, BidiConnectionRestartEvent):
            print("[reconnecting] connection restarting, history preserved...")
        elif isinstance(event, BidiConnectionCloseEvent):
            print(f"[closed] reason={event['reason']}")
        elif isinstance(event, BidiResponseCompleteEvent):
            if event.stop_reason not in ("complete",):
                print(f"[response {event.stop_reason}]")
        elif isinstance(event, BidiUsageEvent):
            if self.show_usage:
                print(
                    f"[usage] input={event.get('inputTokens')} "
                    f"output={event.get('outputTokens')} total={event.get('totalTokens')}"
                )
        elif isinstance(event, BidiErrorEvent):
            print(f"[error] {event.get('message')} (code={event.get('code')})")

    def _on_transcript(self, event: BidiTranscriptStreamEvent) -> None:
        role = event.role
        if event.is_final:
            text = event.current_transcript or event.text
            print(f"\n{role}: {text}")
            self._last_preview_role = None
        else:
            # Partial transcript preview.
            if self._last_preview_role != role:
                print(f"\n{role} (preview): ", end="", flush=True)
                self._last_preview_role = role
            print(event.text, end="", flush=True)

    def _on_tool_use(self, event: object) -> None:
        tool_use = None
        if isinstance(event, dict):
            tool_use = event.get("current_tool_use")
        if tool_use:
            name = tool_use.get("name")
            tool_input = tool_use.get("input")
            print(f"\n[tool] {name} input={tool_input}")
