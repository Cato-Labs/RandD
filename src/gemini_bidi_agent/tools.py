"""Tools available to the Gemini Live agent.

Combines a couple of built-in Strands tools with a small custom example tool.
Tools execute concurrently during the conversation without blocking streaming.

The ``end_session`` tool demonstrates the graceful-shutdown mechanism: any tool
that sets ``request_state["stop_event_loop"] = True`` causes the agent loop to
close the connection instead of sending the result back to the model.
"""

from __future__ import annotations

from typing import Any

from strands import tool

# Built-in tools shipped with strands-agents-tools. Imported at module load so a
# missing dependency fails fast with a clear error.
from strands_tools import calculator, current_time, stop


@tool
def get_weather(location: str) -> str:
    """Get the current weather for a location.

    Args:
        location: City name or location to look up the weather for.

    Returns:
        A short human-readable weather description.
    """
    # Placeholder implementation. Replace with a real weather API call
    # (e.g. Open-Meteo, OpenWeatherMap) in production.
    return f"The weather in {location} is currently sunny and 72\u00b0F (22\u00b0C)."


@tool
def end_session(request_state: dict[str, Any]) -> str:
    """End the conversation gracefully.

    Sets ``stop_event_loop`` so the agent loop shuts the connection down cleanly.

    Args:
        request_state: Per-invocation state injected by the agent loop.

    Returns:
        A short goodbye message.
    """
    request_state["stop_event_loop"] = True
    return "Ending the conversation. Goodbye!"


def default_tools() -> list[Any]:
    """Return the default tool set wired into the agent.

    Returns:
        A list of tools: calculator, current time, a demo weather tool, and both
        the built-in ``stop`` tool and a custom ``end_session`` tool so the user
        can verbally end the conversation.
    """
    return [calculator, current_time, get_weather, stop, end_session]
