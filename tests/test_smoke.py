"""Smoke tests: verify the package imports and wires together correctly.

These tests construct the model and agent objects but never open a network
connection to Gemini (that only happens on ``agent.start()``), so no real API
key is required.
"""

import os

import pytest

# Ensure the genai client can be constructed without a real key.
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-used")

from gemini_bidi_agent import (  # noqa: E402
    AppConfig,
    ConsoleOutput,
    build_agent,
    build_model,
    load_config,
)
from gemini_bidi_agent.config import DEFAULT_MODEL_ID  # noqa: E402
from gemini_bidi_agent.hooks import default_hooks  # noqa: E402
from gemini_bidi_agent.tools import default_tools, end_session, get_weather  # noqa: E402


def test_default_model_id_is_requested_model():
    assert DEFAULT_MODEL_ID == "gemini-3.1-flash-live-preview"


def test_load_config_defaults():
    config = load_config(session_id=None)
    assert isinstance(config, AppConfig)
    assert config.model_id == "gemini-3.1-flash-live-preview"
    assert config.input_rate == 16000
    assert config.output_rate == 24000


def test_provider_config_shape():
    config = load_config()
    provider = config.provider_config()
    assert provider["audio"]["voice"] == config.voice
    assert provider["audio"]["input_rate"] == config.input_rate
    assert provider["inference"]["temperature"] == config.temperature


def test_build_model_uses_configured_model_id():
    model = build_model(load_config())
    assert model.model_id == "gemini-3.1-flash-live-preview"
    # Audio config merged with SDK defaults.
    assert model.config["audio"]["output_rate"] == 24000


def test_build_model_provider_override_merges():
    model = build_model(load_config(), provider_config={"audio": {"voice": "Puck"}})
    assert model.config["audio"]["voice"] == "Puck"
    # Non-overridden values are preserved.
    assert model.config["audio"]["input_rate"] == 16000


def test_default_tools_present():
    tools = default_tools()
    assert get_weather in tools
    assert end_session in tools
    assert len(tools) >= 4


def test_get_weather_returns_string():
    result = get_weather("San Francisco")
    assert isinstance(result, str)
    assert "San Francisco" in result


def test_end_session_sets_stop_flag():
    state: dict = {}
    end_session(state)
    assert state["stop_event_loop"] is True


def test_default_hooks_register():
    from strands.hooks import HookRegistry

    registry = HookRegistry()
    for hook in default_hooks():
        registry.add_hook(hook)  # Should not raise.


def test_build_agent_wires_everything(monkeypatch):
    monkeypatch.delenv("SESSION_ID", raising=False)
    agent = build_agent()
    assert agent.name == "Gemini Live Assistant"
    assert agent.model.model_id == "gemini-3.1-flash-live-preview"


def test_console_output_is_bidi_output():
    from strands.experimental.bidi.types.io import BidiOutput

    console = ConsoleOutput()
    assert isinstance(console, BidiOutput)


@pytest.mark.asyncio
async def test_console_output_handles_transcript(capsys):
    from strands.experimental.bidi.types.events import BidiTranscriptStreamEvent

    console = ConsoleOutput()
    event = BidiTranscriptStreamEvent(
        delta={"text": "Hello"},
        text="Hello",
        role="assistant",
        is_final=True,
        current_transcript="Hello world",
    )
    await console(event)
    captured = capsys.readouterr()
    assert "assistant: Hello world" in captured.out
