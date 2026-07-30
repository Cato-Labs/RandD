"""Direct Strands tools over the Vantage repository using native ToolContext."""

from __future__ import annotations

from typing import Any, Literal

from strands import ToolContext, tool

from app.vantage.context import TenantContext
from app.vantage.domain import DomainError

WRITE_ROLES = ("ORG_ADMIN", "PROPERTY_MANAGER", "INSPECTOR")


def _runtime(tool_context: ToolContext) -> tuple[Any, TenantContext]:
    state = tool_context.invocation_state
    repository = state.get("repository")
    if repository is None:
        raise RuntimeError("repository is unavailable in Strands invocation_state")
    context = TenantContext(
        organization_id=str(state["organization_id"]),
        user_id=str(state["user_id"]),
        roles=frozenset(str(value) for value in state.get("roles", ())),
        home_grants=frozenset(str(value) for value in state.get("home_grants", ())),
    )
    return repository, context


def _call(
    tool_context: ToolContext,
    method: str,
    *args: Any,
    read_only: bool = False,
    **kwargs: Any,
) -> Any:
    repository, context = _runtime(tool_context)
    if not read_only and not context.has_role(*WRITE_ROLES):
        raise DomainError("forbidden", "This role has read-only access")
    transaction = getattr(
        repository,
        "read_only_transaction" if read_only else "transaction",
        None,
    )
    if transaction is None:
        return getattr(repository, method)(*args, **kwargs)
    with transaction(context) as active:
        return getattr(active, method)(*args, **kwargs)


def _tenant(tool_context: ToolContext) -> TenantContext:
    return _runtime(tool_context)[1]


@tool(context=True)
def list_portfolios(tool_context: ToolContext) -> Any:
    """List portfolios in the authenticated active organization."""
    context = _tenant(tool_context)
    return _call(tool_context, "list_portfolios", context.organization_id, read_only=True)


@tool(context=True)
def create_portfolio(tool_context: ToolContext, name: str, client_id: str) -> Any:
    """Create a replay-safe portfolio in the authenticated organization."""
    context = _tenant(tool_context)
    return _call(
        tool_context,
        "create_portfolio",
        context.organization_id,
        context.user_id,
        name,
        client_id,
    )


@tool(context=True)
def create_home(
    tool_context: ToolContext,
    portfolio_id: str,
    name: str,
    client_id: str,
    unit_code: str = "",
    formatted_address: str = "",
) -> Any:
    """Create a home inside an existing portfolio."""
    context = _tenant(tool_context)
    return _call(
        tool_context,
        "create_home",
        context.organization_id,
        context.user_id,
        portfolio_id,
        name,
        client_id,
        unit_code=unit_code or None,
        formatted_address=formatted_address or None,
    )


@tool(context=True)
def start_onboarding_inspection(
    tool_context: ToolContext,
    home_id: str,
    client_id: str,
) -> Any:
    """Start a replay-safe onboarding inspection for a home."""
    context = _tenant(tool_context)
    return _call(
        tool_context,
        "start_inspection",
        context.organization_id,
        context.user_id,
        home_id,
        "onboarding",
        client_id,
    )


@tool(context=True)
def list_room_types(tool_context: ToolContext) -> Any:
    """List the fixed room and outdoor-area catalog."""
    context = _tenant(tool_context)
    return _call(tool_context, "list_room_types", context.organization_id, read_only=True)


@tool(context=True)
def list_rooms(tool_context: ToolContext, home_id: str) -> Any:
    """List active rooms belonging to a home."""
    context = _tenant(tool_context)
    return _call(tool_context, "list_rooms", context.organization_id, home_id, read_only=True)


@tool(context=True)
def create_room(
    tool_context: ToolContext,
    home_id: str,
    room_type_id: str,
    name: str,
    client_id: str,
    inspection_id: str = "",
) -> Any:
    """Create a room or outdoor area in a home."""
    context = _tenant(tool_context)
    return _call(
        tool_context,
        "create_room",
        context.organization_id,
        context.user_id,
        home_id,
        inspection_id or None,
        room_type_id,
        name,
        client_id,
    )


@tool(context=True)
def update_room(
    tool_context: ToolContext,
    room_id: str,
    name: str = "",
    room_type_id: str = "",
    floor_area: str = "",
    notes: str = "",
    display_order: int | None = None,
) -> Any:
    """Update the supplied room fields."""
    context = _tenant(tool_context)
    values = {
        "name": name or None,
        "room_type_id": room_type_id or None,
        "floor_area": floor_area or None,
        "notes": notes or None,
        "display_order": display_order,
    }
    return _call(
        tool_context,
        "update_room",
        context.organization_id,
        context.user_id,
        room_id,
        **{key: value for key, value in values.items() if value is not None},
    )


