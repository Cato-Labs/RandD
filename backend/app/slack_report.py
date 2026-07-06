"""Deliver the inspection form to Slack reliably (custom tool).

The generic ``strands_tools.slack`` files_upload_v2 passthrough works, but it
depends on the model passing a correct workspace-relative ``file`` path — and a
wrong ``workspace/`` prefix (or ``content`` vs ``file`` confusion) silently
uploads nothing. This tool removes that footgun: it resolves the report path
itself, defaults to the live snapshot, refreshes the rotating bot token, and
uploads via ``files_upload_v2`` to the default channel unless told otherwise.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from strands import tool

from app.slack_token import ensure_fresh_bot_token

_WORKSPACE = Path(__file__).resolve().parent.parent / "workspace"
_DEFAULT_REPORT = "reports/inspection-report-latest.html"


def _resolve(path: str) -> Path:
    """Resolve a report path: absolute, cwd (workspace), or repo-known dirs."""
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    # Tolerate a stray "workspace/" prefix the model may add.
    stripped = Path(*candidate.parts[1:]) if candidate.parts[:1] == ("workspace",) else candidate
    for base in (Path.cwd(), _WORKSPACE, _WORKSPACE / "reports", _WORKSPACE / "captures"):
        for cand in (candidate, stripped):
            if (base / cand).exists():
                return base / cand
    return _WORKSPACE / stripped


@tool
def send_report_to_slack(
    title: Optional[str] = None,
    initial_comment: Optional[str] = None,
    channel: Optional[str] = None,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload the inspection form to Slack as a downloadable file attachment.

    Use this to send THE INSPECTION FORM ITSELF to the team — it is the reliable
    path (no manual path juggling). By default it sends the live self-contained
    snapshot (reports/inspection-report-latest.html, all checks/notes/photos/
    videos baked in) to the default channel. Confirm with the inspector before
    sending. For plain text updates use slack_send_message instead.

    Args:
        title: File title shown in Slack (default "Inspection report").
        initial_comment: Message posted alongside the file (e.g. "LBV — ready
            for guests, 2 repairs logged").
        channel: Target channel id. Defaults to SLACK_DEFAULT_CHANNEL_ID.
        path: Report file to send. Defaults to the live inspection snapshot;
            workspace-relative or absolute.

    Returns:
        Dict with status and content (permalink / file id, or an error).
    """
    try:
        channel = channel or os.getenv("SLACK_DEFAULT_CHANNEL_ID")
        if not channel:
            return {"status": "error", "content": [{"text": "❌ No channel: pass channel= or "
                                                            "set SLACK_DEFAULT_CHANNEL_ID."}]}
        report = _resolve(path or _DEFAULT_REPORT)
        if not report.exists():
            return {"status": "error",
                    "content": [{"text": f"❌ Report not found: {path or _DEFAULT_REPORT} "
                                         "(the form exports itself as it changes — make an "
                                         "edit first)."}]}

        ensure_fresh_bot_token()  # rotating xoxe.xoxb token expires ~12h
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            return {"status": "error", "content": [{"text": "❌ SLACK_BOT_TOKEN is not set."}]}

        from slack_sdk import WebClient

        resp = WebClient(token=token).files_upload_v2(
            channel=channel,
            file=str(report),
            filename="inspection-report.html",
            title=title or "Inspection report",
            initial_comment=initial_comment or "Inspection form attached.",
        )
        info = (resp.get("file") or {}) if hasattr(resp, "get") else {}
        where = info.get("permalink") or info.get("id") or "uploaded"
        return {"status": "success",
                "content": [{"text": f"📎 Inspection form delivered to Slack ({report.name} → "
                                     f"{channel}). {where}"}]}
    except Exception as exc:
        return {"status": "error", "content": [{"text": f"❌ Slack upload failed: {exc}"}]}
