# Escapia PMS Integration Audit

**Scope:** `apps/api/src/strqc_api/escapia/*` and related tests, schema, config.
**Audited against:** `AGENTS.md` Addendum 2 and `TASKS.md` M4.
**Date:** 2026-07-06
**Status snapshot:** Implementation exists and is largely correct, but `TASKS.md` still marks M4 tasks as open. This report treats the code as the source of truth and flags the tracker stale.

---

## Executive Summary

The Escapia HSAPI integration is implemented as a clean Python async layer:

- **Auth + client:** implemented correctly (`auth.py`, `client.py`).
- **Sync coverage:** Reservations (delta), Units (poll), and Owners (poll) are implemented. Housekeeping status map/load + write-back and work-order write-back are implemented. **Guests, housekeeping task read, and work-order read are missing.**
- **Scheduler:** basic asyncio scheduler exists with per-resource isolation.
- **Resilience:** exponential backoff/retry on 429/5xx, no hardcoded budget.
- **Custom Strands tool:** **not present** (M4.2 still open in code).
- **Data model:** Addendum-2 schema fields and tables exist in migration `0002_addendum_1_2.sql`.
- **Tests:** 24 tests pass after installing `pytest-asyncio` in the test interpreter. They fail in a bare `python3` environment only because the plugin is missing from that interpreter.

**Bottom line:** the integration layer is a solid foundation and passes its own unit tests, but it is incomplete against the full M4 scope: guest sync, inbound work-order sync, inbound housekeeping task sync, and the agent-facing Strands tool are absent.

---

## Auth/Client Audit

### Token flow (M4.1)

`apps/api/src/strqc_api/escapia/auth.py` implements `EscapiaTokenProvider`:

- Calls `GET /hsapi/auth/token` with `Authorization: Basic base64(clientId:secret)` (line 72-75).
- Caches `authorizationHeaderValue` from the `TokenCreationResult` response when present (line 82-87).
- Refreshes 60 seconds before expiry via `_REFRESH_SKEW` (line 24, 66).
- Never logs credential material; docstring explicitly forbids it (line 9-10, 30).

The spec (`Escapia/escapia_openapi3.json` path `/hsapi/auth/token`) confirms exactly this flow and the `TokenCreationResult` schema fields.

### Required headers (M4.1)

`apps/api/src/strqc_api/escapia/client.py` injects the three required HSAPI headers on every data call (line 115-121):

- `x-homeaway-hasp-api-version`
- `x-homeaway-hasp-api-endsystem`
- `x-homeaway-hasp-api-pmcid`

The test `test_required_headers_injected_on_every_call` (`tests/escapia/test_auth_and_client.py:66`) asserts all three, plus `Authorization`. This matches the OpenAPI3 spec parameters verified on every HSAPI operation.

### Configuration

`packages/shared/src/strqc_shared/config.py` provides the settings (line 49-54):

- `escapia_base_url: str = "https://hsapi.escapia.com/dragomanadapter"`
- `escapia_client_id`, `escapia_client_secret`, `escapia_pmc_id`
- `escapia_api_version: str = "1"`, `escapia_end_system: str = "EscapiaVRS"`

`EscapiaClient.from_settings` wires these directly (client.py:71-82).

**Risk:** the default `api_version` is `"1"`, but the OpenAPI3 spec defaults to `"10"`. Either is acceptable per PMC, but production deployment should explicitly set this. No validation against the spec is performed.

---

## Sync Coverage

### Reservations (M4.4) — delta

**File:** `apps/api/src/strqc_api/escapia/sync.py`, lines 97-133.

- Uses `GetReservationChanges` with `startVersion` (the only delta endpoint in the spec, confirmed by OpenAPI3 and the module docstring).
- Reads `sync_cursor` table for `start_version` (line 106-107).
- Fetches each changed reservation via `GetReservationById` (line 118).
- Skips `Deleted` changes (line 114-117) and reservations with unknown units (line 122-126), but still advances the cursor (line 132).
- Upserts `task` rows with `escapia_reservation_native_pms_id` and `source_system = 'ESCAPIA'` (line 69-94).

