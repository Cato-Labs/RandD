"""FastMCP server generated from Perplexity's official Agent API reference."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap


OPENAPI_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "integrations"
    / "perplexity-openapi.json"
)
AGENT_API_PATHS = {
    "/v1/agent",
    "/v1/agent/{id}",
    "/v1/agent/{id}/files",
    "/v1/agent/{id}/files/{file_id}/content",
    "/v1/agent/{id}/cancel",
    "/v1/models",
}


def load_agent_api_reference() -> dict[str, Any]:
    """Load the official schema and retain every Agent API operation."""
    specification = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    specification["paths"] = {
        path: operations
        for path, operations in specification["paths"].items()
        if path in AGENT_API_PATHS
    }
    missing = AGENT_API_PATHS.difference(specification["paths"])
    if missing:
        raise RuntimeError(
            f"Perplexity Agent API reference is missing paths: {sorted(missing)}"
        )
    return specification


api_key = os.getenv("PERPLEXITY_API_KEY", "").strip()
api_client = httpx.AsyncClient(
    base_url="https://api.perplexity.ai",
    headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
    timeout=httpx.Timeout(600.0),
)

mcp = FastMCP.from_openapi(
    openapi_spec=load_agent_api_reference(),
    client=api_client,
    name="Perplexity Agent API",
    route_maps=[RouteMap(mcp_type=MCPType.TOOL)],
    validate_output=True,
)


if __name__ == "__main__":
    mcp.run(show_banner=False)
