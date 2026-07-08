# Audit: Test Coverage & CI/Build Infrastructure

**Scope:** Read-only review of `/Users/tims-stuff/RandD/RandD` against AGENTS.md/TASKS.md M0 and M8.
**Date:** 2026-07-06
**Auditor:** Kilo

---

## Executive Summary

The repository has **two parallel, inconsistent build stacks** and **CI that cannot pass as written**.

- **Python packages (`packages/*`, `apps/*`)** are configured as editable Hatchling packages with unit tests, but the vendored Strands SDK (`strands-py/`) is incomplete and breaks the agent package entirely. The API package tests pass only when invoked in isolation.
- **Two backends exist:** `backend/` is a legacy FastAPI app using the real PyPI `strands-agents` SDK; `apps/api/` is the new FastAPI service referenced by the Makefile. They are unrelated.
- **Two frontends exist:** `frontend/` is a Vite AI chat app (not the PWA from DESIGN.md); `apps/web/` is the intended Next.js PWA but remains a `create-next-app` scaffold.
- **No type-checking, E2E, accessibility, or observability tooling** is present, despite M8 requirements.
- **The Makefile and CI both reference a `harness-sdk/strands-py` path that does not exist**, and the CI `test` step will fail because `pytest-asyncio` configuration is not picked up when multiple package test paths are combined.

Overall, the project is **not ready for continuous integration** and requires a monorepo consolidation before M8 work can be meaningfully gated on tests.

---

## Test Inventory by Package/Area

| Package / Area | Test Files | # Tests | Status When Run | Notes |
| --- | --- | --- | --- | --- |
| `packages/shared` | `tests/test_crypto.py` | 6 | **Pass** | Covers `encrypt_secret`, `decrypt_secret`, `mask_secret` (round-trip, AAD, wrong key, bad length, masking). |
| `packages/db` | `tests/test_db.py` | 7 | **Pass** | Migrations, Addendum columns, seed data, stage transitions, inspection flow, sync cursor. |
| `apps/agent` | `tests/test_assemble.py` | 4 | **Cannot load** | `strands-py` import failure blocks collection. |
| `apps/agent` | `tests/test_delivery.py` | 5 | **Cannot load** | Slack adapter tests. |
| `apps/agent` | `tests/test_guardrails.py` | 6 | **Cannot load** | Confirmation guardrails. |
| `apps/agent` | `tests/test_tools.py` | 11 | **Cannot load** | Journal, camera, work orders, stage, property brief. |
| `apps/api` | `tests/escapia/test_auth_and_client.py` | 8 | **Pass (isolated)** | Token caching, headers, 429/5xx backoff, retry. |
| `apps/api` | `tests/escapia/test_housekeeping_workorders.py` | 6 | **Pass (isolated)** | Status map, write-back, work-order push. |
| `apps/api` | `tests/escapia/test_scheduler.py` | 2 | **Pass (isolated)** | Error isolation, scheduler loop. |
| `apps/api` | `tests/escapia/test_sync_reservations.py` | 4 | **Pass (isolated)** | Delta cursor, idempotency, unknown units. |
| `apps/api` | `tests/escapia/test_sync_units_owners.py` | 4 | **Pass (isolated)** | Unit demographics, owner links. |
| `frontend` | — | 0 | **None** | No test scripts or test files. |
| `apps/web` | — | 0 | **None** | No test scripts or test files. |
| E2E / QA | — | 0 | **None** | No Playwright, Cypress, or similar. |
| QC evals (M8.1) | — | 0 | **None** | No labeled photo/checklist regression suite. |
| Accessibility (M8.3) | — | 0 | **None** | No a11y tests, axe, or WCAG audit. |
| Observability (M8.5) | — | 0 | **None** | No tracing/metrics tests, no dashboards. |

**Total test files:** 11.  
**Total tests that can currently execute:** 13 (shared/db) + 24 (api, isolated) = **37**.  
**Total tests that cannot load:** 26 (agent).  
**Total tests that CI will currently fail:** 26 (agent) + 24 (api, due to combined invocation) = **50**.

---

## Test Coverage Gaps

### What is implemented but not tested

