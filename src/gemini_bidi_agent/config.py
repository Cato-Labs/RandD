"""Application configuration loaded from the environment.

Configuration is read from environment variables (and, if present, a ``.env``
file in the working directory). See ``.env.example`` for the full list of
supported variables and their defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

try:  # Optional convenience: load variables from a local .env file.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv is an optional helper.
    pass

# The Gemini Live model requested for this project.
DEFAULT_MODEL_ID = "gemini-3.1-flash-live-preview"
DEFAULT_VOICE = "Kore"
# Gemini Live expects 16 kHz PCM input and streams 24 kHz PCM output.
DEFAULT_INPUT_RATE = 16000
DEFAULT_OUTPUT_RATE = 24000
DEFAULT_TEMPERATURE = 0.7
DEFAULT_SYSTEM_PROMPT = "You are a helpful, concise voice assistant."


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name!r} must be an integer, got {value!r}") from exc


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name!r} must be a number, got {value!r}") from exc


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


@dataclass
class AppConfig:
    """Resolved application configuration.

    Attributes:
        api_key: Google AI Studio API key. Falls back to ``GOOGLE_API_KEY``.
        model_id: Gemini Live model identifier.
        voice: Prebuilt voice name for audio responses.
        input_rate: Microphone input sample rate in Hz.
        output_rate: Speaker output sample rate in Hz.
        temperature: Sampling temperature for generation.
        system_prompt: System instructions for the assistant.
        session_id: Optional session id enabling conversation persistence.
        session_storage_dir: Optional directory for persisted sessions.
        log_level: Logging level name for the ``strands`` and app loggers.
    """

    api_key: str | None = None
    model_id: str = DEFAULT_MODEL_ID
    voice: str = DEFAULT_VOICE
    input_rate: int = DEFAULT_INPUT_RATE
    output_rate: int = DEFAULT_OUTPUT_RATE
    temperature: float = DEFAULT_TEMPERATURE
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    session_id: str | None = None
    session_storage_dir: str | None = None
    log_level: str = "INFO"

    def provider_config(self) -> dict[str, Any]:
        """Return the ``provider_config`` dict for ``BidiGeminiLiveModel``."""
        return {
            "audio": {
                "voice": self.voice,
                "input_rate": self.input_rate,
                "output_rate": self.output_rate,
            },
            "inference": {
                "temperature": self.temperature,
            },
        }

    def client_config(self) -> dict[str, Any]:
        """Return the ``client_config`` dict for ``BidiGeminiLiveModel``.

        When no API key is configured, an empty dict is returned so that the
        underlying ``google-genai`` client can fall back to the
        ``GOOGLE_API_KEY`` environment variable.
        """
        if self.api_key:
            return {"api_key": self.api_key}
        return {}


def load_config(**overrides: Any) -> AppConfig:
    """Build an :class:`AppConfig` from the environment.

    Args:
        **overrides: Explicit values that take precedence over the environment.

    Returns:
        A resolved :class:`AppConfig` instance.
    """
    config = AppConfig(
        api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_API_KEY"),
        model_id=_env_str("GEMINI_MODEL_ID", DEFAULT_MODEL_ID),
        voice=_env_str("GEMINI_VOICE", DEFAULT_VOICE),
        input_rate=_env_int("GEMINI_INPUT_RATE", DEFAULT_INPUT_RATE),
        output_rate=_env_int("GEMINI_OUTPUT_RATE", DEFAULT_OUTPUT_RATE),
        temperature=_env_float("GEMINI_TEMPERATURE", DEFAULT_TEMPERATURE),
        system_prompt=_env_str("GEMINI_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
        session_id=os.getenv("SESSION_ID") or None,
        session_storage_dir=os.getenv("SESSION_STORAGE_DIR") or None,
        log_level=_env_str("LOG_LEVEL", "INFO"),
    )

    for key, value in overrides.items():
        if not hasattr(config, key):
            raise AttributeError(f"Unknown config override: {key!r}")
        setattr(config, key, value)

    return config
