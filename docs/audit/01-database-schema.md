# Database Schema, Migrations & Repository Layer Audit

**Audit date:** 2026-07-06  
**Scope:** `packages/db/src/strqc_db` migrations, connection, repositories, seed, and tests, plus `sql/phase1_schema.sql` and `scripts/migrate_phase1.py`.  
**Source of truth:** `AGENTS.md` (PRD incl. Addenda 1 & 2) and `TASKS.md` milestones M0–M1.  
**Read-only audit:** no code files were modified.

---

## Executive Summary

The repository contains a functioning **Phase-1 SQLite schema** and a **versioned SQL migration runner** that successfully applies two migrations:

1. `0001_phase1_baseline.sql` — core operational schema (properties, stakeholders, roles, tasks, stages, checklist templates, inspections, photos, work orders, reports, maintenance features, migration issues).
2. `0002_addendum_1_2.sql` — Addendum-1 report delivery / photo inclusion and Addendum-2 Escapia sync surface.

All seven tests in `packages/db/tests/test_db.py` pass when run with the correct `PYTHONPATH`.

**What is implemented:**
- The complete set of Phase-1 tables and the M1 Addendum-1/2 columns/entities required by `TASKS.md` M1.2–M1.5.
- A simple but correct migration ledger (`schema_migration`) and idempotent runner (`migrate.py`).
- Seed data for a small Big Bear cluster.
- A thin repository layer covering the most common read/write paths.

**What is missing or incomplete (schema):**
- No direct `property.owner_stakeholder_id` FK; ownership is modeled only through `stakeholder_role`.
- No `purpose` enum on `photo_memory` (Addendum-1 requires CLEAN_VERIFICATION, DAMAGE_DOCUMENTATION, etc.).
- No `space_id` / `asset_id` linkage on `photo_memory`, `inspection_item_result`, or `checklist_item_template`.
- No `asset.status` column (OK/NEEDS_SERVICE/OUT_OF_ORDER/REMOVED) — `property_feature` has only `quantity` and `notes`.
- `report` lacks the `checklist_template_id` FK described in the PRD §6.
- No `maintenance_plan` entity (frequency-based recurring checks); only `maintenance_check` instances exist.
- Escapia demographic fields on `property` are limited to `escapia_unit_native_pms_id` / `escapia_pmc_id`; no lat/long, bed/bath counts, `unitComplex`, `maintenanceNotes`, `vacantUntil`, etc.
- `work_order` lacks Escapia-equivalent fields such as category/subcategory, cost, and `removesUnitFromAvailability`.

**What is missing or incomplete (repository / security):**
- Report CRUD, work-order status transitions, and stakeholder/property maintenance are not covered.
- `HousekeepingStatusMap` has no repository functions.
- Secrets columns (`*_ciphertext`) exist but there is no encryption implementation; plaintext secrets are simply not stored by the CSV importer, not encrypted.

**Security posture:** structural (ciphertext columns exist, CSV importer redacts plaintext) but not enforced end-to-end. TASKS.md M1.6 remains open.

---

## Migration System Status

| Item | Status | Evidence / Notes |
| --- | --- | --- |
| Versioned SQL migrations | Implemented | `packages/db/src/strqc_db/migrations/0001_phase1_baseline.sql`, `0002_addendum_1_2.sql` |
| Migration ledger table | Implemented | `schema_migration` created in `migrate.py:35` |
| Idempotent application | Implemented | `migrate.py:52-61` skips already-applied migrations; `test_migrations_are_idempotent` passes |
| `ON` ordering | Implemented | `migrate.py:26` sorts files by name |
| Foreign keys enabled | Implemented | Every migration file starts with `PRAGMA foreign_keys = ON`; `connection.py:13` also enables it |
| WAL + busy timeout | Implemented | `connection.py:14-15` |
| Down-migrations | Missing | No rollback mechanism; not required by PRD but worth noting |
| Alembic / structured tool | Not adopted | TASKS.md M1.1 still flags this as pending; current system is plain versioned SQL |
| Migration issue logging | Implemented | `migration_issue` table in `0001_phase1_baseline.sql:259` |

---

## Table-by-Table Audit Against Requirements

### `cluster`

| Requirement | Status | Notes |
| --- | --- | --- |
| Geo/cluster grouping | Implemented | `cluster_id`, `name`, `description`; `property.cluster_id` FK |

