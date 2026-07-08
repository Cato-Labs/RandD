# Frontend & Bundle — Simplification Audit

**Date:** 2026-07-06 · **Read-only** · Companion to skeptic report [05](../05-frontend.md)

**Constraint:** Preserve all requirements, features, and experience — **no UX/visual change**. Focus on dead code and bundle weight only.

---

## Executive Summary

The Vite demo carries a large bundle (skeptic: ~2.77 MB main chunk). The dominant, verified causes are **three heavy dependencies pulled eagerly**: `shiki` (syntax highlighting), `mermaid` (diagram rendering), and `@xyflow/react` (the Workflow graph). All three back features that are **not on the default screen**, so they can be lazy-loaded/code-split with zero UX change. There is also a small amount of verified dead code.

---

## Incorporated Skeptic Findings

- Skeptic #5: Vite build succeeds but chunks >500 KB (Shiki/Mermaid/Cytoscape); AI Elements vendored; `apps/web` empty; `use-live-agent.ts` has repeated upsert patterns; `use-mobile.ts` unused in shell.

---

## Dead / Unused Components & Exports (verified via ripgrep)

| Item | Refs (excl. self) | Verdict |
|------|-------------------|---------|
| `ai-elements/shimmer.tsx` | 0 | **Dead** — remove |
| `ai-elements/persona.tsx` | 1 (VoiceDock) | Used — keep |
| All other ai-elements | ≥1 | Used (directly or transitively) |

> Method: `rg -l 'ai-elements/<name>"'` across `frontend/src`, excluding the file itself. Only `shimmer` returned 0 and has no view references.

Note: several ai-elements are used only through the **Canvas/graph cluster** (`canvas, node, edge, panel, controls, toolbar, connection`) which is imported by `WorkflowView` and pulls `@xyflow/react`. That cluster is only mounted when the user toggles **Workflow** (`App.tsx` `workflowOpen`), so it is a prime code-split boundary (see below) — not dead, but deferrable.

Also verify unused exports in `live-types.ts` and `parse-blocks.ts` and prune any type/enum with 0 references (low-risk, compiler-verifiable).

---

## Heavy Dependency Analysis + Code-Splitting

| Dep | Imported by | Feature | On first paint? | Action |
|-----|-------------|---------|-----------------|--------|
| `shiki` | `ai-elements/code-block.tsx` | Syntax-highlighted code blocks | Only when a code block is rendered | `React.lazy`/dynamic import the highlighter; render plain `<pre>` until loaded | 
| `mermaid` | `ai-elements/message.tsx` | Diagram rendering in messages | Only when a mermaid block appears | Lazy-init mermaid on first diagram; defer the import |
| `@xyflow/react` | `WorkflowView` + canvas cluster (8 files) | Live session graph | Only when Workflow panel is toggled | Route-/toggle-level `React.lazy(() => import('./views/WorkflowView'))` |

Expected impact: moving these three out of the initial chunk should cut the main bundle substantially (they are the largest contributors per the skeptic's chunk report). **No UX change** — the features render exactly the same, just loaded on demand. `code-block` and `message` should degrade gracefully (plain text / placeholder) for the sub-second while the chunk loads.

---

## `use-live-agent.ts` and lib Simplification

The hook (836 LOC) repeats the same "get last assistant message, clone parts, upsert part, replace last" pattern in at least four places: `appendText`, `upsertToolPart`, `upsertThoughtPart`, `bidi_grounding_metadata` handler, and `bidi_response_complete` finalizer.

| # | Opportunity | Safe because | Reduction | Risk |
|---|-------------|--------------|-----------|------|
| F1 | Extract `updateLastAssistant(fn)` and `upsertPart(predicate, part)` helpers; rewrite the 4–5 sites to use them | Identical state transitions | ~60–90 LOC | Low (unit-test the helper) |
| F2 | Remove `use-mobile.ts` if it stays unused, OR wire it (skeptic notes it's unused) — for pure simplification, delete until the mobile shell needs it | 0 references today | −1 file | Low |
| F3 | `segments` timing math (`text.length * 0.05`) duplicated with `appendText` — fold into one segment builder | Same values | small | Low |

---

## Duplication to Eliminate

- The message-part upsert logic (F1) — 4–5 copies → 1 helper.
- `code-block` and `message` both set up highlighting/rendering; ensure the lazy loader is shared, not duplicated per component.

---

## Estimated Net Reduction

- **Bundle:** large — deferring `shiki` + `mermaid` + `@xyflow` off the initial chunk is the headline win (initial JS should drop well below the current ~2.77 MB; exact figure to confirm after split).
- **Files:** −1 to −2 (`shimmer.tsx`, optionally `use-mobile.ts`).
- **LOC:** ~−80 in `use-live-agent.ts` via helpers.

---

## Do Not Touch (user-visible)

- Any ai-element with ≥1 reference (rendering/behavior).
- Audio pipeline (`audio.ts`) sample rates, worklet buffer, playback scheduling — audio quality contract.
- Camera facing-mode fallbacks (`camera.ts`) — device compatibility.
- Persona/VoiceDock visuals, transcript rendering.
- The Workflow graph itself — only *how* it loads changes, not what it shows.

---

## Prioritized Recommendations

1. **Code-split `@xyflow` Workflow view** (`React.lazy` on `WorkflowView`) — biggest bundle win, trivial, zero UX change (already behind a toggle).
2. **Lazy-load `shiki` and `mermaid`** in `code-block`/`message`.
3. **F1** consolidate message-part upsert helpers.
4. **Remove `shimmer.tsx`** (verified dead) and unused type exports.
5. Prune/wire `use-mobile.ts`.
