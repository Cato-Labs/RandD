# STR QC Agent — Core, Persona, Tools & Guardrails Audit

**Audit date:** 2026-07-06  
**Scope:** `apps/agent/src/strqc_agent/` (assembly, persona, context, guardrails, tools, console) and `apps/agent/tests/*.py`.  
**Source of truth:** `AGENTS.md` (PRD incl. Addenda 1 & 2) and `TASKS.md` milestones M2–M3.  
**Read-only audit:** no code files were modified.

---

## Executive Summary

The `apps/agent` package contains a **partial but testable STR QC BIDI agent** built on the Strands `BidiAgent` + Gemini Live model. The agent assembles, carries a coherent field-companion persona, and exposes a working set of core domain tools (camera, journal, stages, work orders, property brief, Slack delivery). All 22 tests in `apps/agent/tests` pass when run with the correct `PYTHONPATH`.

**What is implemented:**
- `BidiAgent` assembly with `BidiGeminiLiveModel` defaulting to `gemini-3.1-flash-live-preview` (`assemble.py:48`).
- A versioned, safety-first system prompt / persona (`persona.py:1`).
- Tool registry with typed schemas for camera, journal, stages, work orders, property brief, and report delivery.
- A pluggable capture backend and a swappable delivery adapter (`DryRunDelivery` / `SlackDelivery`).
- A confirmation guardrail hook before consequential tool calls (`guardrails.py:1`).
- Secret masking for property credentials (`property_info.py:1`).

**What is missing or incomplete (blocks v1):**
- **No memory / session persistence** (M2.4). `BidiAgent` is constructed without a `SessionManager`, and the agent’s state is in-memory only.
- **No telemetry / tracing** (M2.6). No OpenTelemetry, tool-call logging, or per-property audit trail is wired.
- **Missing required tools:** Google Maps/Sheets/Calendar/Docs (M3.4), Gmail email (M3.5), telephony (M3.7), Escapia PMS client (M4).
- **No tool-permission matrix by role** (M3.8). Every registered tool is available to every user; `stakeholder_role` is not consulted at tool call time.
- **No report assembly**. `deliver_report` only sends a pre-existing file path; no tool generates the self-contained embedded-photo report that M5.5 / Addendum 1 require.
- **Slack delivery is custom urllib**, not the native `strands_tools.slack` tool that Addendum 1 prescribed (M3.6).
- **Guardrails are narrow**: only URGENT work orders and `DONE`/`REPORT` stage advances require confirmation; HIGH-priority work orders, email, telephony, and report generation are unprotected by the hook.
- **Photo/checklist linkage gaps**: `record_checklist_result` has no `photo_memory_id` parameter, and `capture_photo` has no `space_id`/`asset_id`/`inspection_item_result_id` parameters, so the schema’s required evidence linkage is incomplete.

---

## Agent Assembly Status (M2.1)

| Item | Status | Evidence / Notes |
| --- | --- | --- |
| `BidiAgent` bootstrap | Implemented | `assemble.py:130` constructs `BidiAgent(model=model, tools=list(ALL_TOOLS), system_prompt=..., hooks=..., tool_executor=...)` |
| Gemini Live model | Implemented | `assemble.py:36-52` builds `BidiGeminiLiveModel(model_id=settings.strqc_gemini_model_id, ...)`; default is `gemini-3.1-flash-live-preview` (`shared/config.py:25`) |
| Provider fallbacks | Implemented | `assemble.py:23` supports `gemini` (default), `openai`, `nova` via model-specific vended classes |
| Thinking config | Implemented | `assemble.py:43-46` injects `thinking_config.thinking_level` from `STRQC_GEMINI_THINKING_LEVEL` and `enable_search` from `STRQC_GEMINI_ENABLE_SEARCH` |
| Injectable model for tests | Implemented | `build_agent(..., model=FakeBidiModel())` used in `test_assemble.py:27` |
| Sequential tool executor | Implemented | `assemble.py:137` uses `SequentialToolExecutor` to preserve `take_photo → journal → yolo_vision` ordering |
| `SessionManager` / memory | Missing | `assemble.py:102-140` never passes `session_manager`; in-memory `AgentState` only |
| Agent identification | Implemented | `name="the Keeper"`, `description="STR turnover quality-control field companion"` (`assemble.py:138-139`) |

