"""Explicit authenticated-session access to transient browser camera media."""

from __future__ import annotations

from app.session_media import Frame, SessionMediaRegistry

_registry = SessionMediaRegistry(max_frames=10)


def add_frame(session_id: str, image_b64: str) -> None:
    _registry.add_frame(session_id, image_b64)


def latest_frame(
    session_id: str,
    max_age_seconds: float = 15.0,
) -> Frame | None:
    return _registry.latest_frame(session_id, max_age_seconds)


def stream_active(session_id: str, max_age_seconds: float = 15.0) -> bool:
    return _registry.stream_active(session_id, max_age_seconds)


def arm_clip_capture(session_id: str) -> None:
    _registry.arm_clip(session_id)


def deliver_clip(session_id: str, info: dict) -> None:
    _registry.deliver_clip(session_id, info)


def wait_for_clip(session_id: str, timeout: float) -> dict | None:
    return _registry.wait_for_clip(session_id, timeout)


def discard_session(session_id: str) -> None:
    if not session_id:
        raise ValueError("authenticated session_id is required")
    _registry.discard(session_id)
