# PROMPT — Build "Basecamp": the STR QC field & ops frontend

You are building the frontend for a short-term-rental quality-control platform running in Big Bear Lake, CA. The backend, database, live voice agent, and integrations already exist and work — your job is to wrap them in an innovative, fun, high-end experience that a housekeeper in a moving truck and an owner on a beach can both use without a manual. Intuitiveness is non-negotiable: every innovation below must reduce taps, not add ceremony.

## 1. The world you're building for

A property-management crew turns over ~96 mountain cabins between guests. Stakeholders: **Owner, Housekeeper, Facilities/Maintenance, QC Inspector, Property Manager, Office/Dispatch** — all with different questions ("is my house ready?" vs "what's my route today?"). The heartbeat is the daily turnover board; the soul is the on-site inspection, done by voice with a live AI agent that sees through the inspector's phone camera.

## 2. Existing stack & runtime (do not replace, extend)

- **Frontend**: Vite + React 19 + TypeScript, Tailwind v4, Radix UI, `motion` (animations), `lucide-react`, `streamdown` (agent markdown), `@xyflow/react` (canvas), `@rive-app/react-webgl2` (persona animation), `use-stick-to-bottom`. Voice session plumbing lives in `src/hooks/use-live-agent.ts` (WebSocket to the agent, mic PCM up / audio down, tool events, camera streaming) and `src/lib/audio.ts` / `src/lib/camera.ts`.
- **Backend (FastAPI, port 8000)**:
  - `GET /api/models`, `GET /api/voices?provider=`, `GET /api/agent` (agent card: name, instructions, 25 tools)
  - `WS /ws?mode=audio|text&voice=&provider=gemini|openai|nova` — bidi agent session (Gemini Live is primary). Events: `bidi_connection_start`, `bidi_response_start/complete`, `bidi_transcript_stream`, `bidi_audio_stream` (pcm16 24 kHz), `bidi_interruption`, `tool_use_stream`, `tool_result`, `bidi_usage`, `bidi_error`.
  - `POST /api/inspection/export` — the form posts its full self-contained HTML on every change; response includes `form_uuid`. Signed-off forms auto-archive to S3.
  - `POST /api/inspection/video?section=&duration=` — walkthrough clip upload; response includes `transcript`, `audio_ok`, `audio_max_db`, compact `-web.mp4` URL.
  - `GET /api/workspace` + static `/workspace/*` (captures, reports).
- **The inspection form** is a self-contained interactive HTML (`frontend/public/inspection.html`) with state in `window.__QC_STATE__` (each form has a stable `formId` UUID + `createdUtc`). Keep it embeddable and exportable; you may re-skin it, never break its self-containment.
- **Agent tools the UI must surface**: control_camera, take_photo, take_video, yolo_vision, list_checklist_items, record_checklist_result, record_section_note, attach_item_photo, archive_inspection_report, save_site_memory, search_memory, slack, slack_send_message, gmail_send, gmail_reply, gmail_send_with_attachments, use_google, google_auth, http_request, environment, editor, shell, load_tool, list_library_tools, mcp_client.

## 3. The data model (sqlite `str_qc.sqlite` — build a thin read API or use existing endpoints; schema in `sql/phase1_schema.sql` + `sql/inspection_reports.sql`)

**House (`property`) is the hub object.** Everything radiates from it:

