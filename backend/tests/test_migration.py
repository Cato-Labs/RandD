"""Migration tests (spec §11.1 / §3.5)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.migrate_runtime import apply_pending

EXPECTED_COUNTS = {
    "property": 96,
    "task": 65,
    "stakeholder": 5,
    "stakeholder_role": 97,
    "cluster": 11,
    "inspection_reports": 51,
}

TENANT_OWNED = [
    "stakeholder",
    "stakeholder_role",
    "task",
    "work_order",
    "report",
    "inspection",
    "photo_memory",
    "maintenance_check",
    "inspection_reports",
    "property",
    "cluster",
]


def test_counts_preserved(migrated_db: Path) -> None:
    conn = sqlite3.connect(migrated_db)
    try:
        for table, expected in EXPECTED_COUNTS.items():
            got = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert got == expected, f"{table}: {got} != {expected}"
    finally:
        conn.close()


def test_no_null_tenant_id(migrated_db: Path) -> None:
    conn = sqlite3.connect(migrated_db)
    try:
        for table in TENANT_OWNED:
            n = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE tenant_id IS NULL"
            ).fetchone()[0]
            assert n == 0, f"{table} has {n} NULL tenant_id rows"
    finally:
        conn.close()


def test_integrity_and_fk(migrated_db: Path) -> None:
    conn = sqlite3.connect(migrated_db)
    try:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()


def test_tenant_row_seeded(migrated_db: Path) -> None:
    conn = sqlite3.connect(migrated_db)
    try:
        row = conn.execute(
            "SELECT tenant_id, name, slug FROM tenant WHERE tenant_id = 1"
        ).fetchone()
        assert row == (1, "RandD Tradesmen", "randd-tradesmen")
    finally:
        conn.close()


def test_per_tenant_unique(migrated_db: Path) -> None:
    conn = sqlite3.connect(migrated_db)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        code = conn.execute(
            "SELECT unit_code FROM property WHERE tenant_id = 1 LIMIT 1"
        ).fetchone()[0]
        conn.execute("INSERT INTO tenant (tenant_id, name, slug) VALUES (2, 'T2', 't2')")
        # Reusing the code under a different tenant succeeds.
        conn.execute(
            "INSERT INTO property (tenant_id, unit_code) VALUES (2, ?)", (code,)
        )
        # Duplicating it within tenant 1 fails.
        try:
            conn.execute(
                "INSERT INTO property (tenant_id, unit_code) VALUES (1, ?)", (code,)
            )
            raise AssertionError("expected UNIQUE violation for duplicate within tenant 1")
        except sqlite3.IntegrityError:
            pass
    finally:
        conn.close()


def test_idempotent(migrated_db: Path) -> None:
    # migrated_db already applied once; a second apply must be a no-op.
    applied = apply_pending(str(migrated_db))
    assert applied == []
    conn = sqlite3.connect(migrated_db)
    try:
        ledger = [r[0] for r in conn.execute("SELECT name FROM schema_migration")]
        assert ledger.count("0003_multitenancy") == 1
        # Data still intact after the second run.
        assert (
            conn.execute("SELECT COUNT(*) FROM property WHERE tenant_id = 1").fetchone()[0]
            == 96
        )
    finally:
        conn.close()
