# Agent Core & Tools — Simplification Audit

**Date:** 2026-07-06 · **Read-only** · Companion to skeptic report [02](../02-agent-tools.md)

**Constraint:** Preserve all requirements, features, and experience. Internal simplification only.

---

## Executive Summary

The single biggest simplification in the entire repo lives here: **two agent stacks implement the same tools twice** — `apps/agent/src/strqc_agent/` (DB-backed "the Keeper") and `backend/app/` (meta-tooling "RandD Live", which also carries camera/journal/slack/memory tools). Camera, journal, Slack delivery, and memory each exist in two incompatible forms. Consolidating to one canonical implementation is the largest LOC reduction available without dropping any feature.

Secondary wins: duplicated `build_model`, over-used module-global singletons, and repeated per-tool boilerplate.

---

## Incorporated Skeptic Findings

- Skeptic #2: agent assembles; missing memory/telemetry/google/email/telephony/role-permissions; Slack is custom urllib not native `strands_tools.slack`; photo↔checklist linkage gaps.
- Skeptic #4: confirmed two agents with overlapping-but-incompatible tools; the `/ws` bridge runs the meta-tooling agent, not the Keeper.

Simplification reframes: **don't build the missing tool twice** — pick one home, then the "missing" items are added once.

---

## Duplication Between the Two Agent Stacks (most important)

| Capability | `apps/agent` (Keeper) | `backend/app` (RandD Live) | Recommendation |
|-----------|-----------------------|----------------------------|----------------|
| Camera capture | `tools/camera.py` (CaptureBackend protocol → `photo_memory`) | `camera_control.py` + `capture_tools.py` + `browser_camera.py` (local files) | Keep one. The DB-backed Keeper tool is the product path; the browser-stream plumbing (`browser_camera`, `control_camera`) is the *transport* and can be shared beneath one tool. |
| Journal / checklist | `tools/journal.py` (writes `inspection_item_result`) | `qc_journal.py` (hardcoded dict, no DB) | Keep the DB-backed one; delete the hardcoded checklist once the bridge uses the Keeper. |
| Slack delivery | `tools/slack_delivery.py` (adapter, urllib `files_upload_v2` flow) | `slack_report.py` (`slack_sdk.files_upload_v2`) + native `slack`/`slack_send_message` | One delivery path. Skeptic prefers native `strands_tools.slack`; using it removes the custom urllib adapter body. |
| Memory | none wired | `memory.py` (Bedrock KB) | One memory module, imported by the canonical agent. |
| Provider `build_model` | `assemble.py:26` | `agent.py:114` | **Near-identical** gemini/openai/nova construction — extract one shared builder. |

> Verified: `rg "def build_model"` returns exactly these two definitions.

Consolidating removes an entire parallel tool set (~several hundred LOC across `qc_journal.py`, one of the two camera stacks, one Slack path, one `build_model`).

---

## Simplification Opportunities

| # | Opportunity | Safe because | Reduction | Risk |
|---|-------------|--------------|-----------|------|
| A1 | Extract a single `build_model(provider, config)` into `packages/shared` (or `strqc_agent`) and have both agents call it | Identical construction logic today | ~60 LOC, one source | Med (cross-package import) |
| A2 | Choose the DB-backed Keeper tools as canonical; retire `backend/app/qc_journal.py` hardcoded checklist | Same checklist lives in DB templates already | −~120 LOC | Med (bridge must use Keeper) |
| A3 | Have `SlackDelivery` invoke native `strands_tools.slack` instead of hand-rolled urllib multi-step upload | Same Slack result; less code; aligns with Addendum 1 | −~50 LOC | Low-Med |
| A4 | Collapse per-tool boilerplate (`ctx = get_context(); conn = ctx.get_conn(); try/finally close; error dict`) into a small `@qc_tool` decorator or `with ctx.conn()` context manager | Pure refactor of identical patterns across `journal.py`, `work_orders.py`, `stages.py`, `property_info.py` | ~40–60 LOC | Low |
| A5 | Drop the `provider_config` copy-on-write gymnastics in `assemble.py:41-46` in favor of a small helper | Same resulting config | minor | Low |

---

## Abstraction Reduction (adapters / protocols / singletons)

- **CaptureBackend protocol** is currently justified (tests inject a fake; frontend supplies the real one) — keep, but it needs only the methods actually used; trim any unused protocol members.
- **DeliveryAdapter** protocol is worth keeping (Slack v1, Email/Teams later per Addendum 1) — but the concrete `SlackDelivery` body should delegate to the native tool (A3) rather than reimplement upload.
- **Module-global singletons** (`_current` context, `_capture_backend`, `_delivery_adapter`) are three separate globals set in lockstep by `build_agent`. Consider folding into the single `AgentRunContext` (context already exists) so there is one thing to set/clear. Reduces three global-mutation seams to one.

---

## Dependency Reduction

- If the Keeper becomes canonical and the bridge uses it, `backend/app` sheds `qc_journal` and possibly one Slack path; net fewer imports on the hot `/ws` path.

---

## Estimated Net Reduction

- LOC: **~−300** across duplicate tools + `build_model` + boilerplate (conservative).
- Files: **−1 to −2** (`qc_journal.py`; possibly one camera module merged).
- Conceptual: one agent, one tool set, one model builder.

---

## Do Not Touch (would change behavior/experience)

- Persona content (`persona.py`) — behavioral contract; only trim if a line is provably redundant.
- `SequentialToolExecutor` choice — ordering matters for `take_photo → journal`.
- Guardrail confirmation semantics — safety behavior.
- Result/priority validation and stage keys.

---

## Prioritized Recommendations

1. **A2 + bridge wiring** — pick the Keeper as the single agent; retire the hardcoded backend journal. Biggest LOC + clarity win, and resolves the skeptic's "wrong agent on /ws".
2. **A1** — one shared `build_model`.
3. **A3** — Slack via native tool (less code, matches Addendum 1).
4. **A4** — per-tool boilerplate helper.
5. **Singleton fold** into `AgentRunContext`.