### `property` (House object)

| Requirement | Status | Notes |
| --- | --- | --- |
| `house_id` / `property_id` | Implemented | `property_id INTEGER PRIMARY KEY` (`0001_phase1_baseline.sql:25`) |
| `unit_code` | Implemented | `unit_code TEXT NOT NULL UNIQUE` (`0001_phase1_baseline.sql:26`) |
| `cabin_name` / display name | Partial | Named `display_name`; no `cabin_name` column |
| Address (line, city, state, postal) | Partial | `address_line_1`, `city`, `state_province`, `postal_code` exist; no `address_line_2` |
| `wifi_ssid` | Implemented | `0001_phase1_baseline.sql:32` |
| `wifi_password` encrypted | Partial | `wifi_password_ciphertext` / `wifi_password_secret_ref` exist (`0001_phase1_baseline.sql:33-34`), but no encryption layer writes them |
| `door_code` encrypted | Partial | `door_code_ciphertext` / `door_code_secret_ref` exist (`0001_phase1_baseline.sql:35-36`), but no encryption layer writes them |
| `cluster` / geo | Implemented | `cluster_id` FK |
| `owner_stakeholder_id` | Missing | No direct FK; owner relationship is only via `stakeholder_role` |
| `standing_instructions` | Implemented | `0001_phase1_baseline.sql:38` |
| `roster_active` | Implemented | `0001_phase1_baseline.sql:40` |
| Escapia native IDs | Implemented | `escapia_unit_native_pms_id`, `escapia_pmc_id` added by `0002_addendum_1_2.sql:19-20` |
| Escapia Unit demographics (lat/long, beds, baths, sleeps, complex, etc.) | Missing | Only `property_feature` captures bathrooms/bedrooms as quantities; no lat/long, `unitComplex`, `maintenanceNotes`, `vacantUntil`, `occupiedUntil`, `nextArrival` |
| Source tracking | Implemented | `source_system`, `source_row_number` on `task` only; `property.source_system` exists (`0001_phase1_baseline.sql:41`) |

### `stakeholder` and `role`

| Requirement | Status | Notes |
| --- | --- | --- |
| `stakeholder_id` | Implemented | `0001_phase1_baseline.sql:10` |
| `full_name`, `email`, `phone` | Implemented | `0001_phase1_baseline.sql:11-13` |
| `is_active` | Implemented | `0001_phase1_baseline.sql:14` |
| `contact` | Partial | `email` + `phone` cover the requirement; no single `contact` column |
| Six roles | Implemented | `OWNER`, `HOUSEKEEPER`, `FACILITIES`, `QC_INSPECTOR`, `PROPERTY_MANAGER`, `OFFICE_DISPATCH` (`0001_phase1_baseline.sql:280-287`) |
| `stakeholder_role` global or per-property | Implemented | `property_id` nullable with partial unique indexes (`0001_phase1_baseline.sql:59-65`) |
| Escapia owner native ID | Implemented | `escapia_owner_native_pms_id` added by `0002_addendum_1_2.sql:24` |

### `task` and `task_stage_event`

| Requirement | Status | Notes |
| --- | --- | --- |
| `task_id`, `property_id`, `arrival_date` | Implemented | `0001_phase1_baseline.sql:83-86` |
| `assigned_housekeeper_id` | Implemented | `assigned_housekeeper_stakeholder_id` (`0001_phase1_baseline.sql:87`) |
| `current_stage` | Implemented | `current_stage_definition_id` FK to `stage_definition` (`0001_phase1_baseline.sql:88`) |
| 8 stage definitions | Implemented | `QC`, `B2B`, `CLN`, `DONE`, `OWN`, `WO`, `DONE_WO`, `REPORT` (`0001_phase1_baseline.sql:289-298`) |
| `task_stage_event` | Implemented | `is_complete`, `completed_at`, `completed_by_stakeholder_id`, `source_value` (`0001_phase1_baseline.sql:98-110`) |
| `reservation_context` | Missing | PRD §2 mentions `Task.reservation_context`; no such column exists |
| Escapia reservation / housekeeping task IDs | Implemented | `escapia_reservation_native_pms_id`, `escapia_housekeeping_task_native_pms_id` (`0002_addendum_1_2.sql:21-22`) |

### `checklist_template`, `checklist_category`, `checklist_item_template`

