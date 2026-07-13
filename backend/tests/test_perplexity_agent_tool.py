from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest


class FakeResponse:
    output_text = '{"manufacturer":"Acme"}'

    def model_dump(self, *, mode: str = "python") -> dict:
        assert mode == "json"
        return {
            "id": "resp_123",
            "status": "completed",
            "model": "openai/gpt-5.4",
            "output": [
                {
                    "type": "search_results",
                    "queries": ["Acme model 100 manual"],
                    "results": [{"title": "Acme", "url": "https://example.test/acme"}],
                },
                {
                    "type": "fetch_url_results",
                    "contents": [{"url": "https://example.test/acme", "content": "manual"}],
                },
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": self.output_text,
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "title": "Acme",
                                    "url": "https://example.test/acme",
                                }
                            ],
                        }
                    ],
                },
            ],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "cost": {"total_cost": 0.01},
            },
        }


@pytest.fixture
def fake_perplexity(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    state = SimpleNamespace(client_kwargs=None, request=None, response=FakeResponse())

    class FakeResponses:
        def create(self, **kwargs):
            state.request = kwargs
            return state.response

    class FakePerplexity:
        def __init__(self, **kwargs):
            state.client_kwargs = kwargs
            self.responses = FakeResponses()

    module = ModuleType("perplexity")
    module.Perplexity = FakePerplexity
    monkeypatch.setitem(sys.modules, "perplexity", module)
    return state


def test_perplexity_agent_builds_full_agent_api_request_and_normalizes_output(
    fake_perplexity: SimpleNamespace,
) -> None:
    from app.perplexity_agent import perplexity_agent

    result = perplexity_agent(
        input="Identify this product",
        instructions="Prefer official sources.",
        models=["openai/gpt-5.4", "anthropic/claude-sonnet-4-6"],
        max_steps=4,
        images=["https://example.test/label.jpg", "data:image/png;base64,AAAA"],
        previous_response_id="resp_previous",
        structured_output_name="product_identity",
        structured_output_schema={
            "type": "object",
            "properties": {"manufacturer": {"type": "string"}},
            "required": ["manufacturer"],
        },
    )

    assert fake_perplexity.client_kwargs == {}
    assert fake_perplexity.request == {
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "Identify this product"},
                    {"type": "input_image", "image_url": "https://example.test/label.jpg"},
                    {"type": "input_image", "image_url": "data:image/png;base64,AAAA"},
                ],
            }
        ],
        "instructions": "Prefer official sources.",
        "models": ["openai/gpt-5.4", "anthropic/claude-sonnet-4-6"],
        "max_steps": 4,
        "previous_response_id": "resp_previous",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "product_identity",
                "schema": {
                    "type": "object",
                    "properties": {"manufacturer": {"type": "string"}},
                    "required": ["manufacturer"],
                },
            },
        },
        "tools": [{"type": "web_search"}, {"type": "fetch_url"}],
    }
    assert result == {
        "status": "completed",
        "responseId": "resp_123",
        "model": "openai/gpt-5.4",
        "answer": '{"manufacturer":"Acme"}',
        "structuredOutput": {"manufacturer": "Acme"},
        "citations": [
            {"type": "url_citation", "title": "Acme", "url": "https://example.test/acme"}
        ],
        "searchResults": [
            {
                "queries": ["Acme model 100 manual"],
                "results": [{"title": "Acme", "url": "https://example.test/acme"}],
            }
        ],
        "fetchUrlResults": [
            {"contents": [{"url": "https://example.test/acme", "content": "manual"}]}
        ],
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "cost": {"total_cost": 0.01},
        },
        "cost": {"total_cost": 0.01},
    }


def test_perplexity_agent_supports_preset_and_selected_builtin_tools(
    fake_perplexity: SimpleNamespace,
) -> None:
    from app.perplexity_agent import perplexity_agent

    perplexity_agent(
        input="Fetch this URL",
        preset="pro-search",
        built_in_tools=["fetch_url_content"],
    )

    assert fake_perplexity.request == {
        "input": "Fetch this URL",
        "preset": "pro-search",
        "tools": [{"type": "fetch_url"}],
    }


