"""Database seed helpers shared by backend acceptance tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path


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