### Observations

- The model configuration is clean and testable. `build_agent` is fully constructible without network because the Gemini Live connection is opened only on `agent.start()`.
- `SequentialToolExecutor` is the right choice for ordered field workflows, but note that the vision tools (`yolo_vision`, `take_photo`) are only loaded when `strands_fun_tools` + OpenCV are present (`tools/__init__.py:34-43`). In the current environment OpenCV is unavailable, so the agent assembles without them; the persona still references `yolo_vision` continuous detection, which will be impossible if the package is missing.
- The `session_manager` slot is a natural hook for the M2.4 memory work, but the vendored `strands-py` copy does not include the `strands.session` package; any memory implementation will need to use the full installed `strands` SDK (already present at `/opt/homebrew/lib/python3.14/site-packages/strands/`).

---

## Persona Audit (M2.2)

| Requirement | Status | Evidence |
| --- | --- | --- |
| Field-companion voice | Implemented | `persona.py:18-23` — warm, plain-spoken, direct, verbs first, one question at a time |
| Safety-first language | Implemented | `persona.py:25-28` — safety-critical items first, photo evidence required, failed safety item → work order immediately |
| Checklist discipline | Implemented | `persona.py:30-36` — work in order, PASS/FAIL/NA via journal, capture photo on fail/marginal, ground verdict in visible evidence |
| Terminology consistency | Implemented | `persona.py:22-23` — property/home, turnover, checklist item, work order, readiness, sign-off |
| Walkthrough vision | Implemented | `persona.py:38-44` — start `yolo_vision`, chain `take_photo → journal` |
| Consequential-action confirmation | Implemented | `persona.py:46-50` — ask before work orders, owner comms, stage advances, calls |
| Human override / honesty | Implemented | `persona.py:52-56` — never hide failures, human overrides stand, hand control back |
| Versioned prompt | Implemented | `persona.py:9` `PERSONA_VERSION = "1"`, embedded in prompt at `persona.py:12` |
| Per-property standing instructions | Implemented | `assemble.py:82-99` loads `unit_code`, `display_name`, `standing_instructions` and appends to system prompt (`persona.py:60-73`) |

### Observations

- The persona is well written and directly encodes the PRD’s tone and safety behavior. The test `test_build_agent_prompt_carries_persona_and_property_context` confirms the property brief and standing instructions are appended without secrets (`test_assemble.py:60-67`).
- The prompt does not explicitly tell the agent how to call the Daily Planning / route-planner behavior (M2.3). There is no tool for listing today’s tasks or generating a route; the persona can only discuss this if the model knows the database implicitly, which it cannot.
- There is no prompt guard against hallucinated QC verdicts beyond the general instruction to “ground every verdict in what you can actually see.” The reliability risk noted in AGENTS.md §Risks is not mitigated by any programmatic check (see Guardrails section).

---

## Tool-by-Tool Audit (M3.1–M3.8)

### Registered Tool Inventory

`ALL_TOOLS` in `tools/__init__.py:48-60` registers:

1. `list_checklist_items` (`journal.py:66`)
2. `record_checklist_result` (`journal.py:32`)
3. `capture_photo` (`camera.py:66`)
4. `open_work_order` (`work_orders.py:12`)
5. `list_open_work_orders` (`work_orders.py:46`)
6. `advance_stage` (`stages.py:14`)
7. `get_property_brief` (`property_info.py:25`)
8. `deliver_report` (`slack_delivery.py:130`)
9. Optional vision tools from `strands_fun_tools` (`tools/__init__.py:59`) — only if OpenCV is installed.

The assembly test verifies `EXPECTED_TOOLS <= set(agent.tool_names)` (`test_assemble.py:15-57`). All required tool names are present.

### Camera Tool (M3.1)

