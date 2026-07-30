"""Read-only access to real walkthrough clips persisted by the product flow."""

import re
import time
from pathlib import Path
from typing import Any

from strands import tool

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
