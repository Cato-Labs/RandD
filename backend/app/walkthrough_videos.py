"""Access recorded walkthrough clips persisted by the product flow (list + deliver)."""

import os
import re
import time
from pathlib import Path
from typing import Any

from strands import tool

from app.slack_token import ensure_fresh_bot_token

_CAPTURES = Path(__file__).resolve().parent.parent / "workspace" / "captures"
_NAME_RE = re.compile(r"^video-(\d+)-(.+?)(-web)?\.(mp4|webm)$")


def _clips() -> list[dict[str, Any]]:
    if not _CAPTURES.exists():
        return []
    groups: dict[str, dict[str, Any]] = {}
    for path in _CAPTURES.iterdir():
        match = _NAME_RE.match(path.name)
        if match is None:
            continue
        epoch = int(match.group(1))
        slug = match.group(2)
        is_web = bool(match.group(3))
        key = f"{epoch}-{slug}"
        entry = groups.setdefault(
            key,
            {"epoch": epoch, "section": slug.replace("-", " "), "raw": path},
        )
        if is_web:
            entry["deliver"] = path

    clips: list[dict[str, Any]] = []
    for entry in groups.values():
        chosen: Path = entry.get("deliver") or entry["raw"]
        clips.append({
            "section": entry["section"],
            "recorded": time.strftime("%Y-%m-%d %H:%M", time.localtime(entry["epoch"])),
            "epoch": entry["epoch"],
            "path": f"captures/{chosen.name}",
            "playback_path": f"/workspace/captures/{chosen.name}",
            "size_bytes": chosen.stat().st_size,
        })
    return sorted(clips, key=lambda clip: int(clip["epoch"]), reverse=True)


@tool
def list_walkthrough_videos(
    section: str | None = None,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """List real persisted walkthrough videos, newest first.

    Args:
        section: Optional loose section-name filter.
        limit: Maximum number of clips to return.

    Returns:
        Clip metadata containing persisted and playback paths.
    """
    clips = _clips()
    if section:
        needle = re.sub(r"[^a-z0-9]+", "", section.lower())
        clips = [
            clip
            for clip in clips
            if needle in re.sub(r"[^a-z0-9]+", "", str(clip["section"]).lower())
        ]
    return clips[: max(1, int(limit))]


@tool
def send_video_to_slack(
    section: str | None = None,
    path: str | None = None,
    channel: str | None = None,
    initial_comment: str | None = None,
) -> dict[str, Any]:
    """Upload a recorded walkthrough video to Slack.

    Sends the compact web mp4 (plays inline in Slack). By default sends the most
    recent clip; pass section to pick the latest for that area, or path for a
    specific file (from list_walkthrough_videos). Posts to the default channel
    unless channel is given. Confirm with the inspector before sending.

    Args:
        section: Send the latest clip for this section (e.g. "hot tub").
        path: Specific clip path (workspace-relative or absolute) to send.
        channel: Target channel id. Defaults to SLACK_DEFAULT_CHANNEL_ID.
        initial_comment: Message posted with the file.

    Returns:
        Dict with status and content (permalink / file id, or an error).
    """
    try:
        channel = channel or os.getenv("SLACK_DEFAULT_CHANNEL_ID")
        if not channel:
            return {"status": "error", "content": [{"text": "❌ No channel: pass channel= or "
                                                            "set SLACK_DEFAULT_CHANNEL_ID."}]}
        # Resolve which clip to send.
        target: Path | None = None
        if path:
            p = Path(path).expanduser()
            if not p.is_absolute():
                stripped = Path(*p.parts[1:]) if p.parts[:1] == ("workspace",) else p
                for base in (Path.cwd(), _CAPTURES.parent, _CAPTURES, _CAPTURES.parent / "reports"):
                    if (base / stripped).exists():
                        p = base / stripped
                        break
            target = p
        else:
            clips = _clips()
            if section:
                needle = re.sub(r"[^a-z0-9]+", "", section.lower())
                clips = [c for c in clips
                         if needle in re.sub(r"[^a-z0-9]+", "", str(c["section"]).lower())]
            if clips:
                target = _CAPTURES / Path(str(clips[0]["path"])).name

        if not target or not target.exists():
            hint = f" for section '{section}'" if section else ""
            return {"status": "error",
                    "content": [{"text": f"❌ No walkthrough video found{hint}. Call "
                                         "list_walkthrough_videos to see what's available."}]}

        ensure_fresh_bot_token()
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            return {"status": "error", "content": [{"text": "❌ SLACK_BOT_TOKEN is not set."}]}

        from slack_sdk import WebClient

        resp = WebClient(token=token).files_upload_v2(
            channel=channel,
            file=str(target),
            filename=target.name,
            title=f"Walkthrough — {section}" if section else "Walkthrough video",
            initial_comment=initial_comment or "Walkthrough clip attached.",
        )
        info = (resp.get("file") or {}) if hasattr(resp, "get") else {}
        where = info.get("permalink") or info.get("id") or "uploaded"
        return {"status": "success",
                "content": [{"text": f"🎥 Walkthrough delivered to Slack ({target.name} → "
                                     f"{channel}). {where}"}]}
    except Exception as exc:
        return {"status": "error", "content": [{"text": f"❌ Slack video upload failed: {exc}"}]}