| Aspect | Status | Evidence / Notes |
| --- | --- | --- |
| `@tool` schema | Implemented | `camera.py:65-95` — parameters `caption`, `purpose`, `include_in_report` |
| `include_in_report` flag | Implemented | Schema default `false`; stored in `photo_memory.include_in_report` (`repositories.py:151-162`) |
| Content hash | Implemented | `camera.py:79` computes SHA-256 of captured bytes |
| Pluggable backend | Implemented | `CaptureBackend` protocol + `FileCaptureBackend` + `set_capture_backend` (`camera.py:26-63`) |
| `property_id` / `task_id` / `inspection_id` linkage | Partial | Stored via `repositories.add_photo`, but `space_id` and `asset_id` are **not** in the schema or DB (`photo_memory` lacks both columns) |
| `inspection_item_result_id` / `work_order_id` linkage | Missing | `photo_memory` has no such columns; `capture_photo` cannot tag a photo to a specific item result or work order |
| Real camera backend | Missing | `FileCaptureBackend` writes a placeholder text file (`camera.py:44-46`); real device capture is M7 frontend work |

**Gap:** The PRD §4 requires photos to link to `space_id`, `asset_id`, and either `inspection_item_result_id` or `work_order_id`. The current tool only links to the property/task/inspection level.

### Journal Tool (M3.2)

| Aspect | Status | Evidence / Notes |
| --- | --- | --- |
| `record_checklist_result` | Implemented | `journal.py:32-62` writes `inspection_item_result` with `result`, `notes`, `inspector_id` |
| Result validation | Implemented | `repositories.py:115-116` rejects anything other than `PASS`, `FAIL`, `NA` |
| Lazy inspection start | Implemented | `journal.py:14-28` starts an `inspection` row if `ctx.inspection_id` is unset |
| `list_checklist_items` | Implemented | `journal.py:66-86` returns items in category/display order with `required_photo` flag |
| Link photo to result | **Missing** | `record_checklist_result` has no `photo_memory_id` parameter, even though `repositories.record_item_result` supports it (`repositories.py:113-114`) |
| `space_id` / `asset_id` on result | Missing | `inspection_item_result` has no such columns; the PRD §3 requires them |

**Gap:** The natural workflow (`take_photo` → `record_checklist_result`) cannot associate the captured photo with the result row because the tool schema omits `photo_memory_id`.

### Photo Reasoning / QC Verification (M3.3)

| Aspect | Status | Evidence / Notes |
| --- | --- | --- |
| Model-layer multimodal input | Supported by model | `BidiGeminiLiveModel` accepts image input; `BidiImageInputEvent` exists in the SDK |
| Explicit photo-analysis tool | Missing | No `assess_photo` or similar tool; the agent must reason from images passed as input events |
| Baseline comparison | Missing | No per-property baseline photo store or comparison tool |
| Anomaly detection | Missing | No dedicated CV / anomaly tool; the agent relies on Gemini’s vision capabilities |

The PRD’s Addendum 1 correctly notes that photo understanding is a model-layer capability, but the agent still needs a workflow that *presents* captured photos to the model for verification. Today, the camera tool only stores the file; nothing passes the image back to the model for a structured verdict. This is an agent-design gap, not a missing model.

### Google Tools (M3.4)

| Tool | Status | Notes |
| --- | --- | --- |
| Google Maps directions | **Missing** | No tool; no `strands_google` import in `apps/agent` |
| Google Sheets task import | **Missing** | No tool |
| Google Calendar | **Missing** | No tool |
| Google Docs report export | **Missing** | No tool |
| OAuth token wiring | **Missing** | `gmail_auth.py` exists elsewhere but is not wired into `apps/agent` |

Settings placeholders exist for Google credentials (`shared/config.py:41-42`), but no tools are registered. The `console.py` comment mentions `strands_google` but it is not imported (`console.py:23`).

### Email Tool (M3.5)

| Aspect | Status | Notes |
| --- | --- | --- |
| Gmail send | **Missing** | No `send_email` tool in `apps/agent` |
| Report delivery via email | **Missing** | Delivery adapter is Slack-only; `Report.delivery_channel` is not used |

The `Report.delivery_channel` column supports `EMAIL`, but no adapter exists.