| Requirement | Status | Notes |
| --- | --- | --- |
| Template name/version | Implemented | `0001_phase1_baseline.sql:112-119` |
| Categories with display order | Implemented | `0001_phase1_baseline.sql:121-128` |
| Item text, display order | Implemented | `0001_phase1_baseline.sql:130-139` |
| PASS/FAIL/NA result enum | Implemented | `inspection_item_result.result` check (`0001_phase1_baseline.sql:173`) |
| Required-photo flag | Implemented | `required_photo` on item template (`0001_phase1_baseline.sql:135`) |
| Maintenance flag | Implemented | `maintenance_required` on item template (`0001_phase1_baseline.sql:136`) |
| Space / asset linkage per item | Missing | No `space_id` or `asset_id` FK on `checklist_item_template` or `inspection_item_result` |
| Required-photo enforcement | Not in schema | Application-layer concern (TASKS.md M5.1) |

### `inspection` and `inspection_item_result`

| Requirement | Status | Notes |
| --- | --- | --- |
| `inspection_id`, `task_id`, `checklist_template_id`, `inspector_id` | Implemented | `0001_phase1_baseline.sql:157-167` |
| `started_at`, `submitted_at` | Implemented | `0001_phase1_baseline.sql:162-163` |
| Item result with result/notes/photo | Implemented | `0001_phase1_baseline.sql:169-182` |
| `space_id` / `asset_id` on result | Missing | Only a single `photo_memory_id` FK exists |
| Multiple photos per item | Missing | Schema allows only one `photo_memory_id` per result; a single FAIL may need multiple photos |

### `photo_memory`

| Requirement | Status | Notes |
| --- | --- | --- |
| `photo_id` / `photo_memory_id` | Implemented | `0001_phase1_baseline.sql:141` |
| `property_id`, `task_id`, `inspection_id` | Implemented | `0001_phase1_baseline.sql:143-145` |
| `capture_uri` / storage | Implemented | `uri`, `storage_ref` (`0001_phase1_baseline.sql:146-147`) |
| `captured_at` | Implemented | `0001_phase1_baseline.sql:150` |
| `content_hash` | Implemented | `0001_phase1_baseline.sql:148` |
| `caption` | Implemented | `0001_phase1_baseline.sql:149` |
| `include_in_report` (Addendum 1) | Implemented | `0002_addendum_1_2.sql:15-16` |
| `purpose` enum (CLEAN_VERIFICATION, DAMAGE_DOCUMENTATION, MAINTENANCE_BEFORE, MAINTENANCE_AFTER, OWNER_REPORT) | Missing | Only `metadata_json` can hold this informally |
| `space_id` / `asset_id` | Missing | No direct linkage to spaces or assets |
| `work_order_id` | Missing | No FK for maintenance before/after photos |
| `captured_by_stakeholder_id` | Missing | No photographer attribution |
| `metadata_json` | Implemented | Generic extension point (`0001_phase1_baseline.sql:151`) |

### `property_feature_type` / `property_feature` (spaces and assets)

| Requirement | Status | Notes |
| --- | --- | --- |
| Feature types for hot tub, TV, EV charger, arcade, patio, porch, bathroom, bedroom | Implemented | `0001_phase1_baseline.sql:300-309` |
| Per-property features with quantity and location | Implemented | `property_feature` (`0001_phase1_baseline.sql:191-202`) |
| `asset.status` (OK/NEEDS_SERVICE/OUT_OF_ORDER/REMOVED) | Missing | `property_feature` has no status column |
| `asset.notes` | Partial | `property_feature.notes` exists but is not the same as an asset-level status log |
| `space_type` / `display_order` as described in PRD | Missing | Spaces are modeled as feature types with `location_label`, not as a distinct `space` table |
| `last_verified_at` | Implemented | `property_feature.last_verified_at` (`0001_phase1_baseline.sql:198`) |

### `maintenance_check`

| Requirement | Status | Notes |
| --- | --- | --- |
| Per-feature maintenance checks | Implemented | `maintenance_check` with `PENDING/PASS/FAIL/NA` status (`0001_phase1_baseline.sql:204-217`) |
| `maintenance_plan` (frequency, auto-generate) | Missing | PRD §5 lists `maintenance_plan_id`, `frequency_days`, `next_due_at`, `auto_generate_work_order`; none present |
| Direct `asset_id` linkage | Missing | Links only to `property_feature_id` |

