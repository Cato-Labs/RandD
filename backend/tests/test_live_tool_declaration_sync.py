"""Tools registered mid-session must be re-declared to the live model.

Live providers (Gemini Live, OpenAI Realtime, Nova Sonic) only call functions
declared in the connection's start config. The platform's contract is that the
agent loads most tools at runtime with ``load_tool``, so the bidi agent loop must
gracefully restart the model connection whenever a tool run changes the registry —
otherwise the newly loaded tool is registered but uncallable.
"""

import asyncio
import os

import pytest

os.environ.setdefault("VANTAGE_SKIP_SLACK_REFRESH", "1")

from app import _vendor  # noqa: F401  (must run before strands.experimental.bidi imports)
from strands import tool
from strands.experimental.bidi.agent import BidiAgent
from strands.experimental.bidi.types.events import BidiTextInputEvent
from strands.types._events import ToolResultEvent


class FakeBidiModel:
    """Minimal BidiModel that records lifecycle calls and stays open like a live session."""

    def __init__(self):
        self.config = {}
        self.start_calls = []
        self.stop_count = 0
        self.sent = []

    async def start(self, system_prompt=None, tools=None, messages=None, **kwargs):
        self.start_calls.append(
            {
                "tools": sorted(tool_spec["name"] for tool_spec in (tools or [])),
                # Snapshot: the agent mutates its messages list in place after start.
                "messages": [dict(message) for message in (messages or [])],
            }
        )

    async def stop(self):
        self.stop_count += 1

    async def send(self, content):
        self.sent.append(content)

    async def receive(self):
        await asyncio.Event().wait()
        yield  # pragma: no cover — keeps this a generator; never reached


@tool
def dynamic_tool() -> str:
    """A tool that is not registered at session start."""
    return "dynamic"


@tool
def plain_tool() -> str:
    """A tool that leaves the registry untouched."""
    return "plain"


def make_registering_tool(agent: BidiAgent):
    """Build a load_tool stand-in that registers dynamic_tool mid-session."""

    @tool
    def fake_load_tool() -> str:
        """Register another tool into the live agent's registry."""
        agent.tool_registry.register_tool(dynamic_tool)
        return "loaded"

    return fake_load_tool


async def run_tool_in_session(agent: BidiAgent, tool_name: str) -> int:
    """Start the agent, execute one tool through the loop, and return in-session stop count.

    The returned count excludes the final ``agent.stop()`` teardown, so it reflects only
    connection restarts triggered while the session was live.
    """
    events = []

    async def consume():
        async for event in agent.receive():
            events.append(event)

    await agent.start()
    consumer = asyncio.create_task(consume())
    try:
        await agent._loop._run_tool({"toolUseId": "tooluse-1", "name": tool_name, "input": {}})
        # Give queued events a chance to drain into the consumer.
        await asyncio.sleep(0.05)
    finally:
        in_session_stop_count = agent.model.stop_count
        consumer.cancel()
        try:
            await consumer
        except asyncio.CancelledError:
            pass
        await agent.stop()

    return in_session_stop_count


async def test_tool_registered_mid_session_is_redeclared_via_restart():
    model = FakeBidiModel()
    agent = BidiAgent(model=model, tools=[plain_tool])
    agent.tool_registry.register_tool(make_registering_tool(agent))

    in_session_stops = await run_tool_in_session(agent, "fake_load_tool")

    # The connection was gracefully restarted with the new tool declared.
    assert in_session_stops == 1
    assert len(model.start_calls) == 2
    assert model.start_calls[0]["tools"] == ["fake_load_tool", "plain_tool"]
    assert model.start_calls[1]["tools"] == ["dynamic_tool", "fake_load_tool", "plain_tool"]

    # The restart replayed history containing the tool use and its result...
    replayed = model.start_calls[1]["messages"]
    replayed_blocks = [block for message in replayed for block in message["content"]]
    assert any("toolUse" in block for block in replayed_blocks)
    assert any("toolResult" in block for block in replayed_blocks)

    # ...so the result must not also be sent live into the fresh connection.
    assert not any(isinstance(content, ToolResultEvent) for content in model.sent)

    # The fresh connection is idle, so the loop nudges the model to continue.
    nudges = [content for content in model.sent if isinstance(content, BidiTextInputEvent)]
    assert len(nudges) == 1
    assert "dynamic_tool" in nudges[0].text


async def test_unchanged_registry_sends_result_without_restart():
    model = FakeBidiModel()
    agent = BidiAgent(model=model, tools=[plain_tool])

    in_session_stops = await run_tool_in_session(agent, "plain_tool")

    assert in_session_stops == 0
    assert len(model.start_calls) == 1

    tool_results = [content for content in model.sent if isinstance(content, ToolResultEvent)]
    assert len(tool_results) == 1
    assert tool_results[0].tool_result["toolUseId"] == "tooluse-1"

    assert not any(isinstance(content, BidiTextInputEvent) for content in model.sent)
