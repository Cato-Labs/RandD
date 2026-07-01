"""Text chat example: terminal input/output only (no audio hardware needed).

Run:
    python examples/text_chat.py

Requires: strands-agents[bidi-io] (prompt-toolkit) and a configured GOOGLE_API_KEY.
"""

import asyncio

from strands.experimental.bidi.io import BidiTextIO

from gemini_bidi_agent import build_agent
from gemini_bidi_agent.io_console import ConsoleOutput


async def main() -> None:
    agent = build_agent()
    text_io = BidiTextIO(input_prompt="> You: ")
    console = ConsoleOutput()

    print("Type a message and press Enter. Say 'stop conversation' or press Ctrl+C to exit.")
    try:
        await agent.run(
            inputs=[text_io.input()],
            outputs=[text_io.output(), console],
        )
    except asyncio.CancelledError:
        pass
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