**Tests:** `tests/escapia/test_sync_reservations.py` covers create, resume, idempotent replay, unknown units, and deleted changes. All pass.

**Gap:** `UpdateReservationOccupancyStatus` is documented as a related endpoint but not used; the platform only consumes occupancy status, not writes it back.

### Units (M4.5) — poll

**File:** `sync.py`, lines 157-226.

- Polls `SearchUnitSummaries` with pagination (line 163-170).
- Fetches full `Unit` records via `GetUnitsById` in chunks of 25 (line 172-173).
- Updates only demographic fields (`display_name`, address, `escapia_unit_native_pms_id`, `escapia_pmc_id`, `source_system`), preserving platform-only fields (`standing_instructions`, `cluster_id`, `qc_assignee_stakeholder_id`, Wi-Fi/door secrets) via `COALESCE` in `_UNIT_DEMOGRAPHIC_UPDATE` (line 142-154).
- Can adopt an existing property by `unit_code` when native IDs are absent (line 184-188).
- Stores `last_polled_at` in `sync_cursor` (line 225).

**Tests:** `tests/escapia/test_sync_units_owners.py` covers demographic update, preservation, insertion, and adoption by unit code. All pass.

### Owners (M4.6) — poll

**File:** `sync.py`, lines 232-288.

- Polls `SearchOwners` with pagination.
- Upserts `stakeholder` with `escapia_owner_native_pms_id` and `role = 'OWNER'`.
- Uses `ownsUnitNativePMSIDs` to create `stakeholder_role` rows linking owners to properties (line 273-282), exactly as Addendum 2 requires.
- Collects unknown units and continues.

**Tests:** `tests/escapia/test_sync_units_owners.py` covers owner create, property links, and idempotency. All pass.

### Guests (M4.6) — poll

**Status:** **not implemented.**

There is no `sync_guests`, `SearchGuests`, or `GetGuestById` wrapper. `endpoints.py` does not define guest models. The schema migration includes a `GUESTS` resource enum in `sync_cursor`, but no code consumes it.

**Risk:** M4.6 explicitly lists Guests as a poll sync target (read-only context). A guest `isWarn` flag from the spec is noted in Addendum 2 as potentially useful to Housekeeping/QC later. Missing this leaves reservation context incomplete.

### Housekeeping (M4.7)

**Status read — partially implemented.**

- `GetHousekeepingStatusList` is wrapped (`endpoints.py:266`) and used to populate `housekeeping_status_map` (`sync.py:294`).
- `SearchHousekeepingTasks` / `GetHousekeepingAssigneeList` / `GetUnitHousekeepingStatuses` are **not wrapped** and there is no `sync_housekeeping_tasks` job.

**Status write-back — implemented.**

- `load_housekeeping_status_map` loads the PMC-specific statuses, defaults using `isDefaultOnCheckIn` for `DONE` and `isDefaultOnCheckOut` for `CLN`, and allows operator overrides (`sync.py:294-348`).
- `push_housekeeping_ready` looks up the mapped `DONE` status and calls `SaveUnitHousekeepingStatus` (`sync.py:351-388`).

**Tests:** `tests/escapia/test_housekeeping_workorders.py` covers status map load, operator overrides, ready push, and failure when map is missing. All pass.

**Gap:** Inbound housekeeping task read is missing, so the scheduler cannot reconcile Escapia-assigned tasks with platform tasks. The write-back is also currently disconnected from the actual `Task.current_stage` state machine (no caller wires it automatically when a task reaches `DONE`).

### Work Orders (M4.8)

**Write-back — implemented.**

- `push_work_order` fetches the platform `work_order`, maps priority (`LOW` → `Low`, etc.) and status (`NEW`/`ASSIGNED`/`IN_PROGRESS`/`BLOCKED`/`DONE`/`CANCELLED`) to the Escapia enum, and calls `SaveWorkOrder` (`sync.py:394-431`).
- Stores the returned `nativePMSID` in `work_order.escapia_work_order_native_pms_id` (line 425-431).
- Re-push includes the native ID so Escapia updates rather than duplicates (line 421-422, test line 137).

