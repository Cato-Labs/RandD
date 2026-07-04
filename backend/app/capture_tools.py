"""take_photo / take_video that capture from the INSPECTOR'S DEVICE CAMERA.

Priority order per capture:
1. Browser stream — frames the device camera is already streaming over the
   session WebSocket (teed into app.browser_camera). This is the camera the
   inspector actually holds (phone/tablet/laptop).
2. Server hardware (cv2) — cameras attached to the machine running this
   backend. Only relevant when the backend runs on hardware with a webcam.

Output contracts mirror strands_fun_tools.take_photo so downstream photo
routing (workspace preview, checklist pinning) keeps working.
"""

import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

from app import browser_camera


def _save_dir(save_path: Optional[str]) -> Path:
    directory = Path(save_path).expanduser() if save_path else Path.cwd()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _cv2_available_cameras(max_check: int = 4) -> List[int]:
    try:
        import cv2
    except Exception:
        return []
    found = []
    for i in range(max_check):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            found.append(i)
            cap.release()
    return found


@tool
def take_photo(
    num_photos: int = 1,
    delay: float = 0.0,
    save_path: str = None,
    discover: bool = False,
) -> Dict[str, Any]:
    """Capture photo(s) from the inspector's device camera.

    Uses the live browser camera stream when it's on (start it with
    control_camera("start") if needed), falling back to any camera attached
    to the server host. Photos are saved as JPEG files.

    Args:
        num_photos: Number of photos to take (1-10, spaced ~2s apart on the stream)
        delay: Seconds to wait before capturing
        save_path: Directory to save photos (defaults to current directory)
        discover: If True, report which capture sources are available

    Returns:
        Dict with status and content (file paths, resolution info)
    """
    try:
        if discover:
            sources = []
            if browser_camera.stream_active():
                sources.append("device camera (browser stream) — LIVE")
            cams = _cv2_available_cameras()
            if cams:
                sources.append(f"server cameras: {cams}")
            if not sources:
                sources.append(
                    'none — call control_camera("start") to turn on the device camera'
                )
            return {"status": "success", "content": [{"text": "📷 Sources: " + "; ".join(sources)}]}

        if delay > 0:
            time.sleep(min(delay, 10.0))

        directory = _save_dir(save_path)
        num_photos = max(1, min(int(num_photos), 10))

        # 1) Device camera via browser stream
        if browser_camera.stream_active():
            saved = []
            last_ts = 0.0
            deadline = time.time() + 3.0 * num_photos + 5.0
            while len(saved) < num_photos and time.time() < deadline:
                frame = browser_camera.latest_frame()
                if frame and frame.ts > last_ts:
                    last_ts = frame.ts
                    filename = f"photo-{int(frame.ts)}-device-{len(saved) + 1}.jpg"
                    filepath = directory / filename
                    filepath.write_bytes(frame.jpeg)
                    saved.append(filepath)
                if len(saved) < num_photos:
                    time.sleep(0.5)
            if saved:
                lines = [
                    "📸 **Photo Capture Results (device camera):**",
                    f"✅ Success: {len(saved)}/{num_photos} photos",
                    f"📁 Save directory: `{directory}`",
                    "",
                ]
                lines += [f"✅ `{p}` ({os.path.getsize(p):,} bytes)" for p in saved]
                return {"status": "success", "content": [{"text": "\n".join(lines)}]}

        # 2) Server hardware fallback
        cams = _cv2_available_cameras()
        if cams:
            import cv2

            cap = cv2.VideoCapture(cams[0])
            ret, img = cap.read()
            cap.release()
            if ret:
                filepath = directory / f"photo-{int(time.time())}-cam{cams[0]}.jpg"
                cv2.imwrite(str(filepath), img)
                h, w = img.shape[:2]
                return {
                    "status": "success",
                    "content": [{"text": f"📸 Captured from server camera {cams[0]}: `{filepath}` ({w}x{h})"}],
                }

        return {
            "status": "error",
            "content": [{
                "text": "❌ No camera source available. The device camera isn't streaming — "
                        'call control_camera("start") first (the inspector may need to grant permission), '
                        "then retry."
            }],
        }
    except Exception as e:
        return {"status": "error", "content": [{"text": f"❌ Photo error: {e}"}]}


@tool
def take_video(
    duration: float = 10.0,
    save_path: str = None,
    discover: bool = False,
) -> Dict[str, Any]:
    """Record a video clip from the inspector's device camera.

    Collects the live browser camera stream for ``duration`` seconds and
    assembles an mp4 (frame rate matches the stream cadence — a walkthrough
    timelapse, not full-motion video). Falls back to any server-attached
    camera for full-motion capture. Start the device camera first with
    control_camera("start").

    Args:
        duration: Seconds of stream to record (2-120)
        save_path: Directory to save the video (defaults to current directory)
        discover: If True, report which capture sources are available

    Returns:
        Dict with status and content (file path, fps, frame count)
    """
    try:
        if discover:
            return take_photo(discover=True)

        directory = _save_dir(save_path)
        duration = max(2.0, min(float(duration), 120.0))

        # 1) Device camera via browser stream
        if browser_camera.stream_active():
            start_ts = time.time()
            time.sleep(duration)
            frames = browser_camera.frames_since(start_ts)
            if len(frames) >= 2:
                import cv2
                import numpy as np

                decoded = []
                for f in frames:
                    img = cv2.imdecode(np.frombuffer(f.jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if img is not None:
                        decoded.append(img)
                if len(decoded) >= 2:
                    h, w = decoded[0].shape[:2]
                    fps = max(0.5, len(decoded) / duration)
                    filepath = directory / f"video-{int(start_ts)}-device-{int(duration)}s.mp4"
                    writer = cv2.VideoWriter(
                        str(filepath), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
                    )
                    for img in decoded:
                        if img.shape[:2] != (h, w):
                            img = cv2.resize(img, (w, h))
                        writer.write(img)
                    writer.release()
                    return {
                        "status": "success",
                        "content": [{
                            "text": f"🎥 Recorded {len(decoded)} frames over {duration:.0f}s from the device camera "
                                    f"({fps:.1f} fps timelapse) → `{filepath}` "
                                    f"({os.path.getsize(filepath):,} bytes)"
                        }],
                    }
            return {
                "status": "error",
                "content": [{"text": "❌ Too few frames arrived from the device stream — keep the camera on and retry."}],
            }

        # 2) Server hardware fallback (full-motion)
        cams = _cv2_available_cameras()
        if cams:
            from app.take_video import take_video as server_take_video

            return server_take_video(camera_ids=[cams[0]], duration=duration, save_path=str(directory))

        return {
            "status": "error",
            "content": [{
                "text": "❌ No camera source available. The device camera isn't streaming — "
                        'call control_camera("start") first, then retry.'
            }],
        }
    except Exception as e:
        return {"status": "error", "content": [{"text": f"❌ Video error: {e}"}]}