### Slack Tool (M3.6)

| Aspect | Status | Evidence / Notes |
| --- | --- | --- |
| Swappable adapter | Implemented | `DeliveryAdapter` protocol + `DryRunDelivery` + `SlackDelivery` (`slack_delivery.py:29-103`) |
| `files_upload_v2` flow | **Partial** | Uses the WebAPI `files.getUploadURLExternal` → upload → `files.completeUploadExternal` flow (the V2 implementation detail), but **not** the native `strands_tools.slack` tool prescribed by Addendum 1 |
| `slack_send_message` equivalent | Implemented | `completeUploadExternal` carries `initial_comment` (`slack_delivery.py:96`) |
| No-network default | Implemented | `make_delivery_adapter` defaults to `DryRunDelivery` when `SLACK_BOT_TOKEN` is empty (`slack_delivery.py:105-110`) |
| DB delivery status update | **Missing** | `deliver_report` returns a status dict but does not update `report.delivery_status` / `delivered_at` |
| Bot token handling | Implemented | `Settings.slack_bot_token` and `Settings.slack_default_channel_id` (`shared/config.py:45-46`) |

**Deviation from Addendum 1:** The PRD explicitly states the report-delivery step should call the native `strands_tools.slack` tool with `slack(action="files_upload_v2", ...)` and `slack_send_message`. The current implementation is a custom urllib wrapper. It is functionally equivalent for v1, but it is not the “native” tool the PRD requires, and it will be harder to extend to Teams/Email later (those are whole new adapter classes rather than a unified channel dispatcher).

### Telephony Tool (M3.7)

| Aspect | Status |
| --- | --- |
| Outbound calls | **Missing** |
| Twilio or other provider integration | **Missing** |
| Tool-permission for calls | N/A — not implemented |

The persona mentions “placing a call” as a consequential action (`persona.py:48`), but no telephony tool exists.

### Stages Tool (M2.3 / M3.x)

| Aspect | Status | Evidence / Notes |
| --- | --- | --- |
| Stage keys | Implemented | `stages.py:10` defines `QC, B2B, CLN, DONE, OWN, WO, DONE_WO, REPORT` |
| Advancement + event recording | Implemented | `stages.py:14-31` calls `repositories.set_task_stage` which updates `task.current_stage_definition_id` and upserts `task_stage_event` (`repositories.py:69-94`) |
| Unknown-key rejection | Implemented | `repositories.py:75-76` raises `ValueError` |
| Stage-order enforcement | **Missing** | `advance_stage` can jump from `CLN` directly to `REPORT` or `WO` without requiring intermediate stages; no state machine |
| Notification triggers | **Missing** | `notification_trigger` table is seeded but no code fires triggers on stage changes |

### Work Order Tools (M5.3)

| Aspect | Status | Evidence / Notes |
| --- | --- | --- |
| `open_work_order` | Implemented | `work_orders.py:12-42` creates `work_order` and links to `source_item_result_ids` via `work_order_source_item` |
| Priority enum | Implemented | `LOW`, `MEDIUM`, `HIGH`, `URGENT` validated in `repositories.py:172-173` |
| `list_open_work_orders` | Implemented | `work_orders.py:46-65` returns non-DONE/CANCELLED rows |
| Status lifecycle | **Partial** | Schema supports `NEW → ASSIGNED → IN_PROGRESS → BLOCKED → DONE → CANCELLED`, but no tool transitions status |
| Escapia write-back | **Missing** | `work_order.escapia_work_order_native_pms_id` exists (`0002_addendum_1_2.sql:23`) but no integration code |
| Facilities assignment | **Missing** | `assigned_facilities_stakeholder_id` is not set by the tool |

### Property Brief Tool

| Aspect | Status | Evidence / Notes |
| --- | --- | --- |
| Schema | Implemented | `property_info.py:25-69` |
| Secret masking | Implemented | Ciphertext/ref columns are popped; only a masked `••••` value is returned (`property_info.py:58-59`) |
| Features list | Implemented | Returns `property_feature` rows with name, location, quantity |
| Standing instructions | Implemented | Included in output |