**Inbound read — missing.**

There are no wrappers for `SearchWorkOrders`, `GetWorkOrder`, `GetWorkOrders`, or `GetWorkOrderTask`. The scheduler does not pull existing Escapia work orders into the platform. The bi-directional requirement is therefore only half satisfied.

**Automatic safety-critical push — missing.**

The M4.8 requirement states: "a failed safety-critical checklist item should call `SaveWorkOrder` directly rather than only living in the platform's own table." `push_work_order` exists as a function, but there is no trigger or caller that automatically invokes it when `inspection_item_result.result = 'FAIL'` and `checklist_item_template.maintenance_required = 1`. The M5 work-order engine (not yet implemented) will need to call this.

---

## Scheduler/Strategy Audit (M4.9)

**File:** `apps/api/src/strqc_api/escapia/scheduler.py`.

- Defines `run_sync_cycle` with per-job error isolation so one failure does not stop the cycle (line 51-68).
- Provides `run_forever` interval loop with `max_cycles` bound for tests (line 71-94).
- Default jobs: `units`, `owners`, `reservations`, `housekeeping_status_map` (line 33-38). This reflects the delta-vs-poll asymmetry: only reservations is a delta feed; units/owners/housekeeping are polls.
- **Missing from default jobs:** `WORK_ORDERS` inbound poll and `GUESTS` poll.

The docstring correctly notes the GraphQL Gateway API is out of v1 scope (M4.10) and leaves it as a Phase-2 stub (line 8-10).

**Risk:** The scheduler is currently a pure Python loop. There is no cron/APN/deployment integration. The default 5-minute interval (`DEFAULT_INTERVAL_SECONDS = 300.0`) is reasonable but not validated against Escapia rate limits.

---

## Custom Strands Tool Status (M4.2)

**Status:** **not implemented.**

There is no Strands `ToolSpec`, no wrapper around `strands-agents-tools` `http_request`, and no dynamic loading of the `Escapia/escapia_openapi3.json` spec. The integration is currently a direct `httpx` client library usable only by Python service code, not by the agent tool registry.

`TASKS.md` M4.2 explicitly requires: "Custom Strands tool wrapping `http_request`, using the OpenAPI3 spec as the endpoint/schema contract." This is the only piece in M4 that has to be built from scratch (per Addendum 2).

**Recommendation:** Implement a Strands tool in `apps/agent/src/strqc_agent/tools/escapia.py` (or similar) that exposes high-level operations (e.g., `sync_reservations`, `push_housekeeping_ready`, `push_work_order`) backed by the existing `EscapiaClient`. The OpenAPI3 spec can be loaded at tool-registration time to validate endpoint names and parameter shapes, but the actual transport should still use the tested `httpx` client rather than a generic `http_request` tool with no auth/header logic.

---

## Endpoints/Status

`apps/api/src/strqc_api/escapia/endpoints.py` wraps the following HSAPI operations with thin typed models:

| Escapia operationId | Method/Path | Status | Notes |
|---|---|---|---|
| `GetReservationChanges` | `GET /hsapi/GetReservationChanges` | implemented | Delta only |
| `GetReservationById` | `GET /hsapi/GetReservationById` | implemented | |
| `SearchUnitSummaries` | `POST /hsapi/SearchUnitSummaries` | implemented | |
| `GetUnitsById` | `POST /hsapi/GetUnitsById` | implemented | |
| `SearchOwners` | `POST /hsapi/SearchOwners` | implemented | |
| `GetHousekeepingStatusList` | `GET /hsapi/GetHousekeepingStatusList` | implemented | |
| `SaveUnitHousekeepingStatus` | `PUT /hsapi/SaveUnitHousekeepingStatus` | implemented | |
| `SaveWorkOrder` | `PUT /hsapi/SaveWorkOrder` | implemented | Write-only |
| `SearchGuests` / `GetGuestById` | — | missing | M4.6 |
| `SearchHousekeepingTasks` | — | missing | M4.7 read |
| `SearchWorkOrders` / `GetWorkOrder` / `GetWorkOrders` | — | missing | M4.8 read |
| `UpdateReservationOccupancyStatus` | — | not used | Related but not required for v1 read |