- `property`: `unit_code` (e.g. LBV — the universal handle), `display_name` ("Lakefront Bay View"), `address_line_1/city/state/postal`, `wifi_ssid`, `wifi_password_ciphertext`, `door_code_ciphertext` (AES-256-GCM; UI shows masked value + reveal-on-tap that calls a decrypt endpoint — plaintext is never bundled), `qc_assignee_stakeholder_id`, `standing_instructions` (e.g. "DO NOT PLOW. OWNER WANTS SNOW BLOWER" — these are safety-critical callouts, make them loud), `cluster_id`, `roster_active`.
- `cluster`: 11 geo areas (Boulder Bay, Metcalf Bay, Gibraltar Point/Lagonita Point, Village, Foxfarm/Winter, Lower/Upper Moonridge, Airport, Shay Meadows, Sugarloaf, Fawnskin) — the natural map/route grouping.
- `property_feature` + `property_feature_type`: HAS_HOT_TUB, TV, EV_CHARGER, BEDROOM, BATHROOM, PATIO… with quantities.
- `stakeholder`, `role` (OWNER, HOUSEKEEPER, FACILITIES, QC_INSPECTOR, PROPERTY_MANAGER, OFFICE_DISPATCH), `stakeholder_role` (per-house assignments). Current staff: Maribel, Gabriella, Bertha, Liz n Leo (housekeepers), Dan (QC).
- `task` (the daily board row): property, `arrival_date`, assigned housekeeper; `task_stage_event` per stage: **QC → B2B → CLN → DONE → OWN → WO → DONE_WO → REPORT** (`stage_definition` has display order). 65 live tasks today.
- `checklist_template/category/item_template`: the Master checklist (Hot Tub; Housekeeping: Kitchen/Bathrooms/Bedroom/Home; Outdoors; Utilities; Gifts; sign-off "Ready for guests"; Repairs Needed).
- `inspection`, `inspection_item_result` (PASS/FAIL/NA + photo + notes), `photo_memory`.
- `inspection_reports` (live form tracking): `form_uuid` PK, `created_utc`, `updated_utc` (updates on every keystroke-level export), `property`, `signed_off`, `items_done/items_total`, `sections`, `repairs`, `state_json`, `archived_utc`, `s3_summary_uri`, `s3_artifact_uri`.
- **Per-house S3 knowledge base** (bucket `strands-kb1`): `memories/<house>/inspections/`, `memories/<house>/notes/` (site memories), `artifacts/<house>/inspections/` (full interactive report HTMLs). The agent recalls these via `search_memory`.

## 4. The experience — screens & signature moves

### A. "Today" — the mission board (default screen)
The daily turnover board reimagined. Not a spreadsheet: a **column of house cards grouped by geo cluster**, each card showing unit code monogram, arrival countdown ("guests in 4h"), housekeeper avatar chip, and the 8-stage progress as a **summit trail**: a mountain-profile micro-visualization where each stage is a trail marker that lights as it completes (this is Big Bear — lean into the alpine identity). Tap a stage marker to toggle it (optimistic update, undo snackbar). Filters: by housekeeper, by cluster, "arriving today", "blocked" (WO open). A header stat strip: houses ready / in progress / blocked, with a gentle sunrise-to-sunset gradient that tracks the actual time of day.

### B. "Route" — the driving day
For a chosen housekeeper/QC + date: their tasks ordered into a route, rendered on a map (Google Maps JS or static tiles + deep links) with numbered pins colored by cluster. One tap on a pin = house card sheet: address (tap = open native navigation), door code (masked → biometric/hold-to-reveal), wifi, standing instructions in a red-bordered callout, features (hot-tub icon row). "Start my day" enters a **focus flow**: full-screen current stop, big "Navigate" and "Begin inspection" buttons, swipe to advance. The agent can be summoned here by voice to reorder stops ("skip LBV, guests late").

### C. "Inspect" — the live agent console (the crown jewel)
The existing voice console, elevated. Layout: camera viewfinder center-stage; the **Rive persona** (listening/thinking/speaking states already computed in `use-live-agent`) floats as a companion orb, not a chat header. The checklist rides as a bottom sheet with the Master categories as horizontally-scrollable chips; items check themselves in real time as the agent calls `record_checklist_result` — animate each with a satisfying stamp effect + haptic. Tool activity renders as a subtle "the agent is doing X" ticker (streamdown for results), never a wall of JSON. Walkthrough recording (take_video) shows a red rec ring around the viewfinder with live elapsed time; when the clip returns, surface `audio_ok` immediately — if the mic was dead, a "no narration captured — re-shoot?" toast (this was a real field failure; make it impossible to miss). Sign-off is ceremonial: a full-screen "Ready for guests" moment with the house's stats (items passed, photos, clips, duration) and a single thumb-press-and-hold to sign — then confetti of pine needles, archive to S3 fires, Slack/email delivery offered as two big buttons.

