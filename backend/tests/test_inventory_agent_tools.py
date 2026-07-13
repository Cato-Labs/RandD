from __future__ import annotations

from contextlib import contextmanager

from app.inventory_tools import build_inventory_tools
from app.vantage.context import TenantContext


class RecordingRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return {"operation": name, "args": args, "kwargs": kwargs}

        return record


class RecordingAdapter:
    def __init__(self) -> None:
        self.repository = RecordingRepository()
        self.transactions: list[tuple[str, TenantContext]] = []

    @contextmanager
    def transaction(self, context: TenantContext):
        self.transactions.append(("write", context))
        yield self.repository

    @contextmanager
    def read_only_transaction(self, context: TenantContext):
        self.transactions.append(("read", context))
        yield self.repository


CONTEXT = TenantContext(
    user_id="user-1",
    organization_id="org-1",
    roles=frozenset({"INSPECTOR"}),
    home_grants=frozenset(),
)


def _tools(adapter: RecordingAdapter) -> dict[str, object]:
    return {tool.tool_name: tool for tool in build_inventory_tools(adapter, CONTEXT)}


def test_inventory_tool_factory_exposes_onboarding_operations() -> None:
    names = set(_tools(RecordingAdapter()))
    assert {
        "list_portfolios",
        "create_portfolio",
        "create_home",
        "start_onboarding_inspection",
        "list_room_types",
        "list_rooms",
        "create_room",
        "update_room",
        "create_asset",
        "update_asset",
        "move_asset",
        "record_asset_document",
        "list_asset_documents",
        "record_asset_research_value",
        "list_asset_research_values",
    } <= names


def test_inventory_tools_bind_identity_and_transaction_mode() -> None:
    adapter = RecordingAdapter()
    tools = _tools(adapter)

    portfolio = tools["create_portfolio"](name="Lakefront", client_id="client-1")
    portfolios = tools["list_portfolios"]()

    assert portfolio["operation"] == "create_portfolio"
    assert adapter.repository.calls[0] == (
        "create_portfolio",
        ("org-1", "user-1", "Lakefront", "client-1"),
        {},
    )
    assert portfolios["operation"] == "list_portfolios"
    assert adapter.repository.calls[1] == ("list_portfolios", ("org-1",), {})
    assert [mode for mode, _ in adapter.transactions] == ["write", "read"]


def test_create_home_and_inspection_use_server_tenant_context() -> None:
    adapter = RecordingAdapter()
    tools = _tools(adapter)

    tools["create_home"](
        portfolio_id="portfolio-1",
        name="Cabin 7",
        client_id="home-client",
        unit_code="C7",
        formatted_address="7 Lake Road",
    )
    tools["start_onboarding_inspection"](home_id="home-1", client_id="inspection-client")

    assert adapter.repository.calls[0] == (
        "create_home",
        ("org-1", "user-1", "portfolio-1", "Cabin 7", "home-client"),
        {"unit_code": "C7", "formatted_address": "7 Lake Road"},
    )
    assert adapter.repository.calls[1] == (
        "start_inspection",
        ("org-1", "user-1", "home-1", "onboarding", "inspection-client"),
        {},
    )


def test_document_tool_accepts_photo_or_source_url_without_object_key() -> None:
    adapter = RecordingAdapter()
    tools = _tools(adapter)

    tools["record_asset_document"](
        asset_id="asset-1",
        kind="receipt",
        photo_id="photo-1",
        source_url="",
    )

    name, args, kwargs = adapter.repository.calls[0]
    assert name == "record_asset_document"
    assert args == ("org-1", "asset-1", "receipt")
    assert kwargs == {"photo_id": "photo-1", "source_url": None}
    assert "object_key" not in kwargs


def test_read_only_role_cannot_use_mutating_inventory_tools() -> None:
    adapter = RecordingAdapter()
    owner = TenantContext("owner-1", "org-1", frozenset({"OWNER"}), frozenset())
    tools = {tool.tool_name: tool for tool in build_inventory_tools(adapter, owner)}

    result = tools["create_portfolio"](name="Blocked", client_id="client-1")

    assert result["ok"] is False
    assert result["error"]["code"] == "forbidden"
    assert adapter.repository.calls == []
