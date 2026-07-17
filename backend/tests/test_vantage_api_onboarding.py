from __future__ import annotations

from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.vantage.api import create_vantage_router
from app.vantage.context import TenantContext


class RecordingRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, name: str):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "get_asset":
                return {"id": args[-1], "home_id": "home-denied"}
            if name in {"list_asset_documents", "list_asset_research_values"}:
                return []
            return {"operation": name}

        return record


class RecordingAdapter:
    def __init__(self) -> None:
        self.active = RecordingRepository()

    @contextmanager
    def transaction(self, _context):
        yield self.active

    @contextmanager
    def read_only_transaction(self, _context):
        yield self.active


def _client() -> tuple[TestClient, RecordingRepository]:
    adapter = RecordingAdapter()
    context = TenantContext("user-1", "org-1", frozenset({"INSPECTOR"}), frozenset())
    app = FastAPI()
    app.include_router(create_vantage_router(adapter, lambda: context))
    return TestClient(app), adapter.active


def _owner_client() -> tuple[TestClient, RecordingRepository]:
    adapter = RecordingAdapter()
    context = TenantContext("owner-1", "org-1", frozenset({"OWNER"}), frozenset({"home-allowed"}))
    app = FastAPI()
    app.include_router(create_vantage_router(adapter, lambda: context))
    return TestClient(app), adapter.active


def test_portfolio_and_home_creation_use_authenticated_identity() -> None:
    client, repository = _client()

    assert client.post(
        "/api/portfolios",
        json={"name": "Lakefront", "clientId": "portfolio-client"},
    ).status_code == 201
    assert client.post(
        "/api/homes",
        json={
            "portfolioId": "portfolio-1",
            "name": "Cabin 7",
            "clientId": "home-client",
            "unitCode": "C7",
            "formattedAddress": "7 Lake Road",
        },
    ).status_code == 201

    assert repository.calls == [
        ("create_portfolio", ("org-1", "user-1", "Lakefront", "portfolio-client"), {}),
        (
            "create_home",
            ("org-1", "user-1", "portfolio-1", "Cabin 7", "home-client"),
            {"unit_code": "C7", "formatted_address": "7 Lake Road"},
        ),
    ]


def test_asset_create_exposes_full_existing_metadata() -> None:
    client, repository = _client()
    response = client.post(
        "/api/rooms/room-1/assets",
        json={
            "clientId": "asset-client",
            "inspectionId": "inspection-1",
            "assetType": "Appliance",
            "name": "Dryer",
            "manufacturer": "GE",
            "modelNumber": "GTX22",
            "serialNumber": "SER-1",
            "quantity": 1,
            "purchaseDate": "2025-01-02",
            "purchasePrice": "599.00",
            "estimatedCurrentValue": "450.00",
            "estimatedReplacementCost": "699.00",
            "warrantyProvider": "GE",
            "warrantyExpiration": "2028-01-02",
            "dimensions": "27x44x30",
            "colorFinish": "White",
            "installationDate": "2025-01-03",
            "lastServiceDate": "2026-03-04",
            "productIdentifier": "0123456789",
            "locationDescription": "Laundry alcove",
            "condition": "good",
            "conditionNotes": "Minor scuff",
            "notes": "Vent inspected",
            "tags": ["laundry", "electric"],
        },
    )

    assert response.status_code == 201
    name, args, kwargs = repository.calls[0]
    assert name == "create_asset"
    assert args == (
        "org-1",
        "user-1",
        "room-1",
        "inspection-1",
        "Appliance",
        "Dryer",
        "asset-client",
    )
    assert kwargs["manufacturer"] == "GE"
    assert kwargs["estimated_replacement_cost"] == "699.00"
    assert kwargs["tags"] == ["laundry", "electric"]


def test_asset_document_and_research_endpoints_use_existing_records() -> None:
    client, repository = _client()

    assert client.post(
        "/api/assets/asset-1/documents",
        json={"kind": "receipt", "photoId": "photo-1"},
    ).status_code == 201
    assert client.post(
        "/api/assets/asset-1/research-values",
        json={
            "fieldName": "replacement_cost",
            "value": 699,
            "provenance": "externally_researched",
            "sourceReference": "https://example.com/dryer",
            "confidence": 0.92,
            "confirmed": False,
        },
    ).status_code == 201

    assert repository.calls[0] == (
        "record_asset_document",
        ("org-1", "asset-1", "receipt"),
        {"photo_id": "photo-1", "source_url": None},
    )
    assert repository.calls[1] == (
        "record_asset_research_value",
        ("org-1", "asset-1"),
        {
            "field_name": "replacement_cost",
            "value": 699,
            "provenance": "externally_researched",
            "source_reference": "https://example.com/dryer",
            "confidence": 0.92,
            "confirmed": False,
        },
    )


def test_asset_document_and_research_reads_honor_owner_home_grants() -> None:
    client, repository = _owner_client()

    assert client.get("/api/assets/asset-1/documents").status_code == 404
    assert client.get("/api/assets/asset-1/research-values").status_code == 404
    assert [name for name, _args, _kwargs in repository.calls] == [
        "get_asset",
        "get_asset",
    ]