### `work_order` and `work_order_source_item`

| Requirement | Status | Notes |
| --- | --- | --- |
| `work_order_id`, `task_id`, `property_id` | Implemented | `0001_phase1_baseline.sql:219-232` |
| Status enum (NEW/ASSIGNED/IN_PROGRESS/BLOCKED/DONE/CANCELLED) | Implemented | `0001_phase1_baseline.sql:223` |
| Priority enum (LOW/MEDIUM/HIGH/URGENT) | Implemented | `0001_phase1_baseline.sql:224` |
| `assigned_facilities_stakeholder_id` | Implemented | `0001_phase1_baseline.sql:225` |
| `opened_at`, `closed_at`, `details` | Implemented | `0001_phase1_baseline.sql:226-228` |
| Link to failed inspection item | Implemented | Junction table `work_order_source_item` (`0001_phase1_baseline.sql:234-240`) |
| Escapia native work order ID | Implemented | `escapia_work_order_native_pms_id` (`0002_addendum_1_2.sql:23`) |
| Escapia-equivalent fields (category, subcategory, cost, removesUnitFromAvailability) | Missing | Not required by M1 but needed for M4.8 |

### `report`

| Requirement | Status | Notes |
| --- | --- | --- |
| `report_id`, `task_id`, `property_id` | Implemented | `0001_phase1_baseline.sql:242-246` |
| `ready_for_guests` | Implemented | `0001_phase1_baseline.sql:247` |
| `signed_off_by_stakeholder_id`, `signed_off_at` | Implemented | `0001_phase1_baseline.sql:248-249` |
| `export_uri`, `summary_text` | Implemented | `0001_phase1_baseline.sql:250-251` |
| `delivery_channel` (SLACK/EMAIL/TEAMS) | Implemented | `0002_addendum_1_2.sql:8-9` |
| `delivered_at` | Implemented | `0002_addendum_1_2.sql:10` |
| `delivery_status` (PENDING/SENT/FAILED) | Implemented | `0002_addendum_1_2.sql:11-12` |
| `checklist_template_id` | Missing | PRD §6 lists `checklist_template_id` on `Report`; schema does not include it |
| `generated_by_model` | Implemented | Extra column beyond PRD (`0001_phase1_baseline.sql:252`) |

### `sync_cursor` and `housekeeping_status_map` (Addendum 2)

| Requirement | Status | Notes |
| --- | --- | --- |
| `SyncCursor` per PMC per resource | Implemented | `sync_cursor` (`0002_addendum_1_2.sql:39-48`) with `start_version` and `last_polled_at` |
| Resource enum | Implemented | `RESERVATIONS`, `UNITS`, `OWNERS`, `HOUSEKEEPING`, `WORK_ORDERS`, `GUESTS` (`0002_addendum_1_2.sql:42-43`) |
| `HousekeepingStatusMap` per PMC | Implemented | `housekeeping_status_map` (`0002_addendum_1_2.sql:51-61`) |
| Repository functions for sync cursor | Implemented | `get_sync_cursor`, `upsert_sync_cursor` in `repositories.py:193-213` |
| Repository functions for housekeeping map | Missing | No repository coverage |

### `notification_trigger`

| Requirement | Status | Notes |
| --- | --- | --- |
| Event/role mapping | Implemented | `event_key`, `description`, `default_role_id` (`0001_phase1_baseline.sql:67-73`) |
| Initial triggers | Implemented | `CHECKLIST_ITEM_FAILED`, `TASK_READY_FOR_OWNER_REVIEW`, `WORK_ORDER_BLOCKED`, `REPORT_SIGN_OFF_PENDING` (`0001_phase1_baseline.sql:311-316`) |

---

## Repository Coverage Gaps

Implemented repository functions (in `packages/db/src/strqc_db/repositories.py`):

- `get_property` (line 20)
- `list_properties` (line 26)
- `property_features` (line 33)
- `tasks_for_date` (line 51)
- `set_task_stage` (line 69)
- `start_inspection` (line 100)
- `record_item_result` (line 111)
- `checklist_items` (line 130)
- `add_photo` (line 148)
- `create_work_order` (line 169)
- `get_sync_cursor` / `upsert_sync_cursor` (lines 193, 200)

Notable gaps:

| Area | Status | Impact |
| --- | --- | --- |
| Report CRUD / sign-off | Missing | `report` table has no repository functions; delivery logic cannot be built on top of it yet |
| Work order status update / assignment | Missing | `create_work_order` only creates `NEW` orders; no `set_work_order_status` or assignment helper |
| Task CRUD beyond stage transition | Missing | No `create_task`, `update_task`, `list_tasks_by_stakeholder` |
| Property write / update | Missing | Only `get_property` and `list_properties` |
| Stakeholder CRUD | Missing | No repository functions; seed and CSV importer create stakeholders ad-hoc |
| `housekeeping_status_map` | Missing | No create/read/update for Escapia status mapping |
| `maintenance_check` / `maintenance_plan` | Missing | No repository functions; `maintenance_plan` table itself is missing |
| Photo query by purpose / report inclusion | Missing | No `list_photos_for_report`, `set_photo_purpose` |
| Transactional composition | Partial | Each function manages its own `with conn:` transaction; callers must be careful not to nest |
| Typed models | Missing | Returns raw `dict` from `sqlite3.Row`; no Pydantic/dataclass models shared with API (TASKS.md M1.7) |

---

## Test Results

Ran the DB test suite with `PYTHONPATH=packages/db/src`:

```bash
PYTHONPATH=packages/db/src python3 -m pytest packages/db/tests -q
```

Result: **7 passed in 0.11s**.

| Test | Verifies | Result |
| --- | --- | --- |
| `test_migrations_are_idempotent` | Runner skips already-applied migrations | Pass |
| `test_addendum_columns_exist` | Addendum-1/2 columns and tables exist | Pass |
| `test_seeded_property_and_features` | Seed data loads; property + features queryable | Pass |
| `test_stage_transition_records_event` | `set_task_stage` updates task and event | Pass |
| `test_inspection_flow_and_work_order` | Inspection + item result + work order link | Pass |
| `test_invalid_result_rejected` | `record_item_result` rejects non-PASS/FAIL/NA | Pass |
| `test_sync_cursor_upsert` | Sync cursor upsert works | Pass |

Note: tests do not run by default because the package is not installed and `strqc_db` is not on `PYTHONPATH`. This is a minor developer-experience issue, not a schema issue.

---

## Security Observations

| Requirement | Status | Notes |
| --- | --- | --- |
| Ciphertext columns exist for Wi-Fi and door code | Implemented | `wifi_password_ciphertext`, `door_code_ciphertext` (`0001_phase1_baseline.sql:33-35`) |
| Secret-reference columns exist | Implemented | `wifi_password_secret_ref`, `door_code_secret_ref` (`0001_phase1_baseline.sql:34-36`) |
| Encryption implementation | Missing | No KMS/app-key envelope encryption; no code path writes ciphertext |
| Plaintext secret ingestion | Mitigated | `scripts/migrate_phase1.py:255-272` warns and refuses to store raw secrets from CSV, but does not encrypt them |
| SQLite file at rest | Unencrypted | The whole `.sqlite` file is plaintext; at-rest encryption relies on filesystem or SQLCipher |
| Logging of secrets | Not verified | No application logging layer exists yet to audit |
| `source_value` column in `task_stage_event` | Risk | Stores raw CSV cell values (`scripts/migrate_phase1.py:412`); if stage columns ever contain sensitive text, this could leak |

**Recommendation:** complete TASKS.md M1.6 by adding an envelope-encryption helper before any real credentials are inserted; treat the ciphertext columns as non-optional for production.

---

## Risks and Recommendations

1. **No encryption layer for secrets (M1.6).** The schema is structurally ready, but the application will store plaintext in ciphertext columns unless an encryption helper is added. This is the highest-risk gap for v1.
2. **Photo/result linkage is too coarse.** `inspection_item_result` references only one photo and lacks `space_id`/`asset_id`. This will make report assembly and failure triage harder.
3. **No `purpose` on photos.** Addendum-1 explicitly calls for a `purpose` enum; currently only generic `metadata_json` can hold it.
4. **Missing `report` repository.** The PRD's sign-off → Slack delivery flow cannot be implemented without report CRUD.
5. **No `maintenance_plan` table.** Recurring maintenance (hot tub service, detector batteries) cannot be scheduled automatically.
6. **Escapia demographic fields incomplete.** The Addendum-2 native IDs are present, but many Unit fields from the Escapia spec are not modeled; keep them in `metadata_json` or extend the schema during M4.
7. **Migration tool not adopted.** Plain SQL works for now but will not scale to multi-developer schema evolution; consider Alembic or similar as planned in M1.1.
8. **Tests require manual `PYTHONPATH`.** Add a `pyproject.toml` or `pytest.ini` so CI can run tests without env overrides.
9. **No repository for `housekeeping_status_map`.** Escapia status write-back (M4.7) needs create/update/read functions.
10. **Typed models missing.** API and agent will benefit from shared Pydantic/dataclass models (M1.7).

