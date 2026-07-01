"""A fully-featured Strands ``BidiAgent`` powered by the Gemini Live API.

This package wires the Strands bidirectional streaming stack to Google's
Gemini Live model (``gemini-3.1-flash-live-preview``) with support for:

* Real-time audio and text streaming (multimodal I/O)
* Concurrent tool execution during conversations
* Automatic interruption handling (barge-in)
* Automatic connection restart on model timeouts
* Lifecycle / analytics / connection hooks
* Optional session persistence

The public building blocks are intentionally thin factory functions that
compose the Strands SDK components directly rather than wrapping them, so you
retain full access to the underlying ``BidiAgent`` and ``BidiGeminiLiveModel``
APIs.
"""

from .agent import build_agent
from .config import AppConfig, load_config
from .hooks import ConnectionMonitor, ConversationAnalytics, ConversationLogger
from .io_console import ConsoleOutput
from .model import build_model
from .tools import get_weather

__all__ = [
    "AppConfig",
    "load_config",
    "build_model",
    "build_agent",
    "get_weather",
    "ConsoleOutput",
    "ConversationLogger",
    "ConversationAnalytics",
    "ConnectionMonitor",
]

__version__ = "0.1.0"
