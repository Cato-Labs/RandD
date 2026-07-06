"""Access recorded walkthrough videos (list + deliver).

take_video records a clip and returns its transcript in-session, but afterward
the agent had NO way to find, reference, or send a saved walkthrough — the
camera/vision tools only see the LIVE stream. These tools close that gap: list
the clips captured on disk (grouped by section, newest first) and deliver a
chosen clip to Slack. Clips live in ``workspace/captures/`` and are also served
at ``/workspace/captures/<name>`` for the UI.

Each capture yields a raw recording (``.webm``/``.mp4``) plus a compact
``-web.mp4`` (small, plays everywhere). We surface the compact one for delivery
and playback, falling back to the raw file.
"""

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

from app.slack_token import ensure_fresh_bot_token

_CAPTURES = Path(__file__).resolve().parent.parent / "workspace" / "captures"
# video-<epoch>-<section-slug>[-web].(mp4|webm)
_NAME_RE = re.compile(r"^video-(\d+)-(.+?)(-web)?\.(mp4|webm)$")


def _clips() -> List[Dict[str, Any]]:
    """One entry per capture (keyed by epoch+section), preferring the web mp4."""
    if not _CAPTURES.exists():
        return []
    groups: Dict[str, Dict[str, Any]] = {}
    for f in _CAPTURES.iterdir():
        m = _NAME_RE.match(f.name)
        if not m:
            continue
        epoch, slug, is_web, ext = int(m.group(1)), m.group(2), bool(m.group(3)), m.group(4)
        key = f"{epoch}-{slug}"
        entry = groups.setdefault(key, {"epoch": epoch, "section": slug.replace("-", " ")})
        # Prefer the compact web mp4 as the deliverable; keep raw as fallback.
        if is_web or "deliver" not in entry:
            if is_web or ext == "mp4" or "deliver" not in entry:
                entry["deliver"] = f
        entry.setdefault("raw", f)
        if is_web:
            entry["deliver"] = f
    out = []
    for e in groups.values():
        chosen: Path = e.get("deliver") or e["raw"]
        out.append({
            "section": e["section"],
            "recorded": time.strftime("%Y-%m-%d %H:%M", time.localtime(e["epoch"])),
            "epoch": e["epoch"],
            "file": chosen.name,
            "path": f"captures/{chosen.name}",  # workspace-relative (send-ready)
            "url": f"/workspace/captures/{chosen.name}",
            "size": chosen.stat().st_size,
        })
    out.sort(key=lambda c: c["epoch"], reverse=True)
    return out


@tool
def list_walkthrough_videos(section: Optional[str] = None, limit: int = 12) -> Dict[str, Any]:
    """List recorded walkthrough videos so you can reference or send them.

    Use this whenever asked about, or asked to send/share, a walkthrough clip —
    it is how you ACCESS videos recorded earlier (the camera/vision tools only
    see the live stream). Returns clips newest-first with their section, time,
    size, playback url, and a send-ready path (pass that path to
    send_video_to_slack or gmail_send_with_attachments).

    Args:
        section: Optional filter, matched loosely against the section slug
            (e.g. "hot tub", "kitchen", "housekeeping").
        limit: Max clips to return (newest first).

    Returns:
        Dict with status and the clip listing.
    """
    try:
        clips = _clips()
        if section:
            needle = re.sub(r"[^a-z0-9]+", "", section.lower())
            clips = [c for c in clips if needle in re.sub(r"[^a-z0-9]+", "", c["section"].lower())]
        if not clips:
            where = f" for section '{section}'" if section else ""
            return {"status": "success",
                    "content": [{"text": f"🎞 No walkthrough videos found{where} yet."}]}
        clips = clips[: max(1, int(limit))]
        lines = ["🎞 **Walkthrough videos** (newest first):"]
        for c in clips:
            lines.append(f"- {c['section']} — {c['recorded']} — {c['size']:,} bytes — "
                         f"path `{c['path']}` — play {c['url']}")
        return {"status": "success", "content": [{"text": "\n".join(lines)}]}
    except Exception as exc:
        return {"status": "error", "content": [{"text": f"❌ Could not list videos: {exc}"}]}


@tool
def send_video_to_slack(
    section: Optional[str] = None,
    path: Optional[str] = None,
    channel: Optional[str] = None,
    initial_comment: Optional[str] = None,
) -> Dict[str, Any]:
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
        target: Optional[Path] = None
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
                         if needle in re.sub(r"[^a-z0-9]+", "", c["section"].lower())]
            if clips:
                target = _CAPTURES / clips[0]["file"]

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