def test_perplexity_agent_adds_smarty_mcp_headers_from_environment_without_returning_them(
    monkeypatch: pytest.MonkeyPatch,
    fake_perplexity: SimpleNamespace,
) -> None:
    from app.perplexity_agent import perplexity_agent

    monkeypatch.setenv("SMARTY_MCP_URL", "https://smarty.invalid/mcp")
    monkeypatch.setenv("SMARTY_AUTH_ID", "env-auth-id")
    monkeypatch.setenv("SMARTY_AUTH_TOKEN", "env-auth-token")

    result = perplexity_agent(
        input="Normalize 1 Rosedale St, Baltimore, MD",
        model="openai/gpt-5.4",
        use_smarty=True,
        smarty_allowed_tools=["US_Address"],
    )

    assert fake_perplexity.request["tools"] == [
        {"type": "web_search"},
        {"type": "fetch_url"},
        {
            "type": "mcp",
            "server_label": "smarty",
            "server_url": "https://smarty.invalid/mcp",
            "headers": {"Auth-Id": "env-auth-id", "Auth-Token": "env-auth-token"},
            "allowed_tools": ["US_Address"],
        },
    ]
    rendered = repr(result)
    assert "env-auth-id" not in rendered
    assert "env-auth-token" not in rendered
    assert "Auth-Token" not in rendered


def test_perplexity_agent_requires_server_side_smarty_credentials(
    monkeypatch: pytest.MonkeyPatch,
    fake_perplexity: SimpleNamespace,
) -> None:
    from app.perplexity_agent import perplexity_agent

    monkeypatch.delenv("SMARTY_AUTH_ID", raising=False)
    monkeypatch.delenv("SMARTY_AUTH_TOKEN", raising=False)

    result = perplexity_agent(input="Validate an address", use_smarty=True)

    assert result == {
        "status": "error",
        "code": "smarty_credentials_unconfigured",
        "retryable": False,
    }
    assert fake_perplexity.request is None


@pytest.mark.parametrize(
    ("kwargs", "code"),
    [
        ({"max_steps": 11}, "invalid_max_steps"),
        ({"models": ["a", "b", "c", "d", "e", "f"]}, "invalid_models"),
        ({"built_in_tools": ["shell"]}, "invalid_builtin_tool"),
    ],
)
def test_perplexity_agent_validates_agent_api_limits(
    kwargs: dict,
    code: str,
    fake_perplexity: SimpleNamespace,
) -> None:
    from app.perplexity_agent import perplexity_agent

    result = perplexity_agent(input="research", **kwargs)

    assert result == {"status": "error", "code": code, "retryable": False}
    assert fake_perplexity.request is None


def test_perplexity_agent_sanitizes_secrets_even_if_an_upstream_output_echoes_them(
    monkeypatch: pytest.MonkeyPatch,
    fake_perplexity: SimpleNamespace,
) -> None:
    from app.perplexity_agent import perplexity_agent

    monkeypatch.setenv("SMARTY_AUTH_ID", "do-not-return-id")
    monkeypatch.setenv("SMARTY_AUTH_TOKEN", "do-not-return-token")
    fake_perplexity.response.model_dump = lambda **_: {
        "id": "resp_secret",
        "status": "completed",
        "output": [
            {
                "type": "mcp_call",
                "headers": {"Auth-Token": "do-not-return-token"},
                "output": "server accidentally echoed do-not-return-id",
            }
        ],
        "usage": {},
    }
    fake_perplexity.response.output_text = "safe answer"

    result = perplexity_agent(input="validate", use_smarty=True)

    rendered = repr(result)
    assert "do-not-return-id" not in rendered
    assert "do-not-return-token" not in rendered
