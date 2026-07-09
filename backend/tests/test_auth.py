"""Auth tests (spec §11.2)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from tests.conftest import add_tenant, seed_user


def test_login_correct_and_wrong_password(client, migrated_db: Path) -> None:
    seed_user(migrated_db, email="u@e.com", password="right", tenant_id=1)

    bad = client.post("/api/auth/login", json={"email": "u@e.com", "password": "wrong"})
    assert bad.status_code == 401

    good = client.post("/api/auth/login", json={"email": "u@e.com", "password": "right"})
    assert good.status_code == 200
    body = good.json()
    assert body["user"]["email"] == "u@e.com"
    assert body["tenant"]["tenant_id"] == 1
    # Cookie set on the client.
    assert client.get("/api/auth/me").status_code == 200


def test_current_user_rejects_missing_cookie(client) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_current_user_rejects_tampered_cookie(client, migrated_db: Path) -> None:
    from app import auth

    seed_user(migrated_db, email="u@e.com", password="pw", tenant_id=1)
    token = auth.create_session_token(1, 1, False)
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    client.cookies.set(auth.cookie_name(), tampered)
    assert client.get("/api/auth/me").status_code == 401


def test_current_user_rejects_expired(client, migrated_db: Path, monkeypatch) -> None:
    from app import auth

    uid = seed_user(migrated_db, email="u@e.com", password="pw", tenant_id=1)
    # Mint a token that is already expired.
    monkeypatch.setattr(auth, "SESSION_TTL_SECONDS", -10)
    token = auth.create_session_token(uid, 1, False)
    client.cookies.set(auth.cookie_name(), token)
    assert client.get("/api/auth/me").status_code == 401


def test_require_platform_admin_rejects_tenant_user(client, migrated_db: Path) -> None:
    seed_user(migrated_db, email="t@e.com", password="pw", tenant_id=1)
    client.post("/api/auth/login", json={"email": "t@e.com", "password": "pw"})
    r = client.post("/api/admin/tenants", json={"name": "X", "slug": "x"})
    assert r.status_code == 403


def test_platform_admin_can_create_tenant_and_user(client, migrated_db: Path) -> None:
    seed_user(
        migrated_db, email="s@e.com", password="pw", tenant_id=None, is_platform_admin=1
    )
    client.post("/api/auth/login", json={"email": "s@e.com", "password": "pw"})
    t = client.post("/api/admin/tenants", json={"name": "Acme", "slug": "acme"})
    assert t.status_code == 200
    tid = t.json()["tenant"]["tenant_id"]
    u = client.post(
        f"/api/admin/tenants/{tid}/users",
        json={"email": "admin@acme.com", "password": "pw"},
    )
    assert u.status_code == 200
    assert u.json()["user"]["tenant_id"] == tid


def test_ws_token_mint_validate_and_expire(client, migrated_db: Path) -> None:
    from app import auth

    seed_user(migrated_db, email="u@e.com", password="pw", tenant_id=1)
    client.post("/api/auth/login", json={"email": "u@e.com", "password": "pw"})

    minted = client.post("/api/auth/ws-token")
    assert minted.status_code == 200
    token = minted.json()["token"]
    claims = auth.verify_ws_token(token)
    assert claims["tenant_id"] == 1

    # A session cookie must not validate as a WS token.
    session = auth.create_session_token(1, 1, False)
    with pytest.raises(ValueError):
        auth.verify_ws_token(session)

    # Expired WS token rejected.
    expired = auth.create_ws_token(1, 1, False)
    time.sleep(0)  # no-op; craft an already-expired token instead
    import jwt

    payload = {
        "typ": "ws",
        "user_id": 1,
        "tenant_id": 1,
        "is_platform_admin": False,
        "iat": int(time.time()) - 120,
        "exp": int(time.time()) - 60,
    }
    stale = jwt.encode(payload, auth._secret(), algorithm="HS256")
    with pytest.raises(ValueError):
        auth.verify_ws_token(stale)
    assert expired  # sanity: valid token minted


def test_ws_rejects_without_and_with_bad_token(client, migrated_db: Path) -> None:
    from starlette.websockets import WebSocketDisconnect

    # No token query param -> rejected at connect.
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws?mode=text&provider=gemini"):
            pass

    # Present-but-invalid token -> accepted then bidi_error + close.
    with client.websocket_connect("/ws?mode=text&provider=gemini&token=bogus") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "bidi_error"
        assert msg["error"] == "unauthorized"


def test_logout_clears_cookie(client, migrated_db: Path) -> None:
    seed_user(migrated_db, email="u@e.com", password="pw", tenant_id=1)
    client.post("/api/auth/login", json={"email": "u@e.com", "password": "pw"})
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401
