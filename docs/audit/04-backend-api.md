# Backend API & Realtime Bridge Audit — 2026-07-06

## Executive Summary

The code under `backend/app/` is a **FastAPI + WebSocket live-agent server** ("RandD Live") rather than the M6 REST API service described in `TASKS.md`. It successfully implements a **real-time BIDI bridge** (`/ws`) that drives the vendored `BidiAgent` with browser microphone and camera streams, and it contains working domain tools for camera capture, checklist journaling, Slack delivery, Gmail attachments, transcription, and Bedrock-based memory. However, the M6 requirements for a **role-based REST/RPC API**, **object storage with signed URLs/thumbnails**, **AuthN/Z**, **offline sync endpoints**, and a **performance budget** are either absent or only partially present in this subtree. The actual v1 API service (`apps/api/src/strqc_api/`) and the STR QC agent (`apps/agent/src/strqc_agent/`) live outside `backend/app/`; the relationship between them and the meta-tooling agent in `backend/app/` is the most important architectural finding.

**Import check result:** `from app.main import app` succeeds when run inside `backend/venv` with `GOOGLE_API_KEY=dummy`, but fails with a fresh `python3` because `strands_google` is not installed globally. No tests exist under `backend/app/` or `backend/tests/`; tests are located in `apps/agent/tests/` and `apps/api/tests/`.

---

## 1. API Endpoints Audit

| Endpoint | File | Purpose | M6 Mapping | Status |
|---|---|---|---|---|
| `GET /api/agent` | `backend/app/main.py:180` | Returns agent name, model, instructions, tool list | Meta/debug only | ✅ Present |
| `GET /api/models` | `backend/app/main.py:190` | Vended BIDI providers (`gemini`, `openai`, `nova`) | Model picker | ✅ Present |
| `GET /api/voices` | `backend/app/main.py:210` | Voices per provider | Model picker | ✅ Present |
| `GET /api/workspace` | `backend/app/main.py:215` | Lists files in `backend/workspace` | Static file index | ✅ Present |
| `POST /api/inspection/video` | `backend/app/main.py:41` | Receives browser-recorded walkthrough clip | Media upload | ✅ Present |
| `POST /api/inspection/export` | `backend/app/main.py:92` | Receives self-contained HTML report snapshot | Report persistence | ✅ Present |
| `/ws` | `backend/app/main.py:225` | WebSocket BIDI bridge | M6.2 | ✅ Present |
| REST endpoints for properties, tasks, inspections, work orders, reports, routes | — | — | **M6.1** | ❌ Not implemented in `backend/app/` |
| Auth endpoints (login, session, scopes) | — | — | **M6.4** | ❌ Not implemented in `backend/app/` |
| Offline sync endpoints | — | — | **M6.5** | ❌ Not implemented in `backend/app/` |

The `backend/app/main.py` service exposes only **agent-lifecycle and media-upload endpoints**. It does not implement the M6.1 REST/RPC service over the repositories in `packages/db/src/strqc_db/`. That API service appears to be intended for `apps/api/src/strqc_api/`, which currently only contains the Escapia integration (`apps/api/src/strqc_api/escapia/`).

### Observations

- `CORS` is configured with `allow_origins=["*"]` (`backend/app/main.py:27`), which is acceptable for local dev but a security risk in production.
- There is no middleware for authentication, authorization, rate limiting, or request logging.
- Static files are served from `backend/workspace` at `/workspace/*`; this is a local-filesystem store, not object storage with signed URLs.

---

## 2. WebSocket BIDI Bridge Audit

### Implementation

The bridge is implemented in:

- `backend/app/main.py:225` — `websocket_endpoint` accepts `/ws`, creates `BidiAgent` via `create_agent`, and runs it with `BidiWebSocketInput`/`BidiWebSocketOutput`.
- `backend/app/io.py` — Adapts browser WebSocket frames to the vendored `BidiInput`/`BidiOutput` protocols.
- `backend/app/agent.py` — Builds the vendored `BidiAgent` model (Gemini, OpenAI, Nova) and registers tools.
- `backend/app/_vendor.py` — Shadows `strands.experimental.bidi` with the repo-vendored copy under `strands-py/src/strands/experimental/bidi`.

### Audio Formats

