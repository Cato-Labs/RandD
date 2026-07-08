# DB & Shared Layer — Simplification Audit

**Date:** 2026-07-06 · **Read-only** (no code modified) · Companion to skeptic reports [01](../01-database-schema.md), [06](../06-shared-security.md)

**Constraint:** Every proposal preserves all requirements, features, and experience. These are internal simplifications with identical external behavior.

---

## Executive Summary

The DB and shared packages are already small and clean. The main waste is **a duplicated schema source of truth** and **repository boilerplate**. Fixing these reduces surface area without touching behavior.

Net opportunity: remove ~1 redundant schema file, ~2 helpers of boilerplate, tighten config. No feature change.

---

## Incorporated Skeptic Findings

- Skeptic #1: schema + Addendum 1/2 fields present; migrations idempotent; repository coverage partial; `mask_secret` leaks final char; no `PYTHONPATH`/pytest config.
- Skeptic #6: crypto correct; secrets are plain `str` (should be `SecretStr`); empty `STRQC_SESSION_SECRET`; loose dep pins.

Simplification lens turns several of these into "consolidate/tighten" rather than "add".

---

## Simplification Opportunities

| # | Opportunity | Safe because | Reduction | Risk |
|---|-------------|--------------|-----------|------|
| D1 | Delete `sql/phase1_schema.sql` (superseded by `packages/db/migrations/0001_phase1_baseline.sql`) | The live schema is owned by `packages/db` migrations (README §Legacy confirms). The `sql/` copy is a second source of truth that can drift. | −1 file (~13 KB), removes drift risk | Low — verify nothing imports it (only referenced by legacy `scripts/migrate_phase1.py`) |
| D2 | Fold `sql/inspection_reports.sql` into a migration or drop if the `report_db.py` table is created in code | One authoritative place for DDL | −1 file | Low |
| D3 | Add a `row_to_dict` + `fetch_all`/`fetch_one` helper in `repositories.py` and reuse; removes repeated `[dict(r) for r in cur.fetchall()]` and repeated `with conn:` scaffolding | Pure refactor of identical code paths | ~20–30 LOC, clearer | Low |
| D4 | Collapse the two near-identical sync-cursor accessors into the generic `_rows` pattern already present | Behavior identical | small | Low |
| D5 | Convert secret fields in `config.py` to `SecretStr` and read via `.get_secret_value()` | Same values, less accidental logging (also a skeptic security ask) — no behavior change for consumers if accessors updated in lockstep | net-neutral LOC, safer | Low-Med (touch call sites) |
| D6 | Fix `mask_secret` to return a fixed-width mask (drop the "+ last char" branch) | Simpler and removes the info leak; callers only display it | −a few LOC | Low |
| D7 | Tighten dep pins with upper bounds / a lock file | Reproducible installs; no runtime change | 0 LOC | Low |

---

## Duplication to Eliminate

1. **Schema DDL exists twice** — `sql/phase1_schema.sql` vs `packages/db/.../0001_phase1_baseline.sql`. Keep the migration; delete `sql/phase1_schema.sql`. (D1)
2. **Legacy CSV migrator** `scripts/migrate_phase1.py` embeds/depends on the old schema — it is Phase-1 kickoff tooling. If still needed, point it at the migration package rather than the `sql/` copy so there is one DDL source.
3. **Config duplication** — `backend/app` reads env directly (`os.getenv`) while `strqc_shared/config.py` centralizes it. Long-term, backend should consume `strqc_shared` settings; short-term this is cross-package (see reports 02/03/05).

---

## Dependency Reduction

- `packages/db` has **no runtime deps** — already optimal.
- `packages/shared` deps (`pydantic`, `pydantic-settings`, `cryptography`) are all used and minimal — keep.

---

## Estimated Net Reduction

- Files: **−2** (`sql/phase1_schema.sql`, `sql/inspection_reports.sql` if folded in)
- LOC: **~−40** boilerplate in `repositories.py` via helpers
- Drift risk: one schema source instead of two

---

## Do Not Touch (would change behavior)

- Migration ledger / ordering logic in `migrate.py` — correct and required.
- `connection.py` PRAGMAs (foreign_keys, WAL, busy_timeout) — behavioral guarantees.
- Crypto algorithm/format (`v1.<nonce>.<ct>`, AAD) — changing breaks existing ciphertext.
- Result-enum validation (`PASS/FAIL/NA`), priority validation — feature contracts.

---

## Prioritized Recommendations

1. **D1** delete duplicate `sql/phase1_schema.sql` (highest drift-risk win, trivial).
2. **D3** add repository fetch/transaction helpers (readability + LOC).
3. **D6** fix `mask_secret` (tiny, also closes skeptic leak).
4. **D5/D7** `SecretStr` + dep pinning (safety, near-zero footprint).
