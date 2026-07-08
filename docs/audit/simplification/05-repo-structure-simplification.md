# Repo Structure & Tooling — Simplification Audit

**Date:** 2026-07-06 · **Read-only** · Companion to skeptic reports [07](../07-tests-ci.md), [00](../00-index.md)

**Constraint:** Preserve all requirements, features, and experience. Remove duplication/dead scaffolding only; every capability must remain available somewhere.

---

## Executive Summary

The repository's biggest structural cost is **two parallel stacks** (`backend/` + `frontend/` legacy Vite vs `apps/api` + `apps/web` intended) plus a **broken vendored SDK path** and a handful of **stray/duplicated files**. Choosing one canonical stack and deleting the other is the single largest footprint reduction in the whole project and directly removes the "which stack do I run?" ambiguity the skeptic flagged — with **no loss of capability**, because the two stacks are functional duplicates of the same product surface.

---

## Incorporated Skeptic Findings

- Skeptic #7: two backends, two frontends; CI references non-existent `harness-sdk/strands-py`; vendored `strands-py/` incomplete (`ModuleNotFoundError: strands.types`); Makefile/scripts/README disagree; lockfile confusion; no type-check/E2E/a11y.
- Skeptic #00: consolidated critical risks.

---

## Two-Stack Consolidation Analysis

| Stack | Unique value today | Status |
|-------|--------------------|--------|
| `backend/` (FastAPI + `/ws` bridge) + `frontend/` (Vite AI Elements) | The **only working end-to-end live voice/camera/tooling demo**; proves BIDI. Uses PyPI `strands-agents`. | Working, but is the *legacy* stack per README/TASKS |
| `apps/api` (Escapia + intended API) + `apps/web` (Next.js) + `apps/agent` (Keeper) + `packages/*` | The **intended product architecture** (DB-backed agent, migrations, Escapia, PWA target). | Partially built; `apps/web` is a scaffold; `apps/agent` can't import the broken vendored SDK |

**Recommendation (two viable paths, both reduce footprint):**

- **Path A (fastest to lean):** Keep `apps/*` + `packages/*` as canonical. **Port** the working bridge (`backend/app/io.py`, `browser_camera.py`, WebSocket endpoint) into `apps/api`, wire it to the **Keeper** agent, then **delete `backend/`**. Migrate the proven Vite components into `apps/web` (or keep `frontend/` temporarily as a reference and delete after port).
- **Path B (pragmatic interim):** Freeze `apps/*` as the target, keep `backend/`+`frontend/` running until the port lands, but **immediately delete the truly dead pieces** below regardless of path.

Either way, the end state is **one backend + one frontend**, roughly halving the app-layer file/config count.

---

## Dead Files / Paths to Remove (verified)

| Path | Evidence | Action |
|------|----------|--------|
| `strands-py/` (vendored, incomplete) | Skeptic: `strands.types` missing; not installable. `harness-sdk/` doesn't exist. | Replace with proper `harness-sdk` submodule **or** rely on PyPI `strands-agents` (as `backend/` does), then delete the broken copy. |
| `sql/phase1_schema.sql` | Superseded by `packages/db/migrations/0001` (README §Legacy). | Delete (see DB report D1). |
| `randd-fixes.patch` (root) | Stray patch file, 7.4 KB; not referenced by build/CI. | Verify contents applied, then delete. |
| `chat.json` (root, 91 B) | Stray; not referenced. | Verify + delete. |
| `frontend/` (after port) | Functional duplicate of the target web app. | Delete once ported (Path A). |
| `backend/` (after port) | Functional duplicate of the target API/bridge. | Delete once ported (Path A). |

> Before deleting `randd-fixes.patch`/`chat.json`, confirm no script/doc references them (`rg` the filename).

---

## Tooling / CI / Script Consolidation

| Item | Problem | Fix (no capability loss) |
|------|---------|--------------------------|
| CI install path | References `harness-sdk/strands-py` (missing) | Point at the real SDK source (submodule or PyPI) |
| `make test` | Combined pytest drops `asyncio_mode` | Run per-package OR add root `pytest.ini` with `asyncio_mode=auto` |
| `make lint` | 2 ruff errors in `assemble.py` | Auto-fix (`ruff --fix`) |
| `scripts/run-backend.sh` / `run-frontend.sh` | Drive the **legacy** stack; contradict Makefile (`apps/*`) | After consolidation, delete the legacy scripts; keep one dev entrypoint |
| root `package.json` `dev` | Starts legacy stack via `concurrently` | Repoint to canonical stack (or remove once Makefile is the single entrypoint) |
| `clean-ports.sh` | macOS-only `lsof`, misses :3000 | Minor; keep but note portability |

---

## Package-Manager & Lockfile Consolidation

- Present at root: **`package-lock.json` only** (verified — no `pnpm-lock.yaml`/`pnpm-workspace.yaml` at root now). README/Makefile mention `pnpm`. 
- **Pick one manager.** If npm, update README/Makefile (`make install-web` uses `pnpm`) to `npm`. If pnpm, generate the lockfile and remove `package-lock.json`. Single manager = no "multiple lockfiles" Next.js workspace-root warning the skeptic saw.

---

## Docs Consolidation

| Docs | Overlap | Action |
|------|---------|--------|
| `AGENTS.md` (root) | Canonical PRD | Keep |
| `apps/web/AGENTS.md`, `apps/web/CLAUDE.md` | Scaffold-generated agent docs | Remove or replace with a one-line pointer to root `AGENTS.md` |
| `README.md`, `backend/README.md`, `apps/web/README.md` | Overlapping quickstarts; some describe legacy stack | Collapse to one root README after stack consolidation; keep app READMEs to a short blurb |

---

## Estimated Net Reduction

- **Directories:** −1 large (`strands-py/` broken copy) and, after port, −2 app trees (`backend/`, `frontend/`) collapsed into `apps/*`.
- **Files:** −4 immediately (`sql/phase1_schema.sql`, `randd-fixes.patch`, `chat.json`, `apps/web/CLAUDE.md`) + many more after stack consolidation.
- **Cognitive load:** one stack, one manager, one dev command, one PRD.

---

## Do Not Delete — Still Needed

- `apps/*`, `packages/*` — the target architecture.
- `Escapia/` specs — integration contract.
- `AGENTS.md`, `TASKS.md`, `DESIGN.md` — sources of truth.
- The **working bridge code** in `backend/app/io.py` + `browser_camera.py` — port it before deleting `backend/`; don't lose the transport logic.
- `docs/audit/**` — this audit trail.

---

## Prioritized Recommendations

1. **Decide the canonical stack** (recommend `apps/*` + `packages/*`) — unblocks every other cleanup.
2. **Fix the Strands SDK path** (submodule or PyPI), delete broken `strands-py/`.
3. **Delete stray files** (`sql/phase1_schema.sql`, `randd-fixes.patch`, `chat.json`, scaffold `CLAUDE.md`).
4. **Single package manager + lockfile**; align README/Makefile.
5. **Port the bridge to `apps/api` wired to the Keeper, then delete `backend/` + `frontend/`.**
6. **Auto-fix ruff + fix pytest invocation** so CI passes on the slimmer tree.