- **Input rate:** `BROWSER_MIC_RATE = 16000` (`backend/app/agent.py:41`). The frontend is expected to stream PCM16 at 16 kHz. The model configs pass `input_rate=16000` for every provider. This matches the requirement for "audio in 16 kHz PCM."
- **Output rate:** Left at each model's native rate (`backend/app/agent.py:119-122`). The frontend plays back at whatever `sample_rate` the model stamps on `bidi_audio_stream`. OpenAI Realtime defaults to 24 kHz, so "audio out 24 kHz PCM" is satisfied for OpenAI; Gemini Live and Nova Sonic may use different native output rates. The comment in `backend/app/agent.py:120` explicitly states this is intentional.

### Events

`BidiWebSocketInput` (`backend/app/io.py:52`) accepts three frame types:

- `bidi_text_input` → `BidiTextInputEvent`
- `bidi_audio_input` → `BidiAudioInputEvent`
- `bidi_image_input` → `BidiImageInputEvent` (also tee'd to `browser_camera.add_frame` for server-side capture)

`BidiWebSocketOutput` (`backend/app/io.py:91`) forwards:

- All vendored `BidiOutputEvent`s as JSON.
- Enriches `tool_result` events with `tool_name`/`tool_input` from the prior `tool_use_stream` (`backend/app/io.py:94-107`).
- Normalizes `bidi_usage` token fields (`backend/app/io.py:109-112`).

### Camera Control

Camera flow:

1. Agent calls `control_camera(action)` (`backend/app/camera_control.py:15`) — action is one of `start`, `stop`, `snap`, `flip`.
2. Frontend receives the tool call and starts `getUserMedia`.
3. Browser streams JPEG frames as `bidi_image_input` events.
4. `backend/app/io.py:68-69` tee's frames into `browser_camera.add_frame`.
5. `take_photo`/`take_video` (`backend/app/capture_tools.py`) capture from `browser_camera.latest_frame()`.
6. Server-attached camera fallback exists in `take_photo`/`take_video` and `backend/app/take_video.py`.

### Tool Routing

The agent is created with a fixed `TOOLS` list plus `memory_tools()` (`backend/app/agent.py:73-111`). Tools are routed by the vendored `BidiAgent.run` harness, not by a custom bridge. The bridge simply passes events through.

### Interruption

Interruption is handled by the vendored model/harness (e.g., Gemini Live's native turn-taking and the `stop_all` lifecycle in `BidiAgent.run`). The local code does not implement its own interruption logic.

### M6.2 Status

The WebSocket bridge itself is **implemented and functional** for audio, image, transcript, and tool events. The gap is that the **agent currently wired to the bridge is the meta-tooling agent**, not the STR QC agent (`apps/agent/src/strqc_agent/`). The audio-output rate requirement is met for OpenAI but not explicitly forced to 24 kHz for all providers.

---

## 3. Domain Services Audit

### 3.1 Camera / Photo Capture

- `control_camera` (`backend/app/camera_control.py`) — browser camera control only; no actual hardware access.
- `take_photo` / `take_video` (`backend/app/capture_tools.py`) — capture from browser stream, with server webcam fallback. Photos are saved as JPEGs to the current working directory (`backend/workspace` because `startup()` chdirs there). Walkthrough clips are uploaded to `/api/inspection/video` and transcribed.
- `browser_camera` (`backend/app/browser_camera.py`) — ring buffer of ~600 frames, clip mailbox for `take_video`.
- `vision_tools` (`backend/app/vision_tools.py`) — runs YOLOv8n over the browser stream; continuous monitoring mode available.

**Gap vs. M6.3:** Photos are stored on **local disk** and served as static files (`/workspace/captures/*`). There is no object storage, no signed URLs, no thumbnails, and no `photo_memory` integration in this subtree. The `apps/agent/src/strqc_agent/tools/camera.py` does write to `photo_memory` via `strqc_db.repositories.add_photo`, but that code is not wired into the live backend.

### 3.2 Journal / Checklist

- `backend/app/qc_journal.py` defines a **hardcoded** `CHECKLIST_ITEMS` dictionary matching the live HTML form. It exposes `list_checklist_items`, `record_checklist_result`, `record_section_note`, and `attach_item_photo`.
- The tools return confirmation strings; they do **not** write to the operational database (`packages/db/src/strqc_db/`). The live form state is instead persisted through the HTML export to `backend/app/report_db.py` (`inspection_reports` SQLite table).
- `apps/agent/src/strqc_agent/tools/journal.py` is the database-backed version: it writes `inspection_item_result` rows and lazily starts an `inspection`.

**Gap:** The backend is using a hardcoded, form-driven journal rather than the DB-backed template engine required by M5.1.

### 3.3 Report / Slack Delivery

- `backend/app/slack_report.py` — custom `send_report_to_slack` tool that resolves `reports/inspection-report-latest.html` and uploads via `slack_sdk.WebClient.files_upload_v2`.
- `backend/app/gmail_attachments.py` — `gmail_send_with_attachments` builds a multipart MIME message and sends via `strands_google.use_google`.
- `backend/app/kb_archive.py` — archives signed-off reports to a Bedrock KB S3 bucket and writes site memories.
- `backend/app/report_db.py` — upserts every HTML export into `inspection_reports` keyed by `formId`.

**Gap vs. M5.5/M5.6:** Report delivery is **manual/agent-driven**; there is no automatic "on sign-off" dispatch that updates `Report.delivery_status`. The swappable adapter pattern exists in `apps/agent/src/strqc_agent/tools/slack_delivery.py` but is **not used** by the backend's `send_report_to_slack` tool.

### 3.4 Memory

- `backend/app/memory.py` — configures a `BedrockKnowledgeBaseStore` via `strands.memory.MemoryManager`. The manager's `search_memory`/`add_memory` tools are registered on the BIDI agent.
- Configuration is environment-driven (`BEDROCK_KB_ID`, `BEDROCK_KB_DATA_SOURCE_ID`, `BEDROCK_KB_S3_BUCKET`).

### 3.5 Vision

- `yolo_vision` (`backend/app/vision_tools.py`) — generic COCO-class object detection over the browser stream. This is **not** the photo-reasoning requirement in M3.3; the actual QC reasoning is expected to come from the multimodal model (per `AGENTS.md` Addendum 1). YOLO is used as a supplementary walkthrough monitor.

### 3.6 Transcription

- `backend/app/transcribe.py` — transcribes uploaded walkthrough clips. First tries Gemini (`GOOGLE_API_KEY`), then falls back to OpenAI Realtime WebSocket (`gpt-realtime-2`) at 24 kHz PCM. Includes loudness measurement and compact MP4 re-encoding via `imageio_ffmpeg`.

---

## 4. Auth Status

**AuthN/Z is completely absent from `backend/app/`.**

- No login, session, JWT, OAuth, or role-scoped middleware.
- `CORS` allows all origins (`backend/app/main.py:29`).
- `/ws` and `/api/*` are open to any WebSocket/HTTP client.
- There is no mapping of users to stakeholders.
- The only credential handling is `backend/app/slack_token.py` (rotating Slack bot token) and the Google/AWS API keys used by the Strands libraries.

**M6.4 status:** Not implemented in `backend/app/`.

---

## 5. Offline Sync Status

**M6.5 is not implemented in `backend/app/`.**

There are no endpoints to accept queued checklist updates, photo captures, or task progress from a PWA service worker. The backend assumes a live WebSocket connection. The frontend HTML form is self-contained and could theoretically be filled offline, but there is no reconciliation endpoint.

---

## 6. Performance / Reliability Observations

### Performance Budget (M6.6)

- No explicit 2–3 second performance budget or latency instrumentation in `backend/app/`.
- The transcription pipeline (`transcribe_audio`) can take multiple seconds (Gemini round-trip or OpenAI Realtime WebSocket), but it runs in `run_in_threadpool` so it does not block the event loop.
- Photo capture from the browser stream is near-instant once frames are flowing.
- Report export is synchronous and writes the entire HTML blob to disk; large reports could exceed the budget.

### Reliability

- `report_db.py` and `kb_archive.py` swallow exceptions with `except Exception: return None` to avoid breaking the export path. This is a reasonable graceful-degradation pattern but could mask failures.
- The browser camera ring buffer is single-process only (`backend/app/browser_camera.py:10`). No multi-worker or Redis-backed queue.
- No retry/backoff logic in the backend itself (the Strands libraries handle model retries).

---

## 7. Two-Agent Architecture Clarification

There are indeed two distinct BIDI agent implementations:

### 7.1 `backend/app/agent.py` — "RandD Live" Meta-Tooling Agent

- **Persona:** `backend/app/prompts.py` — generic "RandD Live" voice/text assistant focused on **creating Strands tools**, running shell commands, editing files, loading libraries, and meta-tooling. It also contains a large QC section because the same prompt is reused for STR inspections.
- **Tools:** `editor`, `shell`, `load_tool`, `http_request`, Google tools, `strands_tools.slack`, `take_photo`, `take_video`, `qc_journal`, `send_report_to_slack`, etc.
- **Wiring:** Directly mounted on `/ws` in `backend/app/main.py`.
- **Purpose:** A general-purpose live coding/agent assistant that happens to include STR QC tools.

### 7.2 `apps/agent/src/strqc_agent/` — "the Keeper" STR QC Field Companion

- **Persona:** `apps/agent/src/strqc_agent/persona.py` — "the Keeper", a seasoned head of housekeeping for Big Bear cabins. Safety-first, checklist-disciplined, plain-spoken.
- **Tools:** Database-backed journal, camera (with `CaptureBackend` protocol), stage advancement, work orders, property brief, Slack delivery adapter, guardrails.
- **Wiring:** `console.py` provides a text-mode harness; `assemble.py` builds the agent with injected context.
- **Purpose:** The v1 STR QC product agent per `TASKS.md` M2/M3.

### Relationship

- The two agents are **separate codebases** sharing the same vendored BIDI harness (`strands-py/src/strands/experimental/bidi`).
- `backend/app/agent.py` is **not** a thin wrapper around `apps/agent/src/strqc_agent`. It builds its own `BidiAgent` with its own tool list and prompt.
- The STR QC agent is currently **not connected to the WebSocket bridge** in `backend/app/main.py`. To satisfy M6/M7, `backend/app/main.py` should either import `strqc_agent.build_agent` and use it for `/ws`, or the production bridge should be moved to `apps/api/`.
- The tools in the two agents overlap conceptually (camera, journal, Slack) but have different implementations: backend uses hardcoded checklists and local files; `strqc_agent` uses `strqc_db` repositories and swappable adapters.

---

## 8. Risks and Recommendations

| Risk | Severity | Recommendation |
|---|---|---|
| `backend/app/` is the wrong home for the v1 API service | **High** | Move M6 REST/RPC, AuthN/Z, and offline sync to `apps/api/src/strqc_api/`. Keep `backend/app/` as a research/dev live-agent server, or replace its `/ws` agent with `strqc_agent.build_agent`. |
| Two agents with overlapping but incompatible tools | **High** | Decide on a single agent architecture for production. Either merge `strqc_agent` tools into the backend, or have the backend bridge instantiate the `strqc_agent` agent. |
| No authentication or authorization | **High** | Implement M6.4 before any production deployment. At minimum, gate `/ws` and `/api/*` behind a session/token and role scopes. |
| Local filesystem photo storage | **High** | Replace with object storage (S3/R2), signed URLs, and thumbnails to meet M6.3. The `strqc_agent` `CaptureBackend` protocol is the right seam. |
| CORS `allow_origins=["*"]` | **Medium** | Restrict to known origins in production. |
| Hardcoded checklist in `qc_journal.py` | **Medium** | Use the DB-backed `checklist_items` repository from `packages/db/src/strqc_db/repositories.py` so the same templates drive the agent and the form. |
| No backend tests | **Medium** | Add tests under `backend/tests/` or `apps/api/tests/` for the bridge, media endpoints, and tool outcomes. |
| No offline sync | **Medium** | Implement M6.5 sync endpoints in `apps/api/`. |
| No performance instrumentation | **Low** | Add timing middleware/metrics for task-list, photo-analysis, and report-generation endpoints. |
| `strands_google` missing outside venv | **Low** | Document that the backend must run inside `backend/venv`; the README already does this. |
| OpenAI output rate not forced to 24 kHz | **Low** | If M6.2 strictly requires 24 kHz output for all providers, add a resampler or constrain provider selection to OpenAI. |

---

## 9. Requirement Mapping Checklist

### M6.1 — API service (REST/RPC over repositories, role-based authz)

- [ ] REST endpoints for properties, tasks, inspections, work orders, reports, routes
- [ ] Uses `strqc_db` repositories
- [ ] Role-based authorization scopes
- [ ] Mapped to `backend/app/main.py` endpoints? **No** — only agent/media endpoints exist.

### M6.2 — Realtime BIDI bridge

- [x] WebSocket endpoint `/ws` exists (`backend/app/main.py:225`)
- [x] Browser mic/camera ⇄ Python agent (`backend/app/io.py`, `backend/app/browser_camera.py`)
- [x] Audio input at 16 kHz PCM (`backend/app/agent.py:41`)
- [~] Audio output at 24 kHz PCM — true for OpenAI, native for others
- [x] Transcript events forwarded (`backend/app/io.py`)
- [x] Tool events forwarded and enriched (`backend/app/io.py:94-112`)
- [~] Interruption handled by vendored harness, not local code
- [ ] Bridge wired to the STR QC agent (`apps/agent/src/strqc_agent`) — **not done**

### M6.3 — Photo storage

- [ ] Object storage backend
- [ ] Signed URLs
- [ ] Thumbnails
- [ ] Linked to `photo_memory` table in `strqc_db`
- [x] Local files served at `/workspace/captures/*` (`backend/app/main.py:34`)
- [ ] M6.3 not satisfied in `backend/app/`.

### M6.4 — AuthN/Z

- [ ] Login endpoint
- [ ] Session/token mechanism
- [ ] Per-role scopes
- [ ] User → stakeholder mapping
- [ ] Middleware on `/api/*` and `/ws`
- [ ] Not implemented in `backend/app/`.

### M6.5 — Offline sync endpoints

- [ ] Accept queued checklist updates
- [ ] Accept queued photo captures
- [ ] Reconcile on reconnect
- [ ] Not implemented in `backend/app/`.

### M6.6 — Performance budget

- [ ] Instrumented response times
- [ ] <2–3 s for task-list + photo-analysis
- [ ] Not implemented in `backend/app/`.

### M3 Tool Requirements (in `backend/app/` context)

- [x] Camera tool (`control_camera`, `take_photo`, `take_video`) — browser-stream only, no DB linkage
- [x] Journal tool (`qc_journal.py`) — hardcoded items, no DB linkage
- [~] Slack delivery (`slack_report.py`) — works but not the swappable adapter required by M3.6
- [x] Google tools (`strands_google` via `use_google`, `gmail_send`, etc.)
- [x] Email tool (`gmail_attachments.py`)
- [ ] Telephony tool — not implemented
- [ ] Tool-permission matrix by role — not implemented

---

## 10. Files Cited

- `backend/app/main.py` — FastAPI app, `/ws`, media endpoints, static files.
- `backend/app/agent.py` — BIDI agent builder and provider config.
- `backend/app/io.py` — WebSocket ↔ BIDI event adapters.
- `backend/app/prompts.py` — System prompt for the meta-tooling agent.
- `backend/app/camera_control.py` — Browser camera control tool.
- `backend/app/capture_tools.py` — `take_photo`/`take_video` from browser stream.
- `backend/app/browser_camera.py` — Frame ring buffer and clip mailbox.
- `backend/app/qc_journal.py` — Hardcoded checklist journal tools.
- `backend/app/slack_report.py` — Slack file upload tool.
- `backend/app/gmail_attachments.py` — Gmail with attachments.
- `backend/app/memory.py` — Bedrock KB memory configuration.
- `backend/app/transcribe.py` — Walkthrough clip transcription.
- `backend/app/vision_tools.py` — YOLO over browser stream.
- `backend/app/report_db.py` — SQLite export persistence.
- `backend/app/kb_archive.py` — S3 archive for reports and site memories.
- `backend/app/take_video.py` — Server-side camera video recording.
- `backend/app/_vendor.py` — Vendored BIDI harness shadowing.
- `apps/agent/src/strqc_agent/assemble.py` — STR QC agent builder.
- `apps/agent/src/strqc_agent/persona.py` — "the Keeper" system prompt.
- `apps/agent/src/strqc_agent/tools/` — DB-backed QC tools.
- `packages/db/src/strqc_db/repositories.py` — Repository layer.
- `apps/api/src/strqc_api/escapia/` — Escapia PMS integration (external to `backend/app/`).
- `TASKS.md` — M2–M6 requirements.
- `AGENTS.md` — PRD requirements including Addenda 1 & 2.
