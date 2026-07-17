"""Negative tenant-isolation tests (spec §11.3) — the merge gate."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .helpers import add_tenant, seed_user


def _make_two_tenants(migrated_db: Path) -> str:
    """Seed tenant 2 with a distinct property reusing a RandD unit_code.

    Returns the reused unit_code.
    """
    add_tenant(migrated_db, 2, "Tenant Two", "tenant-two")
    conn = sqlite3.connect(migrated_db)
    try:
        randd_code = conn.execute(
            "SELECT unit_code FROM property WHERE tenant_id = 1 LIMIT 1"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO property (tenant_id, unit_code, display_name, address_line_1, roster_active) "
            "VALUES (2, ?, 'T2 Cabin', '999 Secret Rd', 1)",
            (randd_code,),
        )
        conn.execute("INSERT INTO stakeholder (tenant_id, full_name) VALUES (2, 'T2 Inspector')")
        conn.commit()
    finally:
        conn.close()
    seed_user(migrated_db, email="r@e.com", password="pw", tenant_id=1)
    seed_user(migrated_db, email="t2@e.com", password="pw", tenant_id=2)
    return randd_code


def test_properties_scoped_to_caller_tenant(client, migrated_db: Path) -> None:
    _make_two_tenants(migrated_db)

    client.post("/api/auth/login", json={"email": "r@e.com", "password": "pw"})
    p1 = client.get("/api/properties").json()["properties"]
    assert len(p1) == 96
    randd_addresses = {p["address"] for p in p1}
    client.post("/api/auth/logout")
    client.cookies.clear()

    client.post("/api/auth/login", json={"email": "t2@e.com", "password": "pw"})
    p2 = client.get("/api/properties").json()["properties"]
    assert len(p2) == 1
    assert p2[0]["name"] == "T2 Cabin"
    # No RandD address/door/wifi leaks into tenant 2's view.
    t2_addresses = {p["address"] for p in p2} - {""}
    assert not (t2_addresses & (randd_addresses - {""}))


def test_inspectors_scoped_to_caller_tenant(client, migrated_db: Path) -> None:
    _make_two_tenants(migrated_db)
    client.post("/api/auth/login", json={"email": "t2@e.com", "password": "pw"})
    inspectors = client.get("/api/inspectors").json()["inspectors"]
    names = {i["name"] for i in inspectors}
    assert names == {"T2 Inspector"}


def test_tenant_user_cannot_import_into_other_tenant(client, migrated_db: Path) -> None:
    _make_two_tenants(migrated_db)
    client.post("/api/auth/login", json={"email": "t2@e.com", "password": "pw"})
    roster = "Unit Code,Address\nZZZ,1 A St\n"
    r = client.post(
        "/api/import/roster?tenant_id=1",
        files={"file": ("roster.csv", roster, "text/csv")},
    )
    assert r.status_code == 403


def test_import_is_tenant_scoped(client, migrated_db: Path) -> None:
    randd_code = _make_two_tenants(migrated_db)

    conn = sqlite3.connect(migrated_db)
    p1_before = conn.execute(
        "SELECT COUNT(*) FROM property WHERE tenant_id = 1"
    ).fetchone()[0]
    conn.close()

    client.post("/api/auth/login", json={"email": "t2@e.com", "password": "pw"})
    roster = f"Unit Code,Address\n{randd_code},T2 addr\nT2NEW,New Rd\n"
    r = client.post(
        "/api/import/roster", files={"file": ("roster.csv", roster, "text/csv")}
    )
    assert r.status_code == 200

    conn = sqlite3.connect(migrated_db)
    try:
        # RandD untouched.
        assert (
            conn.execute("SELECT COUNT(*) FROM property WHERE tenant_id = 1").fetchone()[0]
            == p1_before
        )
        # Tenant 2 gained T2NEW; reused code exists distinctly under both tenants.
        codes2 = {
            r[0]
            for r in conn.execute("SELECT unit_code FROM property WHERE tenant_id = 2")
        }
        assert "T2NEW" in codes2
        assert randd_code in codes2
        both = [
            r[0]
            for r in conn.execute(
                "SELECT tenant_id FROM property WHERE unit_code = ? ORDER BY tenant_id",
                (randd_code,),
            )
        ]
        assert both == [1, 2]
    finally:
        conn.close()


def test_all_api_routes_require_auth(client) -> None:
    # GET routes
    for path in [
        "/api/agent",
        "/api/models",
        "/api/voices",
        "/api/properties",
        "/api/inspectors",
        "/api/workspace",
        "/api/auth/me",
    ]:
        assert client.get(path).status_code == 401, path
    # POST routes that touch data / mint tokens
    assert client.post("/api/auth/logout").status_code == 401
    assert client.post("/api/auth/ws-token").status_code == 401
    assert client.post("/api/inspection/export", content=b"<html></html>").status_code == 401
    assert (
        client.post(
            "/api/import/roster", files={"file": ("r.csv", "Unit Code\nX\n", "text/csv")}
        ).status_code
        == 401
    )
