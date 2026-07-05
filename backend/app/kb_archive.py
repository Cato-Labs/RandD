"""Archive inspection reports into the Bedrock Knowledge Base's S3 bucket.

The KB data source only ingests objects under its configured prefix
(``BEDROCK_KB_S3_PREFIX``, default ``memories/``), so each archive writes two
objects into the same bucket (``BEDROCK_KB_S3_BUCKET``):

- ``memories/inspection-reports/<unit>/<timestamp>-summary.txt`` — a plain-text
  digest of the inspection (verdicts, notes, section walkthroughs, repairs).
  Lives under the data-source prefix, so Bedrock ingests it and the agent can
  recall past inspections through ``search_memory``.
- ``inspection-reports/artifacts/<unit>/<timestamp>-report.html`` — the full
  self-contained interactive form (base64 media baked in). Deliberately outside
  the data-source prefix: it is the durable artifact, not vector-index fodder.

Best-effort ``StartIngestionJob`` follows the summary upload when
``BEDROCK_KB_ID`` + ``BEDROCK_KB_DATA_SOURCE_ID`` are configured.

Bootstrap the folders once with: ``python -m app.kb_archive --init``
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

from strands import tool

REPORTS_DIR = Path(__file__).resolve().parent.parent / "workspace" / "reports"
LATEST_REPORT = REPORTS_DIR / "inspection-report-latest.html"

_STATE_RE = re.compile(r"window\.__QC_STATE__ = (\{.*?\});</script>", re.S)


def _bucket() -> Optional[str]:
    return os.getenv("BEDROCK_KB_S3_BUCKET")


def _folder() -> str:
    return os.getenv("KB_REPORTS_FOLDER", "inspection-reports").strip("/")


def _knowledge_prefix() -> str:
    base = os.getenv("BEDROCK_KB_S3_PREFIX", "memories/").strip("/")
    return f"{base}/{_folder()}"


def _artifact_prefix() -> str:
    return f"{_folder()}/artifacts"


def _s3() -> Any:
    import boto3

    return boto3.client("s3")


def extract_state(html: str) -> Optional[Dict[str, Any]]:
    """Pull the embedded ``window.__QC_STATE__`` payload out of a report export."""
    m = _STATE_RE.search(html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def summarize_state(state: Dict[str, Any]) -> str:
    """Render the inspection state as a plain-text knowledge document."""
    lines = [
        f"TURNOVER INSPECTION REPORT — {state.get('property', 'unknown property')}",
        f"Archived: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"Signed off: {'YES — ready for guests' if state.get('signedOff') else 'no'}",
        "",
    ]
    for sec in state.get("sections", []) or []:
        lines.append(f"SECTION: {sec.get('id', '?')}")
        note = (sec.get("note") or "").strip()
        if note:
            lines.append(f"  Walkthrough note: {note}")
        if sec.get("video"):
            lines.append("  Walkthrough video: attached")
        lines.append("")
    items = state.get("items", []) or []
    done = sum(1 for i in items if i.get("checked"))
    lines.append(f"LINE ITEMS ({done}/{len(items)} complete):")
    for item in items:
        mark = "PASS" if item.get("checked") else "OPEN"
        entry = f"  [{mark}] {item.get('label', item.get('id', '?'))}"
        photos = item.get("photos") or []
        if photos:
            entry += f" ({len(photos)} photo{'s' if len(photos) != 1 else ''})"
        lines.append(entry)
        note = (item.get("note") or "").strip()
        if note:
            lines.append(f"        note: {note}")
    repairs = (state.get("repairs") or "").strip()
    lines += ["", f"REPAIRS NEEDED: {repairs if repairs else 'none logged'}"]
    return "\n".join(lines)


def _start_ingestion(s3_client_unused: Any = None) -> Optional[str]:
    """Best-effort Bedrock KB ingestion so the new summary becomes searchable."""
    kb_id = os.getenv("BEDROCK_KB_ID")
    ds_id = os.getenv("BEDROCK_KB_DATA_SOURCE_ID")
    if not (kb_id and ds_id):
        return None
    try:
        import boto3

        client = boto3.client("bedrock-agent")
        response = client.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)
        response_dict = response if isinstance(response, dict) else {}
        ingestion_job = response_dict.get("ingestionJob")
        if isinstance(ingestion_job, dict):
            ingestion_job_id = ingestion_job.get("ingestionJobId")
            if isinstance(ingestion_job_id, str):
                return ingestion_job_id
        return None
    except Exception:
        return None  # sync happens on the KB's own schedule instead


def archive_report(html: str, note: Optional[str] = None) -> Dict[str, Any]:
    """Upload the report (summary + full artifact) into the KB bucket folder."""
    bucket = _bucket()
    if not bucket:
        raise RuntimeError(
            "BEDROCK_KB_S3_BUCKET is not set — configure the knowledge-base bucket "
            "in backend/.env to enable report archiving."
        )
    state = extract_state(html)
    prop = (state or {}).get("property", "unknown")
    slug = re.sub(r"[^a-zA-Z0-9-]+", "-", str(prop)).strip("-").lower() or "unknown"
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())

    summary = summarize_state(state) if state else "Inspection report (no embedded state)."
    if note:
        summary = f"{summary}\n\nARCHIVE NOTE: {note}"

    summary_key = f"{_knowledge_prefix()}/{slug}/{stamp}-summary.txt"
    artifact_key = f"{_artifact_prefix()}/{slug}/{stamp}-report.html"

    s3 = _s3()
    s3.put_object(Bucket=bucket, Key=summary_key, Body=summary.encode("utf-8"),
                  ContentType="text/plain; charset=utf-8")
    s3.put_object(Bucket=bucket, Key=artifact_key, Body=html.encode("utf-8"),
                  ContentType="text/html; charset=utf-8")
    ingestion_job = _start_ingestion()

    return {
        "bucket": bucket,
        "summary_uri": f"s3://{bucket}/{summary_key}",
        "artifact_uri": f"s3://{bucket}/{artifact_key}",
        "ingestion_job_id": ingestion_job,
        "signed_off": bool((state or {}).get("signedOff")),
    }


def ensure_folders() -> Dict[str, str]:
    """Create the two folder markers in the KB bucket (idempotent)."""
    bucket = _bucket()
    if not bucket:
        raise RuntimeError("BEDROCK_KB_S3_BUCKET is not set.")
    s3 = _s3()
    keys = [f"{_knowledge_prefix()}/", f"{_artifact_prefix()}/"]
    for key in keys:
        s3.put_object(Bucket=bucket, Key=key, Body=b"")
    return {"bucket": bucket, "folders": ", ".join(keys)}


@tool
def archive_inspection_report(note: str = None) -> Dict[str, Any]:
    """Archive the latest inspection form into the knowledge-base S3 bucket.

    Uploads a plain-text digest under the Bedrock KB data-source prefix (so it
    becomes searchable long-term memory of past inspections) plus the full
    interactive HTML report as a durable artifact, then kicks off a KB
    ingestion job when configured. Use after sign-off, or whenever the
    inspector wants the current state preserved.

    Args:
        note: Optional context to append to the archived summary
            (e.g. "signed off after hot-tub re-clean")

    Returns:
        Dict with status and content (S3 URIs, ingestion job id)
    """
    try:
        if not LATEST_REPORT.exists():
            return {
                "status": "error",
                "content": [{"text": "❌ No exported inspection form found yet — the form "
                                     "exports itself as it changes; make an edit first."}],
            }
        result = archive_report(LATEST_REPORT.read_text(encoding="utf-8"), note=note)
        ingest = (f" Ingestion job `{result['ingestion_job_id']}` started."
                  if result.get("ingestion_job_id") else
                  " KB will pick it up on its next sync.")
        return {
            "status": "success",
            "content": [{
                "text": f"📦 Archived inspection report to the knowledge base bucket.\n"
                        f"- Searchable summary: `{result['summary_uri']}`\n"
                        f"- Full interactive report: `{result['artifact_uri']}`\n"
                        f"- Signed off: {result['signed_off']}.{ingest}"
            }],
        }
    except Exception as e:
        return {"status": "error", "content": [{"text": f"❌ Archive failed: {e}"}]}


if __name__ == "__main__":
    import sys

    if "--init" in sys.argv:
        print(ensure_folders())
    else:
        print(archive_inspection_report())
