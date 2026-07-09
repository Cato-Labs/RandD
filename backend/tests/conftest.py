"""Shared fixtures for the multi-tenancy / auth test suite.

Every test runs against a fresh copy of the live ``str_qc.sqlite`` migrated
through the ledger runner, with ``STRQC_DB_PATH`` and ``STRQC_SESSION_SECRET``
pointed at throwaway values. No test touches the real database.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND.parent
_LIVE_DB = _REPO_ROOT / "str_qc.sqlite"

sys.path.insert(0, str(_BACKEND))

TEST_SECRET = "test-session-secret-that-is-32-bytes-long!!"


@pytest.fixture()
def migrated_db(tmp_path: Path) -> Path:
    """A fresh copy of the live DB with migration 0003 applied via the ledger."""
    assert _LIVE_DB.exists(), f"live DB not found at {_LIVE_DB}"
    db = tmp_path / "test.sqlite"
    shutil.copy(_LIVE_DB, db)

    os.environ["STRQC_DB_PATH"] = str(db)
    os.environ["STRQC_SESSION_SECRET"] = TEST_SECRET

    from app.migrate_runtime import apply_pending

    apply_pending(str(db))
    return db


@pytest.fixture()
def client(migrated_db: Path):
    """A FastAPI TestClient bound to the migrated copy DB."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def seed_user(
    db: Path,
    *,
    email: str,
    password: str,
    tenant_id: int | None,
    is_platform_admin: int = 0,
) -> int:
    from app import auth

    conn = sqlite3.connect(db)
    try:
        cur = conn.execute(
            "INSERT INTO app_user (tenant_id, email, password_hash, is_platform_admin) VALUES (?,?,?,?)",
            (tenant_id, email, auth.hash_password(password), is_platform_admin),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def add_tenant(db: Path, tenant_id: int, name: str, slug: str) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO tenant (tenant_id, name, slug) VALUES (?,?,?)",
            (tenant_id, name, slug),
        )
        conn.commit()
    finally:
        conn.close()
