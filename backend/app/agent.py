import os

from strands.experimental.bidi.agent import BidiAgent
from strands.experimental.bidi.models.gemini_live import BidiGeminiLiveModel
from strands_tools import editor, load_tool, shell

from app.prompts import SYSTEM_PROMPT

DEFAULT_MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025"

TOOLS = [editor.editor, shell.shell, load_tool.load_tool]


def create_agent(mode: str, voice: str) -> BidiAgent:
    """Create one Gemini Live BidiAgent for a WebSocket connection."""
    model_id = os.getenv("GEMINI_LIVE_MODEL", DEFAULT_MODEL_ID)
    provider_config = {"audio": {"voice": voice}}

    if mode == "text":
        provider_config["inference"] = {"response_modalities": ["TEXT"]}

    client_config = None
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        client_config = {"api_key": api_key}

    model = BidiGeminiLiveModel(
        model_id=model_id,
        provider_config=provider_config,
        client_config=client_config,
    )
    return BidiAgent(model=model, tools=TOOLS, system_prompt=SYSTEM_PROMPT)
