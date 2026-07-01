"""Command-line entrypoint for the Gemini Live BidiAgent.

Runs a live voice + text conversation:

* Microphone audio is streamed to Gemini Live and spoken responses are played
  back through the speakers (``BidiAudioIO``).
* Transcripts, tool usage, and lifecycle events are printed to the console.

Interruptions (barge-in), tool execution, and connection restarts are handled
automatically by the agent and the audio I/O channel.

Usage:
    python -m gemini_bidi_agent.app            # voice + console transcripts
    python -m gemini_bidi_agent.app --text     # terminal text chat only

Requires the ``strands-agents[bidi-io]`` extra for microphone/speaker access.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from .agent import build_agent
from .config import load_config
from .io_console import ConsoleOutput


def _configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logging.getLogger("strands").setLevel(level)


async def run_voice(show_usage: bool = False) -> None:
    """Run a voice conversation with microphone/speaker audio and console transcripts."""
    from strands.experimental.bidi.io import BidiAudioIO  # Requires bidi-io extra.

    config = load_config()
    agent = build_agent(config)
    audio_io = BidiAudioIO()
    console = ConsoleOutput(show_usage=show_usage)

    print("Speak into your microphone. Say 'stop conversation' or press Ctrl+C to exit.")
    try:
        await agent.run(
            inputs=[audio_io.input()],
            outputs=[audio_io.output(), console],
        )
    except asyncio.CancelledError:
        print("\nConversation cancelled by user")
    finally:
        # stop() must only be called after run() exits.
        await agent.stop()


async def run_text(show_usage: bool = False) -> None:
    """Run a terminal text chat conversation."""
    from strands.experimental.bidi.io import BidiTextIO  # Requires bidi-io extra.

    config = load_config()
    agent = build_agent(config)
    text_io = BidiTextIO(input_prompt="> You: ")
    console = ConsoleOutput(show_usage=show_usage)

    print("Type a message and press Enter. Say 'stop conversation' or press Ctrl+C to exit.")
    try:
        await agent.run(
            inputs=[text_io.input()],
            outputs=[text_io.output(), console],
        )
    except asyncio.CancelledError:
        print("\nConversation cancelled by user")
    finally:
        await agent.stop()


def cli() -> None:
    """Parse arguments and launch the selected conversation mode."""
    parser = argparse.ArgumentParser(description="Gemini Live BidiAgent")
    parser.add_argument(
        "--text",
        action="store_true",
        help="Run a terminal text chat instead of voice.",
    )
    parser.add_argument(
        "--usage",
        action="store_true",
        help="Print token-usage updates.",
    )
    args = parser.parse_args()

    config = load_config()
    _configure_logging(config.log_level)

    runner = run_text if args.text else run_voice
    try:
        asyncio.run(runner(show_usage=args.usage))
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    cli()