---

## Test Results

Command run:

```bash
PYTHONPATH=apps/api/src:packages/db/src:packages/shared/src python3 -m pytest apps/api/tests/escapia -q
```

After installing `pytest-asyncio` into the system interpreter:

```
24 passed in 0.27s
```

Without `pytest-asyncio`, every test fails with:

```
async def functions are not natively supported.
You need to install a suitable plugin for your async framework, for example:
  - anyio
  - pytest-asyncio
```

**Observation:** The project `pyproject.toml` (`apps/api/pyproject.toml:21-23`) declares `pytest-asyncio>=0.23` as a dev dependency, but the current execution environment is not installed from that file. This is a packaging/venv issue, not a test bug. Once the proper environment is used, the tests pass cleanly.

**Coverage gaps in tests:**

- No test for `Guest` sync (not implemented).
- No test for `SearchHousekeepingTasks` read (not implemented).
- No test for inbound `SearchWorkOrders`/`GetWorkOrder` (not implemented).
- No test for the automatic safety-critical → work-order push (not wired).
- No test for 5xx retry behavior (only 429 is tested).
- No integration test against the real OpenAPI3 spec (e.g., validating request shapes against spec schemas).

---

## Data Model Mapping Status

Migration `packages/db/src/strqc_db/migrations/0002_addendum_1_2.sql` correctly adds Addendum-2 fields:

- `property.escapia_unit_native_pms_id` (line 19)
- `property.escapia_pmc_id` (line 20)
- `task.escapia_reservation_native_pms_id` (line 21)
- `task.escapia_housekeeping_task_native_pms_id` (line 22)
- `work_order.escapia_work_order_native_pms_id` (line 23)
- `stakeholder.escapia_owner_native_pms_id` (line 24)

And the new tables:

- `sync_cursor` (line 39-48) with `start_version` and `last_polled_at`, resources including `RESERVATIONS`, `UNITS`, `OWNERS`, `HOUSEKEEPING`, `WORK_ORDERS`, `GUESTS`.
- `housekeeping_status_map` (line 51-61) with `pmc_id`, `stage_definition_id`, `escapia_clean_status_id`, `escapia_status_label`.

`packages/db/src/strqc_db/repositories.py` provides `get_sync_cursor` and `upsert_sync_cursor` (line 193-214) and `create_work_order` (line 169-187).

**Note:** `TASKS.md` line 41 claims the live schema has no Addendum-1/2 fields. That statement is stale; the fields and tables exist in migration `0002_addendum_1_2.sql`. The migration may not have been applied to a production database yet, but the schema is present.

---

## Risks and Recommendations

| Risk | Severity | Recommendation |
|---|---|---|
| M4.2 custom Strands tool missing | High | Agent cannot use Escapia integration. Build a Strands tool that delegates to the existing `EscapiaClient` and registers it with the agent. |
| Guest sync missing | Medium | Implement `sync_guests` with `SearchGuests`/`GetGuestById` and store read-only guest context on the reservation task. |
| Inbound housekeeping task sync missing | Medium | Wrap `SearchHousekeepingTasks` and `GetUnitHousekeepingStatuses` so the platform can reconcile Escapia assignments. |
| Inbound work-order sync missing | Medium | Wrap `SearchWorkOrders`/`GetWorkOrder` and run as a poll job; otherwise Facilities is split across systems. |
| Safety-critical auto-push not wired | Medium | Wire the inspection-failure path to call `push_work_order` when `maintenance_required=1` and capture `work_order_source_item` links. |
| `api_version` default mismatch | Low | Ensure production env sets `escapia_api_version` (default "1" vs spec default "10"). |
| Token cache lifetime assumption | Low | `_DEFAULT_LIFETIME = 30 min` is reasonable fallback but Escapia token expiry may differ; monitor production. |
| Retry-After HTTP-date not parsed | Low | `_backoff_delay` parses numeric seconds only; if Escapia sends an HTTP-date, it falls back to generic backoff. Acceptable but could be improved. |
| No package-level test runner | Low | Create a venv and install `apps/api[dev]` so tests run without `PYTHONPATH` hacks. |
| Tracker stale | Low | Update `TASKS.md` status snapshot and M4 checkboxes; much of M4 is implemented. |

