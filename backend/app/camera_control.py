"""Agent-side control of the inspector's device camera.

The camera lives in the inspector's BROWSER (getUserMedia), not on this
server. This tool doesn't touch hardware: the frontend watches for its tool
calls and starts/stops the browser camera (or captures a frame) accordingly.
The confirmation string tells the model what to expect next.
"""

from strands import tool

_ACTIONS = ("start", "stop", "snap")


@tool
def control_camera(action: str) -> str:
    """Control the inspector's device camera (the one in their browser).

    Use this yourself whenever you need to see — you do not need to ask the
    inspector to press anything (their browser may still ask them to grant
    camera permission the first time).

    Args:
        action: "start" to turn the camera on and begin receiving live frames,
            "stop" to turn it off, "snap" to capture one full-quality frame
            right now (camera must already be on).

    Returns:
        str: What will happen next.
    """
    normalized = action.strip().lower()
    if normalized not in _ACTIONS:
        return f"Unknown action {action!r} — use start, stop, or snap."
    if normalized == "start":
        return (
            "Camera start requested. Live frames will begin arriving as image "
            "input within a couple of seconds (the inspector may need to grant "
            "browser camera permission first)."
        )
    if normalized == "snap":
        return "Snap requested — a full-quality frame is being captured and sent now."
    return "Camera stop requested — frames will cease."
