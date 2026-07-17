from __future__ import annotations

from types import SimpleNamespace

import pytest


def test_create_smarty_mcp_client_uses_native_strands_transport_and_env_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.smarty_mcp as smarty_mcp

    monkeypatch.setenv("SMARTY_MCP_URL", "https://smarty.invalid/")
    monkeypatch.setenv("SMARTY_AUTH_ID", "env-auth-id")
    monkeypatch.setenv("SMARTY_AUTH_TOKEN", "env-auth-token")
    captured = SimpleNamespace(client=None, transport=None)

    def fake_transport(url: str, *, headers: dict[str, str]):
        captured.transport = {"url": url, "headers": headers}
        return "native-streamable-http-transport"

    class FakeMCPClient:
        def __init__(self, transport_callable, **kwargs):
            captured.client = {"transport_callable": transport_callable, "kwargs": kwargs}

    monkeypatch.setattr(smarty_mcp, "streamablehttp_client", fake_transport)
    monkeypatch.setattr(smarty_mcp, "MCPClient", FakeMCPClient)

    client = smarty_mcp.create_smarty_mcp_client()

    assert isinstance(client, FakeMCPClient)
    assert captured.client["kwargs"] == {"prefix": "smarty"}
    assert captured.client["transport_callable"]() == "native-streamable-http-transport"
    assert captured.transport == {
        "url": "https://smarty.invalid/",
        "headers": {"Auth-Id": "env-auth-id", "Auth-Token": "env-auth-token"},
    }


def test_create_smarty_mcp_client_rejects_missing_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.smarty_mcp import SmartyMCPConfigurationError, create_smarty_mcp_client

    monkeypatch.delenv("SMARTY_AUTH_ID", raising=False)
    monkeypatch.delenv("SMARTY_AUTH_TOKEN", raising=False)

    with pytest.raises(SmartyMCPConfigurationError, match="SMARTY_AUTH_ID and SMARTY_AUTH_TOKEN"):
        create_smarty_mcp_client()


def test_smarty_mcp_default_url_matches_official_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.smarty_mcp as smarty_mcp

    monkeypatch.delenv("SMARTY_MCP_URL", raising=False)
    monkeypatch.setenv("SMARTY_AUTH_ID", "id")
    monkeypatch.setenv("SMARTY_AUTH_TOKEN", "token")
    captured = SimpleNamespace(transport_callable=None)

    class FakeMCPClient:
        def __init__(self, transport_callable, **_):
            captured.transport_callable = transport_callable

    def fake_transport(url: str, *, headers: dict[str, str]):
        return {"url": url, "headers": headers}

    monkeypatch.setattr(smarty_mcp, "streamablehttp_client", fake_transport)
    monkeypatch.setattr(smarty_mcp, "MCPClient", FakeMCPClient)

    smarty_mcp.create_smarty_mcp_client()

    assert captured.transport_callable()["url"] == "https://mcp.api.smarty.com/"