---

## Requirement-to-Status Checklist

| Requirement (AGENTS.md / TASKS.md) | Status | Evidence |
| --- | --- | --- |
| Property core fields (unit code, display name, address, city/state/postal, Wi-Fi, door code, cluster) | Implemented | `property` table, `0001_phase1_baseline.sql:24-46` |
| Property owner stakeholder link | Partial | Via `stakeholder_role`; no direct `owner_stakeholder_id` |
| Spaces (kitchen, bedroom, bathroom, outdoors, hot tub area) | Partial | `property_feature` with types; no distinct `space` table or `space_type` enum |
| Assets (TVs, hot tubs, grills, detectors, EV chargers, arcade) | Partial | `property_feature_type` covers these; lacks `asset.status` and `asset.notes` semantics |
| Stakeholders and 6 roles | Implemented | `stakeholder`, `role`, `stakeholder_role`, `0001_phase1_baseline.sql:18-57` |
| Tasks and stage events | Implemented | `task`, `task_stage_event`, `stage_definition`, `0001_phase1_baseline.sql:75-110` |
| Checklist templates and categories | Implemented | `checklist_template`, `checklist_category`, `checklist_item_template`, `0001_phase1_baseline.sql:112-139` |
| Checklist item results (PASS/FAIL/NA) | Implemented | `inspection_item_result`, `0001_phase1_baseline.sql:169-182` |
| Photos with metadata | Implemented | `photo_memory`, `0001_phase1_baseline.sql:141-155` |
| Addendum-1: `Photo.include_in_report` | Implemented | `0002_addendum_1_2.sql:15-16` |
| Addendum-1: `Report.delivery_channel` | Implemented | `0002_addendum_1_2.sql:8-9` |
| Addendum-1: `Report.delivered_at` | Implemented | `0002_addendum_1_2.sql:10` |
| Addendum-1: `Report.delivery_status` | Implemented | `0002_addendum_1_2.sql:11-12` |
| Photo `purpose` enum | Missing | No column; only `metadata_json` |
| Work orders | Implemented | `work_order`, `work_order_source_item`, `0001_phase1_baseline.sql:219-240` |
| Reports | Partial | Missing `checklist_template_id` FK; delivery fields present |
| Maintenance plans | Missing | Only `maintenance_check` exists |
| Addendum-2: Escapia native IDs on property/task/work order/stakeholder | Implemented | `0002_addendum_1_2.sql:19-24` |
| Addendum-2: `SyncCursor` | Implemented | `sync_cursor`, `0002_addendum_1_2.sql:39-48` |
| Addendum-2: `HousekeepingStatusMap` | Implemented | `housekeeping_status_map`, `0002_addendum_1_2.sql:51-61` |
| Secrets encryption at rest | Partial | Columns exist; no encryption implementation |
| Versioned migration system | Implemented | `migrate.py`, `schema_migration`, `0001`/`0002` migrations |
| Repository pattern | Partial | Core reads/writes exist; many gaps (see above) |
| Seed data / fixtures | Implemented | `seed.py` Big Bear cluster, `packages/db/src/strqc_db/seed.py:14-91` |
| Unit tests | Implemented | 7 passing in `packages/db/tests/test_db.py` |

---

## File References

- `packages/db/src/strqc_db/migrations/0001_phase1_baseline.sql`
- `packages/db/src/strqc_db/migrations/0002_addendum_1_2.sql`
- `packages/db/src/strqc_db/migrate.py`
- `packages/db/src/strqc_db/connection.py`
- `packages/db/src/strqc_db/repositories.py`
- `packages/db/src/strqc_db/seed.py`
- `packages/db/tests/test_db.py`
- `sql/phase1_schema.sql`
- `scripts/migrate_phase1.py`