**Security note:** `strqc_shared.crypto.mask_secret` returns `••••` + last character for inputs longer than 4 characters (`packages/shared/src/strqc_shared/crypto.py:67-71`). The property-brief tool passes the literal string `"****"` to it, so the test passes, but a real ciphertext would leak its final character. This is a latent information-disclosure bug in the shared crypto helper, not in the agent itself.

### Tool-Permission Matrix by Role (M3.8)

| Aspect | Status | Notes |
| --- | --- | --- |
| Role-based tool filtering | **Missing** | `build_agent` passes `tools=list(ALL_TOOLS)` to every agent; no role check |
| `stakeholder_role` usage | **Missing** | The DB has `stakeholder_role` and the context has `stakeholder_id`, but no matrix maps roles → allowed tools |
| Per-tool authorization hook | **Missing** | `ConfirmationGuardrail` is the only hook; it is role-agnostic |

This is a v1 security blocker (M3.8 is marked with a lock in `TASKS.md`). A housekeeper should not be able to call `deliver_report` or `advance_stage(REPORT)`.

---

## Guardrails Audit (M2.5)

| Requirement | Status | Evidence |
| --- | --- | --- |
| Consequential-action confirmation | Partial | `guardrails.py:27-40` flags `deliver_report`, `open_work_order` only when `priority=URGENT`, and `advance_stage` only for `DONE`/`REPORT` |
| Hook cancels unconfirmed calls | Implemented | `guardrails.py:66-79` sets `event.cancel_tool` with a helpful message |
| One-shot grants | Implemented | `guardrails.py:50-59` — `grant()` allows the next call, then the grant is consumed |
| Revoke grants | Implemented | `guardrails.py:57-59` |
| Both BIDI and non-BIDI events | Implemented | `guardrails.py:61-64` registers on `BeforeToolCallEvent` and `BidiBeforeToolCallEvent` |
| Hallucination / photo-grounded check | **Missing** | No guardrail verifies that a `FAIL` verdict has a photo or that the image supports the claim |
| Telephony confirmation | N/A | Telephony tool does not exist |
| Email confirmation | **Missing** | Email tool does not exist, but `deliver_report` to Slack is covered |
| HIGH-priority work order confirmation | **Missing** | Only `URGENT` triggers confirmation; `HIGH` does not |
| `advance_stage(WO)` / `DONE_WO` / `OWN` confirmation | **Missing** | Only `DONE`/`REPORT` are considered consequential |

### Policy Observations

- The guardrail policy is correctly conservative for the actions it covers, but it under-covers the PRD’s intent. The persona tells the agent to ask before any work order, report, stage advance, or call; the hook only enforces a subset.
- There is no defense against the model marking a safety-critical item PASS without evidence. The PRD’s AI-reliability mitigation (“hybrid workflows, AI suggestions + human override, clear visual evidence”) is present in the prompt but not in code.

---

## Memory and Telemetry Status (M2.4, M2.6)

| Requirement | Status | Evidence |
| --- | --- | --- |
| Persistent memory / `SessionManager` | **Missing** | `assemble.py:102-140` does not pass `session_manager`; `BidiAgent` uses in-memory `AgentState` only (`strands-py/src/strands/experimental/bidi/agent/agent.py:134-142`) |
| Cross-session continuity | **Missing** | No memory store integrated |
| `strands.memory` / `MemoryManager` tools | **Not wired** | A reference `backend/app/memory.py` exists but is not imported or used by `apps/agent` |
| Operational context per property/stakeholder | **Missing** | `AgentRunContext` is transient per `build_agent` call |
| OpenTelemetry / tracing on tool calls | **Missing** | No observability hooks beyond the confirmation guardrail |
| Tool-call audit log | **Missing** | No table records every tool invocation and result for auditability |
| Per-property verdict audit trail | **Missing** | `inspection_item_result` captures verdicts, but not the model/tool reasoning that produced them |

A reference memory implementation exists in `backend/app/memory.py`, which uses `strands.memory.MemoryManager` over a Bedrock Knowledge Base. However, it is not integrated into the current `apps/agent` package and should not be considered implemented for the v1 agent.