### D. "House" — the property dossier
One page per house = the object graph made visible. Hero: display name, unit code, cluster badge, feature icons with counts. Tabs: **Timeline** (inspection_reports rows + S3 artifacts — open past interactive reports in-app), **People** (stakeholder_role assignments with roles), **Memory** (site notes from `memories/<house>/notes/` + a "Tell the agent something about this house" input that calls save_site_memory), **Access** (encrypted credentials with reveal flow), **Repairs** (open WO stages + repairs text from forms). A small "ask about this house" voice button scopes an agent session to it (search_memory pre-seeded).

### E. "Reports" — for PM/Owner eyes
Signed-off inspections as a browsable gallery: cover = first photo, badges for pass-rate and repairs. Open = the actual self-contained interactive form, embedded. Share = gmail_send_with_attachments / Slack upload, driven by the agent with one confirmation.

## 5. Design system

- **Identity**: "alpine premium" — deep pine greens, granite neutrals, snow whites, one warm amber accent (trail-marker orange) for progress and CTAs. Light and dark themes; dark defaults after sunset local time.
- **Type**: a confident grotesque for numbers/codes (unit codes are the brand — treat LBV/COOKIE/EAGLE as monograms), humanist sans for body.
- **Motion**: `motion` spring transitions; every state change animates from its cause (stage marker lights travel along the trail; cards reorder with FLIP). 60fps on mid-range Android; respect `prefers-reduced-motion`.
- **Touch-first**: min 44px targets, bottom-sheet patterns, one-handed reach for all primary actions; the whole inspect flow must work with gloves via voice alone.
- **Offline-graceful**: cache today's board + house dossiers (localStorage/IndexedDB); queue stage toggles when signal drops in the mountains; badge stale data honestly.

## 6. Non-negotiables

1. Voice session stability features stay intact: don't touch the PCM pipeline contracts (16 kHz mic up in 512-sample chunks, 24 kHz down), reconnect UX on `bidi_connection_restart`, camera frame streaming.
2. Secrets: never render decrypted codes without an explicit user gesture; never log them; masked by default everywhere including screenshots of cards.
3. The inspection form remains a self-contained exportable HTML artifact — whatever skin you apply must survive `exportHtml()` round-tripping.
4. `form_uuid` is the join key across UI, DB, and S3 — surface it subtly (footer of reports) for support/debugging.
5. Standing instructions with owner warnings (snow/plow notes) must appear before navigation starts, not buried in a tab.
6. Every list renders from real endpoints/DB — no mock data in the shipped build.

## 7. Deliverables & acceptance

- React app organized by feature (`src/features/today|route|inspect|house|reports`), shared UI kit in `src/components/ui`.
- A thin typed data layer (`src/lib/api.ts`) with all endpoint contracts above; add read endpoints to the FastAPI backend where the sqlite data isn't yet exposed (`/api/houses`, `/api/board?date=`, `/api/houses/{code}/timeline`, `/api/houses/{code}/reveal-secret` with audit logging).
- Lighthouse mobile ≥ 90 performance/accessibility; typecheck clean; the five screens navigable end-to-end against the live backend.
- Demo script: open Today → filter to Bertha → start Route → arrive LBV → run a voice inspection with camera, record a walkthrough, sign off → see it in Reports and the House timeline → share to Slack.

Build it so the crew *wants* to open it at 7am. Fun earns its place only where it makes the job faster.
