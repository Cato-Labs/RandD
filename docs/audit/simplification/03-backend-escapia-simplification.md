# Backend & Escapia — Simplification Audit

**Date:** 2026-07-06 · **Read-only** · Companion to skeptic reports [03](../03-escapia-integration.md), [04](../04-backend-api.md)

**Constraint:** Preserve all requirements, features, and experience. Internal simplification only.

---

## Executive Summary

`backend/app` is a feature-rich live-agent server with several **overlapping persistence/delivery paths** (report_db + kb_archive, Slack via multiple tools, Gmail plain + attachments) and a `_vendor.py` import-shadowing hack. `apps/api/escapia` is clean and well-tested but has **repeated pagination + cursor + request/response boilerplate** that can be table-driven. Neither needs feature changes; both can shed code.

---

## Incorporated Skeptic Findings

- Skeptic #3: Escapia auth/sync/write-back solid and tested; missing guest/inbound reads + custom Strands tool.
- Skeptic #4: `backend/app` is not the M6 API; runs meta-tooling agent; overlapping report persistence; no auth; local-disk photo storage.

Simplification lens: consolidate the overlapping paths that already exist rather than adding new ones.

---

## Backend Simplification Opportunities

| # | Opportunity | Safe because | Reduction | Risk |
|---|-------------|--------------|-----------|------|
| B1 | Unify report persistence: `report_db.upsert_form` and `kb_archive.archive_report` both consume the exported HTML/state; extract one `extract_state` + one persistence entrypoint | Same outputs (DB row + optional S3), one parse | ~30–50 LOC, one parser | Low |
| B2 | Single Slack path: `slack_report.send_report_to_slack` + native `slack`/`slack_send_message` both registered; keep `send_report_to_slack` for the form and native for arbitrary files, but remove any dead wrapper overlap | Same delivery behavior | small | Low-Med |
| B3 | Gmail: `gmail_send`, `gmail_reply`, `gmail_send_with_attachments` — the first two are subsumed by the attachments variant (attachments optional). Keep the superset, drop the thin duplicates if unused by prompt | Attachments tool with empty attachments == plain send | −~30 LOC | Med (prompt references) |
| B4 | Lazy-import heavy/optional deps (imageio_ffmpeg, slack_sdk, google libs) inside the functions that use them, not at module top, to speed cold `/ws` startup | Import timing only, no behavior change | faster startup | Low |
| B5 | `_vendor.py` shadowing: once `apps/agent` uses a proper Strands install (see report 05), the shadow hack can be deleted | Removes a fragile import-order dependency | −1 file, −fragility | Med (depends on SDK fix) |
| B6 | `transcribe.py`: Gemini-first then OpenAI fallback + loudness + compact re-encode. The compact MP4 re-encode via ffmpeg is the heaviest step; gate it behind a flag / only when needed for iOS embed | Same served output when needed; skips work when not | CPU/time | Med (verify iOS embed still works) |
| B7 | `main.py` `on_event("startup")` `os.chdir(WORKSPACE_DIR)` is a global-process side effect used so tools write relative paths; passing an explicit base dir to tools removes the chdir footgun | Same file locations if base dir passed | clarity | Med |

---

## Escapia Simplification Opportunities

| # | Opportunity | Safe because | Reduction | Risk |
|---|-------------|--------------|-----------|------|
| E1 | `endpoints.py` repeats "build params → client.request → parse typed model" per operation; a small `_call(op, params, model)` helper or a declarative op table removes per-endpoint boilerplate | Identical requests | ~40–80 LOC | Low-Med |
| E2 | `sync.py` repeats pagination loops (SearchUnitSummaries, SearchOwners) — extract one `paginate(search_fn, page_size)` generator | Same paging behavior | ~30 LOC | Low |
| E3 | Repeated `get_sync_cursor` / `upsert_sync_cursor` read-modify-write around each poll job — wrap in one `with_cursor(resource)` context manager | Same cursor semantics | ~20 LOC | Low |
| E4 | Priority/status enum mapping dicts (`LOW→Low`, statuses) are inline in `push_work_order`; hoist to module constants (also reusable by inbound read when added) | Same mapping | tiny, reuse | Low |
| E5 | `_UNIT_DEMOGRAPHIC_UPDATE` COALESCE SQL is long but correct; keep. Just ensure the field list is generated from one place if it grows | Same SQL | n/a | Low |

---

## Duplication to Eliminate (across backend + apps/api)

1. **Provider `build_model`** duplicated (`backend/app/agent.py` vs `apps/agent/assemble.py`) — see report 02 A1.
2. **Report state parsing** — `kb_archive.extract_state` vs `report_db` parsing (B1).
3. **Slack upload** logic exists in `backend/app/slack_report.py`, `backend/app` native `slack`, and `apps/agent/tools/slack_delivery.py` — three ways to upload a file (report 02 A3 + B2). Converge on the native tool.

---

## Dependency Reduction

- Audit `backend/requirements.txt` for packages pulled only by removed paths (e.g., if `qc_journal` hardcoded path goes, or if compact-encode is gated, `imageio_ffmpeg` may become optional).
- Lazy-imports (B4) reduce startup cost without removing capability.

---

## Estimated Net Reduction

- LOC: **~−200** (Escapia boilerplate ~−130 via E1–E4; backend persistence/Slack ~−80 via B1–B3).
- Files: **−1** (`_vendor.py`) contingent on SDK fix.
- Startup latency: reduced via lazy imports.

---

## Do Not Touch (would change behavior)

- Escapia auth flow, header injection, retry/backoff — correctness + tested.
- Delta-vs-poll cursor semantics — sync correctness.
- Report export endpoint contract (`/api/inspection/export`) and video endpoint — frontend depends on shapes.
- `run_in_threadpool` wrapping of blocking work — keeps event loop responsive.

---

## Prioritized Recommendations

1. **E1–E3** Escapia helper extraction (biggest clean, lowest risk, fully covered by existing tests).
2. **B1** unify report persistence parsing.
3. **A1/report-02** shared `build_model`.
4. **B4** lazy imports for faster `/ws` cold start.
5. **B2/A3** converge Slack upload on the native tool.
