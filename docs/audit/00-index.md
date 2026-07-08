# STR QC Platform — Codebase Audit Index

**Audit date:** 2026-07-06  
**Scope:** Full codebase audit against `AGENTS.md` (PRD incl. Addenda 1 & 2) and `TASKS.md` milestones M0–M8.  
**Method:** Read-only review by parallel subagents, one per architectural area; verification via targeted test/build runs.  
**Status:** No code files were modified. Audit artifacts live under `docs/audit/`.

---

## Audit Reports

| # | Report | Focus | Key Verdict |
|---|--------|-------|-------------|
| 1 | [Database Schema & Migrations](01-database-schema.md) | `packages/db` schema, migrations, repositories | Schema + Addendum 1/2 fields are present; repository layer incomplete; encryption not enforced |
| 2 | [Agent Core & Tools](02-agent-tools.md) | `apps/agent` BIDI agent, persona, tools, guardrails | Agent assembles cleanly; missing memory, telemetry, Google/email/telephony, role permissions |
| 3 | [Escapia PMS Integration](03-escapia-integration.md) | `apps/api/escapia` client, sync, scheduler | Auth/client + delta/poll sync + write-back are solid; missing guest sync, inbound work orders, custom Strands tool |
| 4 | [Backend API & Realtime Bridge](04-backend-api.md) | `backend/app` FastAPI + `/ws` BIDI bridge | Bridge works, but is meta-tooling agent, not STR QC agent; no REST API, auth, offline sync, object storage |
| 5 | [Frontend & Voice Console](05-frontend.md) | `frontend/` Vite demo + `apps/web/` Next.js | Vite demo proves BIDI tech; Next.js PWA product shell is essentially empty |
| 6 | [Shared Packages & Security](06-shared-security.md) | `packages/shared`, config, crypto, secrets | Crypto is correct; real secrets in `.env`, no SecretStr, empty session-secret default, no authZ |
| 7 | [Tests & CI](07-tests-ci.md) | Test inventory, CI, builds, scripts | Two parallel stacks, broken CI (wrong SDK path, lint errors, pytest-asyncio config), no M8 evals/E2E/a11y |

---

## Executive Summary

### What Works Today

- **Phase-1 data model** is complete, including Addendum-1 (`Report.delivery_*`, `Photo.include_in_report`) and Addendum-2 (Escapia native IDs, `sync_cursor`, `housekeeping_status_map`) fields. Migrations apply cleanly and are idempotent.
- **Escapia integration** is the strongest subsystem: token auth, required headers, retry/backoff, reservations delta sync, units/owners poll sync, housekeeping status map + write-back, and work-order write-back all have working code and passing tests.
- **STR QC agent foundation** (`apps/agent`) assembles on `BidiGeminiLiveModel`, carries a coherent "the Keeper" persona, and has working tools for checklist journal, stage advancement, work orders, and Slack delivery.
- **Realtime BIDI bridge** (`backend/app/ws`) is functional: 16 kHz PCM in, 24 kHz PCM out, camera frames, transcripts, tool events.
- **Vite AI Elements demo** (`frontend/`) builds successfully and proves the voice/camera/tooling surface.
- **Cryptography** (`packages/shared/crypto.py`) is implemented correctly (AES-256-GCM, random nonce, AAD, versioned ciphertext).

### What Is Missing or Broken for v1

| Area | Blocking Issue | Milestone |
|------|----------------|-----------|
| **Monorepo stack** | Two parallel stacks (`backend/`+`frontend/` vs `apps/api`+`apps/web`); Makefile/CI/scripts disagree; vendored `strands-py` is broken/uninstallable. | M0 |
| **CI** | CI cannot pass: missing `harness-sdk/strands-py`, ruff lint errors, pytest-asyncio config not picked up in combined invocation. | M0.5 |
| **Secrets hygiene** | `.env` contains live secrets on disk; `STRQC_SESSION_SECRET` defaults to empty; Pydantic fields are plain `str`, not `SecretStr`. | M0.3 / M1.6 |
| **AuthN/Z** | No login, session, role scopes, or user→stakeholder mapping anywhere in the API. | M6.4 / M8.4 |
| **REST API** | No REST/RPC endpoints over `strqc_db` repositories (properties, tasks, inspections, work orders, reports, routes). | M6.1 |
| **Object storage** | Photos stored on local disk; no S3/R2, signed URLs, or thumbnails. | M6.3 |
| **Offline sync** | No service worker, IndexedDB queue, or reconciliation endpoints. | M6.5 / M7.11 |
| **Next.js PWA** | `apps/web/` is a default starter; no product shell, design system, routing, views, or AI Elements integration. | M7 |
| **Agent wiring** | The `/ws` bridge runs the meta-tooling "RandD Live" agent, not the STR QC `apps/agent` agent. | M2/M6 |
| **Memory & telemetry** | No `SessionManager`, memory tools, OpenTelemetry, or per-property audit trail. | M2.4 / M2.6 |
| **Google / Email / Telephony** | Maps, Sheets, Calendar, Docs, Gmail, and outbound calling tools are not present in `apps/agent`. | M3.4–M3.7 |
| **Role permissions** | No tool-permission matrix by stakeholder role; all tools available to every user. | M3.8 |
| **Report generation** | No self-contained embedded-photo report assembly tool; delivery status not updated in DB. | M5.5 / M5.6 |
| **Escapia gaps** | No guest sync, inbound housekeeping/work-order reads, or agent-facing custom Strands tool. | M4 |
| **M8 quality gates** | No QC evals, E2E tests, accessibility audit, or observability tooling. | M8 |

