# Vantage AI v1 Gap Analysis

**Audited:** 2026-07-10  
**PR:** #5, `main` <- `claude/multi-tenancy-auth-frontend-a2620e`  
**Head reviewed:** `11b32f3`  
**Runtime of record:** `backend/` FastAPI + `frontend/` React/Vite

The linked Claude Code session was not accessible during the audit. This report uses the repository, branch history, PR discussion, database schema, and executable code as evidence.

## Executive finding

PR #5 provides a strong mobile visual prototype and additive read-only field endpoints. It does **not** provide production authentication, organization tenancy, persisted onboarding, room/asset inventory, durable offline sync, original-evidence storage, or a functioning asynchronous human-approval protocol. The `apps/*` and `packages/*` tree contains useful tested domain and Escapia code, but it is not the deployed runtime and must be selectively ported rather than activated wholesale.

## Requirement matrix

| Requirement | Status | Current evidence | Required change | Main risk |
|---|---|---|---|---|
| PR #5 mobile shell and brand | Partial | `frontend/src/views/mobile/*`, `frontend/src/index.css` | Preserve useful components; replace seeded/demo navigation with complete product IA | Overwriting prior-agent work during branch reconciliation |
| Live field reads | Partial | `backend/app/field_api.py` and `/api/field/*` | Add auth, organization scoping, errors, and write APIs | Current helpers swallow DB errors and return empty data |
| Authentication | Conflicting | PR #5 localStorage email/code stub; separate branch uses passwords | Implement real email magic codes, secure cookie sessions, active organization, WS token | Replay/brute force and session fixation |
| Multi-tenancy | Partial | PR #5 calls cluster a workspace; separate branch has one tenant per user | Organization -> Portfolio -> Home, multi-org memberships, RLS, owner-home grants | Cross-tenant SQL, media, memory, or agent leakage |
| Canonical checklist | Complete source, partial execution | `backend/app/qc_journal.py`: 8 section keys, 38 exact items | Persist PASS/FAIL/NA and room-oriented execution | Existing HTML form stores only checked boolean |
| Blank onboarding assessment | Missing | No onboarding inspection type or API | Home-linked draft inspection with no pre-created room instances | Temporary UI data could diverge from inventory |
| Rooms and room types | Missing | No live room model | Extensible room type catalog; create/update/order/archive rooms | Unsafe historical inference from House Keeping sections |
| Assets/appliances | Missing | No live asset workflow | Draft/complete asset model, moves, duplicates, optional enrichment | Optional metadata accidentally blocking save |
| Original asset photos | Missing | Browser preview JPEG and report-compressed copies only | Full-resolution immutable original, hash, signed access, derivatives | Current pipeline downsamples evidence |
| Autosave and resume | Missing | QC offline conductor is timed in-memory simulation | Stable client IDs, idempotency keys, IndexedDB queue, batch sync | Duplicate rooms/assets after retry |
| Agent walkthrough tools | Missing/partial | Camera and journal tools exist; DB tools absent | Tenant-bound structured room/asset/progress/research tools | Model-supplied IDs bypassing authorization |
| Human approval | Conflicting | UI sends normal text; native handoff waits on server stdin | Correlated async approval event and session-local future | Wrong session could resolve approval |
| Session isolation | Missing | Global camera ring buffer, clip mailbox, latest report path | Session/org/home scoped registries and artifacts | Cross-session media leakage |
| Reports and delivery | Partial | Self-contained HTML, Slack and Gmail tools | Report-specific artifacts, owner redaction, delivery status/retry | Absolute paths and shared report expose tenant data |
| Video MP4 | Partial | Transcode exists with raw fallback | Durable retry/status/error pipeline | False success and unplayable files |
| Bedrock memory | Partial | Shared store and model-selected property prefix | Server-derived org/portfolio/home namespace and filters | Cross-tenant retrieval |
| Escapia read integration | Partial in unused tree | `apps/api/src/strqc_api/escapia/*` | Port typed auth/client/read operations into live backend | Accidentally enabling existing write methods in v1 |
| Work orders | Partial schema/tools | Existing phase-1 tables and agent tools | Tenant scope, inspection/asset linkage, persisted UI | Split state across old/new implementations |
| Historical compatibility | Partial | 51 legacy inspection reports and phase-1 schema | Preserve read-only history; do not fabricate rooms | Data loss during migration |
| Tests | Partial | Package-tree tests; little canonical backend coverage | Auth, RLS, onboarding, media, agent, offline, E2E tests | Green unused tests misrepresent production readiness |
| Accessibility/mobile | Partial | Focus ring and responsive prototype | Full state/a11y validation on phone/tablet flows | Camera/offline states inaccessible |

## Confirmed architecture decisions

- `backend/` and `frontend/` remain the runtime of record.
- Organization is the tenant boundary; portfolio and cluster are subordinate groupings.
- PostgreSQL is the production database and enforces RLS; SQLite is a migration source and local compatibility fixture.
- Original evidence is stored separately from previews and derivatives.
- Rooms/assets created during onboarding are normal inventory records immediately, linked back to the creating inspection.
- Historical House Keeping results remain legacy data unless a human reviews a proposed room mapping.
- Escapia is read-only in v1.