@tool(context=True)
def create_asset(
    tool_context: ToolContext,
    room_id: str,
    client_id: str,
    asset_type: str = "",
    name: str = "",
    inspection_id: str = "",
    location_description: str = "",
    manufacturer: str = "",
    model_number: str = "",
    serial_number: str = "",
    quantity: int | None = None,
    condition: Literal["", "GOOD", "FAIR", "POOR", "UNKNOWN"] = "",
    condition_notes: str = "",
    purchase_date: str = "",
    purchase_price: str = "",
    estimated_current_value: str = "",
    estimated_replacement_cost: str = "",
    warranty_provider: str = "",
    warranty_expiration: str = "",
    dimensions: str = "",
    color_finish: str = "",
    installation_date: str = "",
    last_service_date: str = "",
    product_identifier: str = "",
    notes: str = "",
    tags: list[str] | None = None,
) -> Any:
    """Create an asset in a room with the supplied observed metadata."""
    context = _tenant(tool_context)
    metadata = {
        "location_description": location_description or None,
        "manufacturer": manufacturer or None,
        "model_number": model_number or None,
        "serial_number": serial_number or None,
        "quantity": quantity,
        "condition": condition or None,
        "condition_notes": condition_notes or None,
        "purchase_date": purchase_date or None,
        "purchase_price": purchase_price or None,
        "estimated_current_value": estimated_current_value or None,
        "estimated_replacement_cost": estimated_replacement_cost or None,
        "warranty_provider": warranty_provider or None,
        "warranty_expiration": warranty_expiration or None,
        "dimensions": dimensions or None,
        "color_finish": color_finish or None,
        "installation_date": installation_date or None,
        "last_service_date": last_service_date or None,
        "product_identifier": product_identifier or None,
        "notes": notes or None,
        "tags": tags,
    }
    return _call(
        tool_context,
        "create_asset",
        context.organization_id,
        context.user_id,
        room_id,
        inspection_id or None,
        asset_type,
        name,
        client_id,
        **{key: value for key, value in metadata.items() if value is not None},
    )


@tool(context=True)
def update_asset(
    tool_context: ToolContext,
    asset_id: str,
    asset_type: str = "",
    name: str = "",
    location_description: str = "",
    manufacturer: str = "",
    model_number: str = "",
    serial_number: str = "",
    quantity: int | None = None,
    condition: Literal["", "GOOD", "FAIR", "POOR", "UNKNOWN"] = "",
    condition_notes: str = "",
    purchase_date: str = "",
    purchase_price: str = "",
    estimated_current_value: str = "",
    estimated_replacement_cost: str = "",
    warranty_provider: str = "",
    warranty_expiration: str = "",
    dimensions: str = "",
    color_finish: str = "",
    installation_date: str = "",
    last_service_date: str = "",
    product_identifier: str = "",
    notes: str = "",
    tags: list[str] | None = None,
) -> Any:
    """Update the supplied supported metadata fields on an existing asset."""
    context = _tenant(tool_context)
    changes = {
        "asset_type": asset_type or None,
        "name": name or None,
        "location_description": location_description or None,
        "manufacturer": manufacturer or None,
        "model_number": model_number or None,
        "serial_number": serial_number or None,
        "quantity": quantity,
        "condition": condition or None,
        "condition_notes": condition_notes or None,
        "purchase_date": purchase_date or None,
        "purchase_price": purchase_price or None,
        "estimated_current_value": estimated_current_value or None,
        "estimated_replacement_cost": estimated_replacement_cost or None,
        "warranty_provider": warranty_provider or None,
        "warranty_expiration": warranty_expiration or None,
        "dimensions": dimensions or None,
        "color_finish": color_finish or None,
        "installation_date": installation_date or None,
        "last_service_date": last_service_date or None,
        "product_identifier": product_identifier or None,
        "notes": notes or None,
        "tags": tags,
    }
    return _call(
        tool_context,
        "update_asset",
        context.organization_id,
        context.user_id,
        asset_id,
        **{key: value for key, value in changes.items() if value is not None},
    )


@tool(context=True)
def move_asset(tool_context: ToolContext, asset_id: str, target_room_id: str) -> Any:
    """Move an asset to another room in the same home."""
    context = _tenant(tool_context)
    return _call(
        tool_context,
        "move_asset",
        context.organization_id,
        context.user_id,
        asset_id,
        target_room_id,
    )


@tool(context=True)
def record_asset_document(
    tool_context: ToolContext,
    asset_id: str,
    kind: Literal["manual", "receipt", "warranty", "other"],
    photo_id: str = "",
    source_url: str = "",
) -> Any:
    """Attach a verified photo or source URL to an asset as a document."""
    context = _tenant(tool_context)
    return _call(
        tool_context,
        "record_asset_document",
        context.organization_id,
        asset_id,
        kind,
        photo_id=photo_id or None,
        source_url=source_url or None,
    )


@tool(context=True)
def list_asset_documents(tool_context: ToolContext, asset_id: str) -> Any:
    """List documents attached to an asset."""
    context = _tenant(tool_context)
    return _call(
        tool_context,
        "list_asset_documents",
        context.organization_id,
        asset_id,
        read_only=True,
    )


@tool(context=True)
def record_asset_research_value(
    tool_context: ToolContext,
    asset_id: str,
    field_name: str,
    value: Any,
    provenance: Literal[
        "user_entered", "photo_extracted", "online_research", "externally_researched"
    ],
    source_reference: str = "",
    confidence: float | None = None,
    confirmed: bool = False,
) -> Any:
    """Record one provenance-bearing observed or researched asset fact."""
    context = _tenant(tool_context)
    return _call(
        tool_context,
        "record_asset_research_value",
        context.organization_id,
        asset_id,
        field_name=field_name,
        value=value,
        provenance=provenance,
        source_reference=source_reference or None,
        confidence=confidence,
        confirmed=confirmed,
    )


@tool(context=True)
def list_asset_research_values(tool_context: ToolContext, asset_id: str) -> Any:
    """List provenance-bearing facts recorded for an asset."""
    context = _tenant(tool_context)
    return _call(
        tool_context,
        "list_asset_research_values",
        context.organization_id,
        asset_id,
        read_only=True,
    )


INVENTORY_TOOLS = [
    list_portfolios,
    create_portfolio,
    create_home,
    start_onboarding_inspection,
    list_room_types,
    list_rooms,
    create_room,
    update_room,
    create_asset,
    update_asset,
    move_asset,
    record_asset_document,
    list_asset_documents,
    record_asset_research_value,
    list_asset_research_values,
]