| Implemented module | Test coverage | Gap |
| --- | --- | --- |
| `strqc_shared/config.py` | `test_crypto.py` only | `Settings` / env loading has no tests. |
| `strqc_db/repositories.py` | `test_db.py` | Partial; many repository helpers (route planning, report assembly, notifications) are not tested. |
| `strqc_db/seed.py` | `test_db.py` | Only verifies one seeded property; no coverage of seed idempotency or completeness. |
| `strqc_agent/tools/*` | blocked | 8 agent tools have no running tests. |
| `strqc_agent/persona.py` | blocked | System prompt versioning is not verified. |
| `strqc_agent/guardrails.py` | blocked | Confirmation policy is not verified. |
| `strqc_agent/assemble.py` | blocked | Tool registration and prompt injection are not verified. |
| `strqc_api/escapia/*` | covered | Good coverage of client, sync, scheduler, work orders. |
| `frontend/src/*` | none | ~50 components, hooks, and views have zero tests. |
| `apps/web/src/*` | none | Scaffold only, but still no tests. |

### What is required by M8 but absent

- **M8.1 QC evals:** No labeled dataset, no regression test harness, no prompt/model evaluation gate.
- **M8.2 E2E tests:** No happy-path or failure-path tests for turnover, inspection, work-order, or report delivery.
- **M8.3 Accessibility audit:** No WCAG 2.2 AA tests, touch-target checks, or screen-reader tests.
- **M8.5 Observability:** No OpenTelemetry tests, no log/metric dashboards, no per-property audit trail tests.

---

## CI Pipeline Status

### GitHub Actions (`.github/workflows/ci.yml`)

The workflow defines two jobs:

1. **python** (`ubuntu-latest`, Python 3.12)
   - Installs packages via the same commands as `make install`.
   - Runs `ruff check` and `pytest` for all packages in **one invocation**.
2. **web** (`ubuntu-latest`, Node 22)
   - Runs `npm ci`, `npm run lint`, `npm run build` in `apps/web`.

**Problems:**

- **Install step references `harness-sdk/strands-py`, which does not exist.** The actual vendored SDK is at `strands-py/`, but that directory is not a valid installable package (see below). CI will fail at install.
- **Lint step (`ruff check packages apps/agent apps/api`) currently fails** with 2 fixable errors in `apps/agent/src/strqc_agent/assemble.py` (import ordering and whitespace).
- **Test step combines all package test paths in one `pytest` invocation.** Because `apps/api/pyproject.toml` declares `asyncio_mode = "auto"` but `packages/shared` and `packages/db` do not, the async mode is not applied when pytest resolves the rootdir from the first path. This causes all 24 API async tests to fail with:
  ```
  async def functions are not natively supported.
  You need to install a suitable plugin for your async framework, for example:
    - pytest-asyncio
  ```
- **No type-checking job** (M0.5 requires lint, type-check, unit tests).
- **No E2E/accessibility/observability jobs** (M8).
- **Frontend job only tests `apps/web`**, not the `frontend/` Vite app that the README actually describes.

### Makefile (`Makefile`)

| Target | Expected behavior | Actual behavior / risk |
| --- | --- | --- |
| `install` | Install editable Python packages + Strands SDK | Fails: `harness-sdk/strands-py` missing. `strands-py/` is not a package. |
| `install-web` | `pnpm install` in `apps/web` | Only installs `apps/web`; ignores `frontend/` dependencies. |
| `migrate` | Run `strqc_db.migrate` | Cannot run until `install` is fixed. |
| `seed` | Run `strqc_db.seed` | Cannot run until `install` is fixed. |
| `test` | Run all Python tests in one command | Will fail due to `asyncio_mode` configuration issue. |
| `lint` | Run `ruff` | Currently fails (2 errors). |
| `api` | Run `apps/api` FastAPI | Correct, but unrelated to `scripts/run-backend.sh`. |
| `web` | Run `apps/web` Next.js | Correct, but `scripts/run-frontend.sh` runs `frontend/` instead. |
| `agent` | Run `apps/agent` console | Cannot run due to broken `strands-py`. |
| `dev` | Hint to run two shells | Does not start anything. |
| `clean` | Remove DB and caches | OK. |

**No type-check target exists.**

---

## Build Status

### `frontend` (Vite AI chat)

- **Command:** `cd frontend && npm run build`
- **Result:** ✅ Builds successfully.
- **Output snippet:**
  ```
  vite v7.3.6 building client environment for production...
  transforming...
  ✓ 5190 modules transformed.
  rendering chunks...
  computing gzip size...
  dist/index.html                                           0.43 kB │ gzip:   0.30 kB
  dist/assets/index-DDbxfBU5.css                           95.34 kB │ gzip:  15.94 kB
  ...
  ```
