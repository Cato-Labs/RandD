"""Session management helpers.

Provides an optional :class:`~strands.session.session_manager.SessionManager`
for persisting conversation history and agent state across runs.

.. note::
   Gemini Live has limited session-management support: it does not yet produce a
   full message history, so cross-restart persistence is best-effort. Within a
   single session lifecycle, Gemini's own session-resumption handles connection
   restarts (connections can persist up to 24 hours). A session manager is still
   useful for persisting agent state and any recorded messages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .config import AppConfig, load_config

if TYPE_CHECKING:
    from strands.session.session_manager import SessionManager


def build_session_manager(config: AppConfig | None = None) -> "SessionManager | None":
    """Build a file-based session manager when a session id is configured.

    Args:
        config: Application configuration. Loaded from the environment when omitted.

    Returns:
        A :class:`FileSessionManager` when ``session_id`` is set, otherwise ``None``.
    """
    config = config or load_config()

    if not config.session_id:
        return None

    # Imported lazily so the dependency is only required when sessions are used.
    from strands.session.file_session_manager import FileSessionManager

    if config.session_storage_dir:
        return FileSessionManager(
            session_id=config.session_id,
            storage_dir=config.session_storage_dir,
        )
    return FileSessionManager(session_id=config.session_id)
