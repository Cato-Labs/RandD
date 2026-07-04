"""Bridge between the inspector's BROWSER camera and server-side capture tools.

The device camera lives in the browser (getUserMedia) and streams JPEG frames
over the session WebSocket as ``bidi_image_input`` events. The input adapter
tees every frame into this ring buffer, so tools like take_photo/take_video
can capture from the REAL device camera instead of the (nonexistent) server
camera.

Single-process dev server: one buffer shared by the active session
(last-writer-wins if multiple sessions stream simultaneously).
"""

import base64
import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass
class Frame:
    ts: float
    jpeg: bytes


_MAX_FRAMES = 600  # ~10-20 minutes at the browser's streaming cadence
_lock = threading.Lock()
_frames: deque[Frame] = deque(maxlen=_MAX_FRAMES)


def add_frame(image_b64: str) -> None:
    """Record one browser frame (base64 JPEG payload from bidi_image_input)."""
    try:
        jpeg = base64.b64decode(image_b64)
    except Exception:
        return
    with _lock:
        _frames.append(Frame(ts=time.time(), jpeg=jpeg))


def latest_frame(max_age_seconds: float = 15.0) -> Frame | None:
    """Most recent frame, or None if the stream is stale/absent."""
    with _lock:
        if not _frames:
            return None
        frame = _frames[-1]
    if time.time() - frame.ts > max_age_seconds:
        return None
    return frame


def frames_since(start_ts: float) -> list[Frame]:
    """All frames captured at/after ``start_ts`` (oldest first)."""
    with _lock:
        return [f for f in _frames if f.ts >= start_ts]


def stream_active(max_age_seconds: float = 15.0) -> bool:
    return latest_frame(max_age_seconds) is not None