---

## Test Results

Command run:

```bash
PYTHONPATH="/Users/tims-stuff/RandD/RandD/apps/agent/src:/Users/tims-stuff/RandD/RandD/packages/db/src:/Users/tims-stuff/RandD/RandD/packages/shared/src:/Users/tims-stuff/RandD/RandD/strands-py/src" \
  python3 -m pytest apps/agent/tests -q
```

Result:

```text
......................
22 passed, 1 warning in 0.18s
```

The single warning is:

```text
PytestConfigWarning: Unknown config option: asyncio_mode
```

This is benign — the `pytest-asyncio` package is not installed in the environment, so the `asyncio_mode = "auto"` setting in `pyproject.toml` is ignored. None of the current tests exercise async behavior, so this does not affect coverage.

### Test Coverage by File

| File | Tests | What they cover |
| --- | --- | --- |
| `test_assemble.py` | 4 | Fake model protocol, tool registration, system prompt content, property context append |
| `test_guardrails.py` | 6 | Policy matrix, hook cancellation, one-shot grants, revoke |
| `test_delivery.py` | 4 | Slack 3-step upload flow, failure handling, dry-run fallback, `deliver_report` tool |
| `test_tools.py` | 8 | Checklist listing, result recording, rejection of bad verdicts, camera capture + hash, default file backend, work order source-item linking, stage advancement, property-brief secret masking |

### Gaps in Tests

- No tests for the **Slack native tool requirement** (because a custom implementation is tested instead).
- No tests for **memory**, **telemetry**, **Google tools**, **email**, **telephony**, or **role-based permissions** (all missing features).
- No tests for **stage-order enforcement** or **notification triggers**.
- No tests for **report generation** or **delivery status DB updates**.

---

## Risks and Recommendations

| Risk | Severity | Recommendation |
| --- | --- | --- |
| **No role-based tool permissions** | High / v1 blocker | Implement `ToolFilterHook` or a `RoleToolMatrix` that checks `stakeholder_role` before each tool call. Start with default deny: only allow listed tools per role. |
| **No memory / session persistence** | High | Wire `strands.memory.MemoryManager` tools into `ALL_TOOLS` or pass a `SessionManager` to `BidiAgent`. Define memory scope (per-property standing notes, last-turn context, crew preferences). |
| **Guardrail under-coverage** | Medium | Expand `requires_confirmation` to cover `HIGH` work orders, all `advance_stage` calls to `WO`/`DONE_WO`/`OWN`/`DONE`/`REPORT`, and any future email/telephony tools. Add a separate hallucination guardrail that requires a `photo_memory_id` for `FAIL` results on safety-critical items. |
| **Custom Slack instead of native tool** | Medium | Replace the custom `SlackDelivery` urllib wrapper with the `strands_tools.slack` tool’s `files_upload_v2` + `slack_send_message`. Keep the adapter pattern, but have the adapter invoke the native tool rather than raw HTTP. |
| **Missing Google / email / telephony** | High | Add `strands-google` tools (Maps, Sheets, Calendar, Docs), a Gmail `send_email` tool, and a Twilio (or chosen provider) telephony tool. The PRD treats these as v1 integrations. |
| **No report generation** | High | Build a `generate_report` tool or service that assembles a self-contained report with embedded `include_in_report=1` photos, category summaries, work order status, and sign-off. Then update `deliver_report` to use the generated file and set `Report.delivery_status`. |
| **Photo ↔ checklist linkage gaps** | Medium | Add `photo_memory_id` to `record_checklist_result`, and add `space_id`/`asset_id`/`inspection_item_result_id` to `photo_memory` and the capture tool. Link the captured photo to the result automatically when the agent chains `capture_photo → record_checklist_result`. |
| **Stage state machine** | Medium | Enforce valid stage transitions in `advance_stage` (e.g., cannot skip `DONE_WO` before `DONE`, cannot reach `REPORT` while open work orders exist). |
| **Secret mask leaks final character** | Low | Fix `strqc_shared.crypto.mask_secret` to return a fixed mask regardless of input length. |
| **No telemetry** | Medium | Add OpenTelemetry or at least a structured log/table of every tool call, input, result, and model event for auditability. |
| **Vision tools conditionally absent** | Low | Make `strands_fun_tools` a proper dependency or remove the persona’s reliance on `yolo_vision` if it cannot be guaranteed in production. |