---

## Requirement Mapping Checklist

| Requirement | Status | Evidence | Notes |
|---|---|---|---|
| M4.1 Auth: Basic → Bearer token | ✅ | `auth.py:72-87` | Caches header value, refreshes before expiry |
| M4.1 Three required headers | ✅ | `client.py:115-119`, `test_auth_and_client.py:72-74` | Headers on every request |
| M4.1 Base URL | ✅ | `config.py:49`, `client.py:75` | `https://hsapi.escapia.com/dragomanadapter` |
| M4.2 Custom Strands tool using OpenAPI3 spec | ❌ | Not present | Code is direct `httpx` client; no tool registration |
| M4.3 Exponential backoff on 429/5xx | ✅ | `client.py:93-101, 130-139` | Honors `Retry-After`, capped, no hardcoded budget |
| M4.4 Reservations delta via `GetReservationChanges` | ✅ | `sync.py:97-133`, `endpoints.py:211-215` | Cursor stored in `sync_cursor` |
| M4.5 Units poll via `SearchUnitSummaries`/`GetUnitsById` | ✅ | `sync.py:157-226`, `endpoints.py:227-249` | Demographics only, preserves platform fields |
| M4.6 Owners poll via `SearchOwners` with `ownsUnitNativePMSIDs` | ✅ | `sync.py:232-288`, `endpoints.py:252-261` | Links `stakeholder_role` |
| M4.6 Guests poll via `SearchGuests`/`GetGuestById` | ❌ | Not implemented | `sync_cursor` enum exists but no code |
| M4.7 Housekeeping status map per PMC | ✅ | `sync.py:294-348`, `0002_addendum_1_2.sql:51-61` | `GetHousekeepingStatusList` loaded, not hardcoded |
| M4.7 Housekeeping status write-back | ✅ | `sync.py:351-388`, `endpoints.py:273-289` | `SaveUnitHousekeepingStatus` with mapped status |
| M4.7 Housekeeping task read | ❌ | Not implemented | `SearchHousekeepingTasks` not wrapped |
| M4.8 Work orders bi-directional (write) | ✅ | `sync.py:394-431`, `endpoints.py:296-298` | `SaveWorkOrder` with priority/status mapping |
| M4.8 Work orders bi-directional (read) | ❌ | Not implemented | `SearchWorkOrders`/`GetWorkOrder` not wrapped |
| M4.8 Failed safety-critical items auto-push | ❌ | Not wired | `push_work_order` exists but no automatic caller |
| M4.9 Scheduler: delta + poll asymmetry | 🟡 | `scheduler.py:33-38` | Reservations delta; units/owners/housekeeping poll. Missing work-orders/guests poll jobs |
| M4.10 GraphQL Gateway out of scope | ✅ | `scheduler.py:8-10`, `__init__.py:3-4` | Explicitly stubbed as Phase-2 |
| Addendum-2 native ID fields | ✅ | `0002_addendum_1_2.sql:19-23` | All required fields present |
| Addendum-2 `SyncCursor` table | ✅ | `0002_addendum_1_2.sql:39-48` | Delta + poll cursors |
| Addendum-2 `HousekeepingStatusMap` table | ✅ | `0002_addendum_1_2.sql:51-61` | Per-PMC stage mapping |

---

*Report generated by read-only audit. No files modified.*