- **Notes:** No `lint` script in `package.json`. This is the app the README quickstart actually describes, but it is not the Next.js PWA from DESIGN.md/TASKS.md.

### `apps/web` (Next.js PWA)

- **Command:** `cd apps/web && npm run build`
- **Result:** ✅ Builds successfully, but it is a scaffold.
- **Output snippet:**
  ```
  ▲ Next.js 16.2.10 (Turbopack)
    Creating an optimized production build ...
  ✓ Compiled successfully in 1096ms
    Running TypeScript ...
    Finished TypeScript in 876ms ...
  Route (app)
  ┌ ○ /
  └ ○ /_not-found
  ○  (Static)  prerendered as static content
  ```
- **Notes:**
  - Only one route (`/`) and a 404 page. The page is the default `create-next-app` template, not an STR QC app shell.
  - Build emits a warning about multiple lockfiles and workspace root detection:
    ```
    ⚠ Warning: Next.js inferred your workspace root, but it may not be correct.
    We detected multiple lockfiles and selected the directory of /Users/tims-stuff/package-lock.json as the root directory.
    ```
  - This project has both `package-lock.json` and `pnpm-lock.yaml` plus `pnpm-workspace.yaml`, which is confusing for the package manager.

### Backend / API

- **Legacy `backend/` app:** Uses `requirements.txt` with real PyPI `strands-agents`. It is the runtime targeted by `scripts/run-backend.sh` and the frontend proxy. It is not covered by the Makefile or CI.
- **New `apps/api/`:** Has no executable `main.py` at the top level; the Makefile runs `uvicorn strqc_api.main:app`, but `strqc_api/main.py` was not found in the source tree. The package only contains the `escapia/` subpackage.

---

## Lint / Type-Check Status

### Python lint (`ruff`)

- **Command:** `python -m ruff check packages apps/agent apps/api`
- **Result:** ❌ 2 errors, both auto-fixable.
- **Output:**
  ```
  I001 [*] Import block is un-sorted or un-formatted
    --> apps/agent/src/strqc_agent/assemble.py:7:1
  W293 [*] Blank line contains whitespace
    --> apps/agent/src/strqc_agent/assemble.py:40:1
  Found 2 errors.
  [*] 2 fixable with the `--fix` option.
  ```

### JavaScript/TypeScript lint

- **`frontend`:** No `lint` script in `package.json`. `npm run lint` fails with "Missing script: lint".
- **`apps/web`:** `npm run lint` runs `eslint` and exits successfully (no reported errors), but with the current config it scans irrelevant files (`.md`, `.gitignore`). The scaffold code has no lint errors.

### Type-checking

- **Python:** No `mypy`, `pyright`, or `type-check` configuration in any `pyproject.toml` or the Makefile. M0.5 requires type-checking but it is absent.
- **TypeScript:** `frontend` builds with `tsc -b` as part of `npm run build`, which performs type-checking. `apps/web` builds with Next.js and also type-checks during `npm run build`. Neither has a standalone `type-check` script.

---

## E2E / Evals / Accessibility / Observability Status

| Requirement | Status | Evidence |
| --- | --- | --- |
| M8.1 QC evals | ⬜ Not started | No labeled datasets, no eval harness, no regression gate. |
| M8.2 E2E tests | ⬜ Not started | No Playwright, Cypress, or similar tooling. No happy-path or failure-path tests. |
| M8.3 Accessibility audit | ⬜ Not started | No axe, no WCAG tests, no manual a11y checklist, no reduced-motion tests. |
| M8.5 Observability | ⬜ Not started | No OpenTelemetry, no Sentry, no metrics dashboards, no per-property audit tests. |
| M8.6 Deploy | ⬜ Not started | No Dockerfile, no Terraform/CFN, no GitHub deploy workflow, no staging/production separation. |

---

## Makefile and Script Audit

### `scripts/run-frontend.sh`

- Starts the `frontend/` Vite dev server on `:5173`.
- Waits for `http://localhost:8000/api/models`.
- Installs `frontend/node_modules` if missing.
- **Problem:** This script is wired to the legacy `backend/` app (`/api/models`), not to `apps/api` or the new packages. It is also not referenced by the Makefile (which uses `make web` → `apps/web`).

### `scripts/run-backend.sh`

- Creates a venv in `backend/venv`, installs `backend/requirements.txt`, and runs `uvicorn app.main:app` from the `backend/` directory.
- **Problem:** This is the legacy backend. It does not use the `apps/api` package or the `packages/*` workspace. The Makefile `api` target runs a completely different service (`strqc_api.main:app`).

