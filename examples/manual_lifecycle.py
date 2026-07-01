"""Manual lifecycle example: explicit start / send / receive / stop.

Demonstrates driving the agent without I/O channels, processing events
directly, and handling interruptions and connection restarts.

Run:
    python examples/manual_lifecycle.py

Requires: a configured GOOGLE_API_KEY. No audio hardware needed.
"""

import asyncio

from strands.experimental.bidi.types.events import (
    BidiConnectionRestartEvent,
    BidiErrorEvent,
    BidiInterruptionEvent,
    BidiResponseCompleteEvent,
    BidiTranscriptStreamEvent,
)

from gemini_bidi_agent import build_agent


async def main() -> None:
    # Disable session persistence for this simple one-shot example.
    agent = build_agent(use_session=False)

    await agent.start()
    try:
        await agent.send("In one sentence, what is the Gemini Live API?")

        async for event in agent.receive():
            if isinstance(event, BidiTranscriptStreamEvent) and event.is_final:
                print(f"{event.role}: {event.current_transcript or event.text}")
            elif isinstance(event, BidiInterruptionEvent):
                print(f"[interrupted] {event.reason}")
            elif isinstance(event, BidiConnectionRestartEvent):
                print("[reconnecting] history preserved...")
            elif isinstance(event, BidiErrorEvent):
                print(f"[error] {event.get('message')}")
                break
            elif isinstance(event, BidiResponseCompleteEvent):
                # End after the first complete assistant response.
                if event.stop_reason in ("complete", "error"):
                    break
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
