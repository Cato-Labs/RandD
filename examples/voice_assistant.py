"""Voice assistant example: microphone + speakers with console transcripts.

Streams microphone audio to Gemini Live and plays spoken responses through the
speakers, while printing transcripts and tool usage to the console.

Run:
    python examples/voice_assistant.py

Requires: strands-agents[bidi-io] and a configured GOOGLE_API_KEY.
"""

import asyncio

from strands.experimental.bidi.io import BidiAudioIO

from gemini_bidi_agent import build_agent
from gemini_bidi_agent.io_console import ConsoleOutput


async def main() -> None:
    agent = build_agent()
    audio_io = BidiAudioIO()
    console = ConsoleOutput()

    print("Speak into your microphone. Say 'stop conversation' or press Ctrl+C to exit.")
    try:
        await agent.run(
            inputs=[audio_io.input()],
            outputs=[audio_io.output(), console],
        )
    except asyncio.CancelledError:
        pass
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
