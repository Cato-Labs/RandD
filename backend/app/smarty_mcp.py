"""Native Strands connector for Smarty's remote MCP server.

Credentials stay on the server and are read only when a connector is created.
Callers own the returned ``MCPClient`` lifecycle so the discovered tools can be
registered directly on the session's Strands agent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

DEFAULT_SMARTY_MCP_URL = "https://mcp.api.smarty.com/"


class SmartyMCPConfigurationError(RuntimeError):
    """Raised when the server-side Smarty MCP configuration is incomplete."""


@dataclass(frozen=True, repr=False)
class SmartyMCPSettings:
    url: str
    auth_id: str
    auth_token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Auth-Id": self.auth_id, "Auth-Token": self.auth_token}


def load_smarty_mcp_settings() -> SmartyMCPSettings:
    """Load Smarty MCP settings without accepting model-supplied credentials."""
    auth_id = os.getenv("SMARTY_AUTH_ID", "").strip()
    auth_token = os.getenv("SMARTY_AUTH_TOKEN", "").strip()
    if not auth_id or not auth_token:
        raise SmartyMCPConfigurationError(
            "SMARTY_AUTH_ID and SMARTY_AUTH_TOKEN must be configured on the server"
        )
    return SmartyMCPSettings(
        url=os.getenv("SMARTY_MCP_URL", DEFAULT_SMARTY_MCP_URL).strip()
        or DEFAULT_SMARTY_MCP_URL,
        auth_id=auth_id,
        auth_token=auth_token,
    )


def smarty_perplexity_mcp_tool(allowed_tools: list[str] | None = None) -> dict:
    """Build Perplexity's native remote-MCP tool entry for Smarty."""
    settings = load_smarty_mcp_settings()
    definition: dict = {
        "type": "mcp",
        "server_label": "smarty",
        "server_url": settings.url,
        "headers": settings.headers,
    }
    if allowed_tools:
        definition["allowed_tools"] = list(allowed_tools)
    return definition


def create_smarty_mcp_client() -> MCPClient:
    """Create a native Strands MCP client for direct agent tool registration.

    Use the returned client as a context manager, call ``list_tools_sync()``,
    and pass those discovered tools directly to ``Agent(tools=...)``.
    """
    settings = load_smarty_mcp_settings()
    return MCPClient(
        lambda: streamablehttp_client(settings.url, headers=settings.headers),
        prefix="smarty",
    )
