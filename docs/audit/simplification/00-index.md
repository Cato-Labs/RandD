# STR QC Platform — Code Simplification & Optimization Audit (Index)

**Date:** 2026-07-06 · **Read-only** (no code modified) · Companion to the skeptic audit in [`../00-index.md`](../00-index.md)

**Mandate:** A leaner, more efficient, better-performing, lighter codebase — **without any change to requirements, features, or quality of experience.** Every recommendation below is behavior-preserving.

> Note: this pass was executed directly (the parallel simplification subagents hit the billing quota mid-run and were not available). Findings are grounded in the seven skeptic reports plus fresh verification (`ripgrep`/`glob`) of component usage, duplicate definitions, heavy dependencies, and stray files.

---

## Reports

| # | Report | Theme | Headline win |
|---|--------|-------|--------------|
| 1 | [DB & Shared](01-db-shared-simplification.md) | Schema/repo/config | Delete duplicate schema source; repo boilerplate helpers |
| 2 | [Agent & Tools](02-agent-simplification.md) | Two agent stacks | Consolidate duplicate camera/journal/slack/memory + one `build_model` |
| 3 | [Backend & Escapia](03-backend-escapia-simplification.md) | Services | Table-driven Escapia boilerplate; unify report persistence; lazy imports |
| 4 | [Frontend & Bundle](04-frontend-simplification.md) | Bundle weight | Code-split `@xyflow`/`shiki`/`mermaid`; remove dead component |
| 5 | [Repo Structure & Tooling](05-repo-structure-simplification.md) | Footprint | Collapse two stacks into one; delete broken SDK + stray files |

---

## The Big Three (highest leverage, zero behavior change)

1. **Collapse the two parallel stacks into one.** `backend/`+`frontend/` (legacy Vite) and `apps/api`+`apps/web`+`apps/agent`+`packages/*` (intended) are functional duplicates of the same product. Porting the working bridge to `apps/api` (wired to the Keeper agent) and deleting the legacy trees roughly halves the app-layer footprint and eliminates the "which stack?" ambiguity. *No feature is lost — both stacks do the same job.* (Report 5)

2. **De-duplicate the agent tool set.** Camera, journal, Slack delivery, memory, and `build_model` each exist twice across the two agents. One canonical implementation (DB-backed Keeper tools + native Slack tool + one shared model builder) removes ~300 LOC with identical behavior. (Report 2)

3. **Code-split the heavy front-end features.** Verified: `@xyflow/react` (Workflow graph, behind a toggle), `shiki` (code blocks), and `mermaid` (message diagrams) are the dominant weight and are **not on first paint**. `React.lazy`/dynamic import defers them — same UX, much smaller initial bundle (skeptic measured ~2.77 MB main chunk). (Report 4)

---

## Verified Quick Wins (safe, small, immediate)

| Win | Evidence | Report |
|-----|----------|--------|
| Delete `frontend/src/components/ai-elements/shimmer.tsx` | 0 references (ripgrep) | 4 |
| Delete `sql/phase1_schema.sql` | Superseded by `packages/db` migration 0001 (README §Legacy) | 1, 5 |
| Delete stray `chat.json` (91 B) and `randd-fixes.patch` after ref-check | Not referenced by build/CI | 5 |
| Merge duplicate `build_model` (`apps/agent/assemble.py:26` + `backend/app/agent.py:114`) | Only two defs (ripgrep) | 2, 3 |
| Delete broken vendored `strands-py/` after fixing SDK dep | Skeptic: `strands.types` missing, uninstallable | 5 |
| Auto-fix 2 ruff errors in `assemble.py` | Skeptic #7 | 5 |
| `mask_secret` fixed-width mask | Removes last-char leak, less code | 1 |

---

## Consolidations (medium effort, meaningful reduction)

- **Escapia boilerplate** → helpers for pagination, cursor read-modify-write, and per-op request/parse (Report 3, E1–E3, ~−130 LOC, fully covered by existing 24 tests).
- **Report persistence** → one HTML/state parser feeding both DB row and S3 archive (Report 3, B1).
- **Slack upload** → converge three upload paths on the native `strands_tools.slack` tool (Reports 2/3).
- **`use-live-agent.ts` message-part upsert** → one `updateLastAssistant`/`upsertPart` helper replacing 4–5 copies (Report 4, F1, ~−80 LOC).
- **Repository boilerplate** → `fetch_one`/`fetch_all`/transaction helpers (Report 1, D3).
- **Per-tool boilerplate** → `@qc_tool`/context-manager wrapper (Report 2, A4).

---

## Estimated Net Reduction (behavior-preserving)

| Layer | Files | LOC | Other |
|-------|-------|-----|-------|
| Repo structure | −4 now, −2 large trees after port | thousands (dupe stack) | 1 manager, 1 dev command |
| Agent | −1 to −2 | ~−300 | one agent, one model builder |
| Backend/Escapia | −1 (`_vendor.py`) | ~−200 | faster `/ws` cold start |
| Frontend | −1 to −2 | ~−80 | **major** initial-bundle drop via code-split |
| DB/Shared | −2 | ~−40 | one schema source |

---

## Global "Do Not Touch" (behavior/experience contracts)

- Crypto format & AAD, migration ledger/PRAGMAs, result/priority/stage enums.
- Escapia auth headers, retry/backoff, delta-vs-poll cursor semantics.
- Audio sample rates / worklet / playback scheduling; camera facing-mode fallbacks.
- Persona content and guardrail confirmation semantics.
- The Workflow graph and all rendered AI Elements with ≥1 reference — only *how/when* heavy features load may change, never *what* they show.
- Frontend/API request/response shapes (`/api/inspection/export`, `/ws` events).

---

## Recommended Execution Order

1. Decide canonical stack → fix Strands SDK dep → delete broken `strands-py/` and stray files. *(unblocks everything, biggest footprint win)*
2. Extract shared `build_model`; converge Slack on native tool.
3. Code-split `@xyflow`/`shiki`/`mermaid`; remove `shimmer.tsx`. *(biggest perf win)*
4. Escapia + repository + backend boilerplate helpers. *(LOC, guarded by tests)*
5. Consolidate report persistence; `use-live-agent` helpers.
6. Single package manager/lockfile; auto-fix ruff; fix pytest invocation so CI passes on the slimmer tree.

Each step should be validated by the existing test suites (37 currently-passing Python tests + frontend build) before and after, ensuring identical behavior.

---

*Generated by Kilo read-only simplification audit. No code files were modified.*