### `scripts/clean-ports.sh`

- Kills processes on ports 8000 and 5173 using `lsof`.
- **Problem:** OK in principle, but `lsof` is macOS-specific; it will not work on CI runners. Also, it does not clean port 3000 (`apps/web`).

### Root `package.json`

```json
{
  "scripts": {
    "predev": "bash scripts/clean-ports.sh",
    "dev": "concurrently ... \"npm:dev:backend\" \"npm:dev:frontend\"",
    "dev:backend": "bash scripts/run-backend.sh",
    "dev:frontend": "bash scripts/run-frontend.sh"
  }
}
```

- **Problem:** `npm run dev` starts the legacy backend and the Vite frontend, not the new monorepo stack (`apps/api` + `apps/web`). This contradicts the README quickstart which says `make api` and `make web`.

---

## Specific Test Failures and Error Messages

### 1. Agent tests cannot load due to incomplete vendored Strands SDK

**Command:**
```bash
python -m pytest apps/agent/tests -q
```

**Output:**
```
ImportError while loading conftest '/Users/tims-stuff/RandD/RandD/apps/agent/tests/conftest.py'.
apps/agent/tests/conftest.py:11: in <module>
    from strqc_agent.context import AgentRunContext, clear_context, set_context
apps/agent/src/strqc_agent/__init__.py:3: in <module>
    from .assemble import build_agent
apps/agent/src/strqc_agent/assemble.py:11: in <module>
    from strands.experimental.bidi import BidiAgent
strands-py/src/strands/experimental/bidi/__init__.py:7: in <module>
    from ...types._events import (
E   ModuleNotFoundError: No module named 'strands.types'
```

**Root cause:** `strands-py/src/strands/` only contains `experimental/bidi/`. The parent `strands` package is missing `types/`, `tools/`, etc. The `__init__.py` tries to import from `...types._events` which does not exist. The Makefile also references the wrong path (`harness-sdk/strands-py`).

### 2. API tests fail when combined with other packages

**Command:**
```bash
python -m pytest packages/shared/tests packages/db/tests apps/api/tests -q
```

**Output (truncated):**
```
........................FFFFFFFFFFFFFFFFFFFFFFFF
async def functions are not natively supported.
You need to install a suitable plugin for your async framework, for example:
  - pytest-asyncio
```

**Root cause:** `apps/api/pyproject.toml` sets `asyncio_mode = "auto"`, but when pytest is invoked with multiple package paths it does not pick up that config. The `pytest.ini_options` in `apps/api/pyproject.toml` is only honored when the package root is the pytest rootdir.

### 3. Python lint fails

**Output:**
```
I001 [*] Import block is un-sorted or un-formatted  --> apps/agent/src/strqc_agent/assemble.py:7:1
W293 [*] Blank line contains whitespace              --> apps/agent/src/strqc_agent/assemble.py:40:1
Found 2 errors.
```

### 4. Frontend lint script missing

**Output:**
```
npm error Missing script: "lint"
```

---

## Risks and Recommendations

### Critical risks

1. **CI is broken.** The GitHub Actions workflow will fail at install because `harness-sdk/strands-py` is missing, and if that is fixed, it will still fail because of ruff errors and the pytest-asyncio configuration issue. A broken CI is a blocker for any M8 gate.
2. **Two backends and two frontends.** The `backend/` + `frontend/` stack is the one actually described in the README and run by root `npm run dev`, while `apps/api` + `apps/web` is the intended monorepo stack. This is a high-risk fork; developers and CI may test the wrong stack.
3. **Vendored SDK is unusable.** `strands-py/` is not a valid package and cannot be installed. Either replace it with a proper `harness-sdk` git submodule or depend on the real PyPI `strands-agents` (as the legacy backend does).
4. **No type-checking.** Python code is untyped-checked. Given the security-sensitive nature of secrets and PII, type-checking should be a hard gate.
5. **M8 work is entirely missing.** Evals, E2E, a11y, and observability are not scaffolded and will require significant effort.

### Recommendations (prioritized)

1. **Consolidate the monorepo stack.** Decide whether the product is `backend/` + `frontend/` or `apps/api` + `apps/web` and remove the other. Update README, Makefile, CI, and scripts accordingly.
2. **Fix the Strands dependency.**
   - Option A: Add `harness-sdk/strands-py` as a git submodule or subtree with a complete, installable package.
   - Option B: Switch `apps/agent` to depend on PyPI `strands-agents` (consistent with the legacy backend).
