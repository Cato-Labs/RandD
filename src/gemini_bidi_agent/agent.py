"""Agent factory.

Composes the Strands ``BidiAgent`` with the Gemini Live model, tools, hooks, and
an optional session manager. This is a thin factory that returns a fully
configured SDK ``BidiAgent`` — it does not wrap or hide the agent's API, so
callers use ``start`` / ``send`` / ``receive`` / ``run`` / ``stop`` directly.
"""

from __future__ import annotations

from typing import Any

from strands.experimental.bidi import BidiAgent

from .config import AppConfig, load_config
from .hooks import default_hooks
from .model import build_model
from .session import build_session_manager
from .tools import default_tools


def build_agent(
    config: AppConfig | None = None,
    *,
    tools: list[Any] | None = None,
    hooks: list[Any] | None = None,
    use_session: bool = True,
    **model_kwargs: Any,
) -> BidiAgent:
    """Build a fully configured Gemini Live :class:`BidiAgent`.

    Args:
        config: Application configuration. Loaded from the environment when omitted.
        tools: Override the default tool set. Defaults to
            :func:`~gemini_bidi_agent.tools.default_tools`.
        hooks: Override the default hook providers. Defaults to
            :func:`~gemini_bidi_agent.hooks.default_hooks`.
        use_session: When ``True`` (default), attach a session manager if a
            ``SESSION_ID`` is configured.
        **model_kwargs: Extra keyword arguments forwarded to
            :func:`~gemini_bidi_agent.model.build_model` (e.g. ``provider_config``).

    Returns:
        A configured :class:`BidiAgent` ready to ``start()``/``run()``.
    """
    config = config or load_config()

    model = build_model(config, **model_kwargs)
    session_manager = build_session_manager(config) if use_session else None

    return BidiAgent(
        model=model,
        tools=tools if tools is not None else default_tools(),
        system_prompt=config.system_prompt,
        hooks=hooks if hooks is not None else default_hooks(),
        session_manager=session_manager,
        name="Gemini Live Assistant",
        description="A real-time multimodal voice assistant powered by Gemini Live.",
    )