---

## Critical Risks (Must Fix Before v1)

1. **Live secrets in `.env`.** Rotate all keys and move to a secret manager. The `.env` file is gitignored but lives on the developer machine and is rewritten by `slack_token.py`.
2. **No authentication or authorization.** Every API and WebSocket endpoint is open. This is a v1 blocker for any deployment with real property/guest data.
3. **Two-agent / two-stack confusion.** The production voice console must run the STR QC agent (`apps/agent`), not the meta-tooling agent (`backend/app/agent.py`). The monorepo must choose one backend/frontend pair and delete the other.
4. **Broken CI / install.** `make install` and GitHub Actions reference a non-existent `harness-sdk/strands-py` path. The vendored `strands-py/` copy is incomplete (`ModuleNotFoundError: No module named 'strands.types'`).
5. **No Next.js PWA.** The field product is the entire M7 scope and is currently a blank Next.js starter.
6. **No offline support.** Mountain/lake geo properties will have poor connectivity; the PRD explicitly requires offline checklist/photo capture.
7. **No report generation.** Sign-off → embedded-photo report → Slack delivery is the core v1 value loop and is not assembled.
8. **No role-based tool permissions.** A housekeeper could call `deliver_report` or `advance_stage(REPORT)` without restriction.

---

## Test & Build Status Snapshot

| Test/Build | Result | Notes |
|------------|--------|-------|
| `packages/shared/tests` | 6 passed | Crypto round-trip, AAD, key validation |
| `packages/db/tests` | 7 passed | Migrations, Addendum columns, seed, stages, inspections, sync cursor |
| `apps/agent/tests` | Cannot load | `strands-py` import failure blocks collection |
| `apps/api/tests/escapia` | 24 passed (isolated) | Auth, client, sync, scheduler, work orders |
| `make lint` | Fails | 2 ruff errors in `apps/agent/src/strqc_agent/assemble.py` |
| `frontend` build | Passes | Vite demo compiles |
| `apps/web` build | Passes (scaffold) | Default Next.js starter compiles |
| CI as written | Fails | Wrong SDK path, lint errors, pytest-asyncio config mismatch |

---

## Recommended Immediate Next Steps

1. **Consolidate the monorepo:** Decide on `apps/api` + `apps/web` as the product stack; remove or archive `backend/` and `frontend/`; update README, Makefile, CI, and scripts.
2. **Fix the Strands dependency:** Either add `harness-sdk/strands-py` as a complete git submodule or switch `apps/agent` to PyPI `strands-agents` (consistent with legacy backend).
3. **Rotate secrets and move to a secret manager:** Treat the current `.env` as compromised for any shared environment.
4. **Make CI pass:** Fix the install path, ruff errors, and pytest invocation (per-package or global `pytest.ini` with `asyncio_mode = auto`).
5. **Add authN/Z:** Choose an auth provider (Clerk, Auth.js, WorkOS) and gate `/api/*` and `/ws` with role-scoped stakeholder mapping.
6. **Wire the STR QC agent to the bridge:** Replace the meta-tooling agent in `backend/app/main.py` with `strqc_agent.build_agent` or move the bridge to `apps/api`.
7. **Build the Next.js PWA:** Start with M7.1–M7.3 (scaffold, design tokens, app shell) and M7.5–M7.7 (Today route, checklist runner).
8. **Implement report generation and delivery:** Add a `generate_report` tool/service and update `deliver_report` to set `Report.delivery_status`.
9. **Add role-based tool permissions:** Implement a `ToolFilterHook` in `apps/agent` that checks `stakeholder_role`.
10. **Scaffold M8 quality gates:** Add type-checking (mypy/pyright), E2E (Playwright), a11y (axe-core), and observability (OpenTelemetry/Sentry).

---

## Source-of-Truth Documents

- `AGENTS.md` — PRD incl. Addenda 1 & 2
- `TASKS.md` — Milestones M0–M8 and v1 Definition of Done
- `DESIGN.md` — Frontend design system and interaction contract

---

*Generated by Kilo read-only audit. No code files were modified.*
