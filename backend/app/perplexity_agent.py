"""Direct Strands tool for Perplexity's Agent API."""

from __future__ import annotations

import json
import os
from typing import Any

from strands import tool

from app.smarty_mcp import SmartyMCPConfigurationError, smarty_perplexity_mcp_tool

_DEFAULT_BUILTIN_TOOLS = ("web_search", "fetch_url")
_BUILTIN_TOOL_ALIASES = {
    "web_search": "web_search",
    "fetch_url": "fetch_url",
    # Product-facing language sometimes calls the result "fetch URL content";
    # the Agent API request discriminator is currently ``fetch_url``.
    "fetch_url_content": "fetch_url",
}
_SENSITIVE_KEYS = {
    "authorization",
    "auth-id",
    "auth-token",
    "auth_id",
    "auth_token",
    "headers",
}


def _error(code: str, *, retryable: bool = False, http_status: int | None = None) -> dict:
    result: dict[str, Any] = {"status": "error", "code": code, "retryable": retryable}
    if http_status is not None:
        result["httpStatus"] = http_status
    return result


def _response_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        value = response.model_dump(mode="json")
        return value if isinstance(value, dict) else {}
    if isinstance(response, dict):
        return response
    return {}


def _collect_output(
    data: dict[str, Any], output_type: str, payload_keys: tuple[str, ...]
) -> list[dict]:
    collected: list[dict] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != output_type:
            continue
        collected.append({key: item[key] for key in payload_keys if key in item})
    return collected


def _collect_citations(data: dict[str, Any]) -> list[dict]:
    citations: list[dict] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict):
                citations.extend(
                    annotation
                    for annotation in (content.get("annotations") or [])
                    if isinstance(annotation, dict)
                )
    if not citations:
        citations.extend(item for item in (data.get("citations") or []) if isinstance(item, dict))
    return citations


def _scrub_secrets(value: Any, secret_values: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        return {
            key: _scrub_secrets(item, secret_values)
            for key, item in value.items()
            if str(key).lower() not in _SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [_scrub_secrets(item, secret_values) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_secrets(item, secret_values) for item in value)
    if isinstance(value, str):
        scrubbed = value
        for secret in secret_values:
            if secret:
                scrubbed = scrubbed.replace(secret, "[redacted]")
        return scrubbed
    return value


def _normalize_response(response: Any, *, structured: bool) -> dict[str, Any]:
    data = _response_dict(response)
    answer = getattr(response, "output_text", None)
    if not isinstance(answer, str):
        answer = data.get("output_text") if isinstance(data.get("output_text"), str) else ""
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    normalized: dict[str, Any] = {
        "status": data.get("status") or "completed",
        "responseId": data.get("id"),
        "model": data.get("model"),
        "answer": answer,
        "structuredOutput": None,
        "citations": _collect_citations(data),
        "searchResults": _collect_output(data, "search_results", ("queries", "results")),
        "fetchUrlResults": _collect_output(
            data, "fetch_url_results", ("urls", "contents", "results")
        ),
        "usage": usage,
        "cost": usage.get("cost"),
    }
    if structured:
        try:
            normalized["structuredOutput"] = json.loads(answer)
        except (TypeError, json.JSONDecodeError):
            normalized["structuredOutput"] = None

    secrets = tuple(
        secret
        for secret in (os.getenv("SMARTY_AUTH_ID", ""), os.getenv("SMARTY_AUTH_TOKEN", ""))
        if secret
    )
    return _scrub_secrets(normalized, secrets)


@tool
def perplexity_agent(
    input: str,
    instructions: str = "",
    preset: str = "",
    model: str = "",
    models: list[str] | None = None,
    max_steps: int = 0,
    images: list[str] | None = None,
    previous_response_id: str = "",
    structured_output_schema: dict[str, Any] | None = None,
    structured_output_name: str = "product_research",
    built_in_tools: list[str] | None = None,
    use_smarty: bool = False,
    smarty_allowed_tools: list[str] | None = None,
) -> dict:
    """Research products and addresses through Perplexity's Agent API.

    Web search and URL fetching are enabled by default. Set ``use_smarty`` to
    let Perplexity discover and call Smarty's remote MCP tools with credentials
    sourced only from server environment variables. Never provide credentials
    in arguments. Use ``fetch_url_content`` or ``fetch_url`` to request the
    Agent API's ``fetch_url`` built-in tool.
    """
    if max_steps and not 1 <= max_steps <= 10:
        return _error("invalid_max_steps")
    if models and not 1 <= len(models) <= 5:
        return _error("invalid_models")

    selected_tools = list(_DEFAULT_BUILTIN_TOOLS if built_in_tools is None else built_in_tools)
    try:
        tools: list[dict[str, Any]] = [
            {"type": _BUILTIN_TOOL_ALIASES[name]} for name in selected_tools
        ]
    except KeyError:
        return _error("invalid_builtin_tool")

    if use_smarty:
        try:
            tools.append(smarty_perplexity_mcp_tool(smarty_allowed_tools))
        except SmartyMCPConfigurationError:
            return _error("smarty_credentials_unconfigured")

    request: dict[str, Any] = {"input": input}
    if images:
        request["input"] = [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": input},
                    *({"type": "input_image", "image_url": image} for image in images),
                ],
            }
        ]
    if instructions:
        request["instructions"] = instructions
    if models:
        request["models"] = list(models)
    elif model:
        request["model"] = model
    elif preset:
        request["preset"] = preset
    else:
        request["preset"] = "pro-search"
    if max_steps:
        request["max_steps"] = max_steps
    if previous_response_id:
        request["previous_response_id"] = previous_response_id
    if structured_output_schema is not None:
        request["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": structured_output_name,
                "schema": structured_output_schema,
            },
        }
    request["tools"] = tools

    try:
        from perplexity import Perplexity

        response = Perplexity().responses.create(**request)
    except ImportError:
        return _error("perplexity_sdk_unavailable")
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        return _error(
            "perplexity_request_failed",
            retryable=status is None or status == 429 or status >= 500,
            http_status=status if isinstance(status, int) else None,
        )
    return _normalize_response(response, structured=structured_output_schema is not None)