3. **Fix CI/test invocation.** Either run pytest per package (`cd apps/api && pytest`) or add a root `pytest.ini` with `asyncio_mode = auto` and a global `pytest-asyncio` config.
4. **Add Python type-checking.** Add `mypy` or `pyright` to each package and a `make type-check` target.
5. **Add lint to `frontend`.** Add `eslint` and `prettier` scripts.
6. **Scaffold M8 infrastructure.** Add Playwright for E2E, an a11y audit harness (axe-core or Storybook a11y), and OpenTelemetry/Sentry for observability.
7. **Remove lockfile confusion.** Use either npm or pnpm, not both. Pick one lockfile and workspace strategy.

---

## Requirement Mapping Checklist

| TASKS.md / AGENTS.md requirement | Status | Notes |
| --- | --- | --- |
| **M0.1** Workspace layout | 🟡 Partial | Layout exists, but two stacks (`backend/` vs `apps/`) create ambiguity. |
| **M0.2** Pin Strands SDK | ❌ Failing | SDK path wrong (`harness-sdk/` missing); vendored copy is broken. |
| **M0.3** Secrets hygiene | 🟡 Partial | `.env.example` exists; `test_crypto.py` covers encryption. Full audit not in scope. |
| **M0.4** README quickstart (`make dev`, `make install`) | ❌ Failing | `make install` fails; `make dev` only prints a hint; root `npm run dev` starts legacy stack. |
| **M0.5** Baseline CI (lint, type-check, unit tests) | ❌ Failing | CI fails at install/test; no type-checking configured. |
| **M1.1–M1.5** Data-model completion | 🟡 Partial | Schema and tests include Addendum fields, but no migration tool (Alembic) is in place. |
| **M1.6** Encrypt secrets at rest | 🟡 Partial | Crypto helpers tested; end-to-end enforcement not audited. |
| **M1.7** Repository pattern + typed models | 🟡 Partial | `repositories.py` exists and has partial tests. |
| **M1.8** Seeds/fixtures | ✅ Present | Seed data and tests exist. |
| **M2–M3** Agent core + tools | 🟡 Partial | Source code exists but cannot be imported/tested due to broken SDK. |
| **M4** Escapia integration | 🟡 Partial | API tests cover client/sync/scheduler; agent-side Escapia tool missing. |
| **M5** Domain services (QC engine) | 🟡 Partial | Repositories and tools exist, but no report assembly or delivery tests run. |
| **M6** Backend API + realtime bridge | 🟡 Partial | Legacy backend works; new `apps/api` has no main entry or tests. |
| **M7** Frontend (Next.js PWA) | ❌ Not started | `apps/web` is a scaffold; `frontend/` is a Vite AI chat, not the PWA. |
| **M8.1** QC evals | ❌ Not started | No evals. |
| **M8.2** E2E tests | ❌ Not started | No E2E tooling. |
| **M8.3** Accessibility audit | ❌ Not started | No a11y tooling. |
| **M8.4** Security review | ⬜ Not audited | Out of scope for this test/CI audit. |
| **M8.5** Observability | ❌ Not started | No observability tests. |
| **M8.6** Deploy | ❌ Not started | No deploy pipeline or IaC. |
| **M8.7** Pilot | ⬜ Not applicable | Not yet. |

---

## Commands Run During This Audit

```bash
# Python test suite (from repo root)
python3 -m venv /tmp/str-qc-audit-venv
/tmp/str-qc-audit-venv/bin/pip install -e "packages/shared[dev]"
/tmp/str-qc-audit-venv/bin/pip install -e "packages/db[dev]"
/tmp/str-qc-audit-venv/bin/pip install -e "apps/agent[dev]"
/tmp/str-qc-audit-venv/bin/pip install -e "apps/api[dev]"
PYTHONPATH="/Users/tims-stuff/RandD/RandD/strands-py/src:$PYTHONPATH" \
  /tmp/str-qc-audit-venv/bin/python -m pytest packages/shared/tests packages/db/tests apps/agent/tests apps/api/tests -q

# Lint
/tmp/str-qc-audit-venv/bin/python -m ruff check packages apps/agent apps/api

# Frontend builds
cd frontend && npm run build
cd frontend && npm run lint
cd apps/web && npm install && npm run build && npm run lint
```
