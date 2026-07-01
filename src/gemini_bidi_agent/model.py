"""Gemini Live model factory.

Builds a :class:`~strands.experimental.bidi.models.BidiGeminiLiveModel`
configured for the ``gemini-3.1-flash-live-preview`` model. The factory simply
translates an :class:`~gemini_bidi_agent.config.AppConfig` into the provider and
client configuration expected by the Strands SDK.
"""

from __future__ import annotations

from typing import Any

from strands.experimental.bidi.models import BidiGeminiLiveModel

from .config import AppConfig, load_config


def build_model(
    config: AppConfig | None = None,
    *,
    provider_config: dict[str, Any] | None = None,
    client_config: dict[str, Any] | None = None,
) -> BidiGeminiLiveModel:
    """Construct a configured Gemini Live model.

    Args:
        config: Application configuration. Loaded from the environment when omitted.
        provider_config: Optional extra provider config merged over the config-derived
            values (e.g. additional ``inference`` fields such as ``response_modalities``).
        client_config: Optional extra client config merged over the config-derived
            values (e.g. ``http_options``).

    Returns:
        A ready-to-use :class:`BidiGeminiLiveModel` bound to the configured model id.
    """
    config = config or load_config()

    resolved_provider = config.provider_config()
    if provider_config:
        for section, values in provider_config.items():
            if isinstance(values, dict) and isinstance(resolved_provider.get(section), dict):
                resolved_provider[section] = {**resolved_provider[section], **values}
            else:
                resolved_provider[section] = values

    resolved_client = {**config.client_config(), **(client_config or {})}

    return BidiGeminiLiveModel(
        model_id=config.model_id,
        provider_config=resolved_provider,
        client_config=resolved_client,
    )