---

## Requirement Mapping Checklist

| Requirement | Source | Status | Evidence / Gap |
| --- | --- | --- | --- |
| Agent bootstrap with `BidiAgent` + Gemini Live | M2.1 | ✅ | `assemble.py:130`, `BidiGeminiLiveModel` default `gemini-3.1-flash-live-preview` |
| System prompt / persona (field-companion, safety-first, checklist discipline, terminology) | M2.2 | ✅ | `persona.py:1` |
| Daily Planning behavior | M2.3 | ❌ | No route-planning or task-list tool; agent cannot list today’s tasks |
| Checklist Guidance behavior | M2.3 | ✅ | `list_checklist_items`, `record_checklist_result` |
| QC Verification behavior | M2.3 | 🟡 | Model can see images, but no explicit tool/workflow to verify photos and mark verdicts |
| Issue Routing behavior | M2.3 | 🟡 | `open_work_order` exists, but no automatic creation from failed items, no facilities assignment |
| Owner Communication behavior | M2.3 | 🟡 | `deliver_report` exists, but no report generation tool or automatic sign-off dispatch |
| Memory | M2.4 | ❌ | No `SessionManager`, no memory tools |
| Confirmation before destructive actions | M2.5 | 🟡 | `ConfirmationGuardrail` covers subset; misses HIGH work orders, several stages, email, telephony |
| Hallucination checks | M2.5 | ❌ | No programmatic guardrail; only prompt instruction |
| Telemetry / tracing | M2.6 | ❌ | No OpenTelemetry or tool-call audit logging |
| Camera tool | M3.1 | 🟡 | Schema exists, backend is pluggable, but `space_id`/`asset_id`/`inspection_item_result_id` missing |
| Journal tool | M3.2 | 🟡 | Writes verdicts, but cannot link a photo to a result |
| Photo reasoning (multimodal assessment) | M3.3 | 🟡 | Model-native vision is available, but no structured assessment tool/workflow |
| Google tools (Maps, Sheets, Calendar, Docs) | M3.4 | ❌ | Not present |
| Email tool | M3.5 | ❌ | Not present |
| Slack tool (`files_upload_v2`, `slack_send_message`, swappable adapter) | M3.6 | 🟡 | Adapter is swappable and Slack-first, but uses custom urllib, not native `strands_tools.slack` |
| Telephony tool | M3.7 | ❌ | Not present |
| Tool-permission matrix by role | M3.8 | ❌ | Not implemented; all tools available to all users |
| Addendum-1 fields in schema (`Report.delivery_*`, `Photo.include_in_report`) | M1.2 | ✅ | `0002_addendum_1_2.sql:7-16`; `repositories.add_photo` supports `include_in_report` |
| Addendum-2 fields in schema (Escapia IDs, `SyncCursor`, `HousekeepingStatusMap`) | M1.3–M1.5 | ✅ | `0002_addendum_1_2.sql:18-60` |
| Escapia client / custom tool | M4 | ❌ | Not in `apps/agent`; only in `apps/api/src/strqc_api/escapia/` (out of this audit scope) |

---

## Overall Assessment

`apps/agent` is a solid foundation for the STR QC agent: it assembles cleanly on `BidiGeminiLiveModel`, carries a strong persona, and has working tools for the checklist/stage/work-order core loop. However, it is still missing the **memory**, **telemetry**, **Google/Email/Telephony integrations**, **role-based permissions**, and **report generation** pieces that the PRD marks as v1 requirements. The biggest near-term risks are the **absence of a role-based tool matrix** (a security blocker) and the **incomplete photo↔checklist linkage** (a data-integrity issue for the audit trail). The Slack delivery works but should be aligned with the native `strands_tools.slack` tool per Addendum 1 before v1 ships.
