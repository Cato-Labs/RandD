from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.vantage.domain import ConflictError, DomainError, VantageRepository
from app.vantage.schema import PHOTO_PURPOSES, ROOM_TYPES, install_sqlite_schema


@pytest.fixture()
def repo(tmp_path: Path) -> VantageRepository:
    path = tmp_path / "live-home.sqlite"
    connection = sqlite3.connect(path)
    install_sqlite_schema(connection)
    repository = VantageRepository(lambda: sqlite3.connect(path))
    repository.bootstrap_organization("org-a", "Alpha", "portfolio-bootstrap-a")
    repository.bootstrap_organization("org-b", "Beta", "portfolio-bootstrap-b")
    repository.bootstrap_user("user-a", "a@example.com", "org-a", "INSPECTOR")
    repository.bootstrap_user("user-b", "b@example.com", "org-b", "INSPECTOR")
    return repository


def _inventory(repository: VantageRepository) -> tuple[dict, dict, dict, dict]:
    portfolio = repository.create_portfolio("org-a", "user-a", "Lake Homes", "portfolio-client")
    home = repository.create_home(
        "org-a",
        "user-a",
        portfolio["id"],
        "Lake House",
        "home-client",
        unit_code="LH-1",
        formatted_address="1 Lake Way",
    )
    inspection = repository.start_inspection(
        "org-a", "user-a", home["id"], "onboarding", "inspection-client"
    )
    room_type = next(row for row in repository.list_room_types("org-a") if row["name"] == "Kitchen")
    room = repository.create_room(
        "org-a", "user-a", home["id"], inspection["id"], room_type["id"], "Kitchen", "room-client"
    )
    asset = repository.create_asset(
        "org-a",
        "user-a",
        room["id"],
        inspection["id"],
        "Appliance",
        "Range",
        "asset-client",
    )
    return home, inspection, room, asset


def _verified_document_photo(
    repository: VantageRepository, home: dict, inspection: dict, room: dict, asset: dict
) -> dict:
    upload = repository.initiate_original_upload(
        "org-a",
        "user-a",
        home_id=home["id"],
        room_id=room["id"],
        asset_id=asset["id"],
        inspection_id=inspection["id"],
        client_id="document-photo",
        storage_bucket="vantage-originals",
        filename="receipt.jpg",
        mime_type="image/jpeg",
        byte_size=25,
        sha256="a" * 64,
        purpose="asset_document",
    )
    repository._finalize_original_from_storage(
        "org-a",
        upload["upload_id"],
        {
            "storage_bucket": upload["storage_bucket"],
            "object_key": upload["object_key"],
            "storage_version_id": "version-document",
            "byte_size": 25,
            "mime_type": "image/jpeg",
            "sha256": "a" * 64,
            "etag": "etag-document",
            "encryption_algorithm": "aws:kms",
            "kms_key_id": "kms-key",
            "object_lock_mode": "COMPLIANCE",
            "retention_until": "2033-01-01T00:00:00+00:00",
            "legal_hold_status": None,
        },
    )
    return {"id": upload["photo_id"], "object_key": upload["object_key"]}


def test_fixed_room_catalog_and_document_photo_purpose_are_normalized(repo: VantageRepository) -> None:
    expected_additions = {
        "Front Yard", "Back Yard", "Garage", "Deck / Patio", "Driveway", "Laundry Room",
        "Office", "Attic", "Storage", "Deck", "Porch", "Boat Deck", "Living Room", "Hallway",
        "Family Room", "Sun Room", "Library", "Theater", "Pantry", "Walk-in Closet",
    }
    assert expected_additions <= set(ROOM_TYPES)
    assert len(ROOM_TYPES) == len(set(ROOM_TYPES))
    assert "Guest House/Casida" not in ROOM_TYPES
    assert "asset_document" in PHOTO_PURPOSES
    seeded = [row["name"] for row in repo.list_room_types("org-a")]
    assert set(seeded) == set(ROOM_TYPES)
    assert len(seeded) == len(set(seeded))


def test_portfolio_and_home_creation_are_scoped_replay_idempotent(repo: VantageRepository) -> None:
    portfolio = repo.create_portfolio("org-a", "user-a", "Coastal", "portfolio-1")
    replay = repo.create_portfolio("org-a", "user-a", "Coastal", "portfolio-1")
    assert replay["id"] == portfolio["id"]
    assert [row["name"] for row in repo.list_portfolios("org-a")] == ["Alpha", "Coastal"]
    with pytest.raises(ConflictError) as conflict:
        repo.create_portfolio("org-a", "user-a", "Mountain", "portfolio-1")
    assert conflict.value.code == "idempotency_payload_conflict"
    with pytest.raises(ConflictError) as duplicate_name:
        repo.create_portfolio("org-a", "user-a", "Coastal", "portfolio-2")
    assert duplicate_name.value.code == "portfolio_name_conflict"

    home = repo.create_home(
        "org-a", "user-a", portfolio["id"], "Coastal Home", "home-1",
        unit_code="C-1", formatted_address="1 Coast Road",
    )
    home_replay = repo.create_home(
        "org-a", "user-a", portfolio["id"], "Coastal Home", "home-1",
        unit_code="C-1", formatted_address="1 Coast Road",
    )
    assert home_replay["id"] == home["id"]
    assert home["created_by"] == "user-a" and home["client_id"] == "home-1"
    with pytest.raises(ConflictError):
        repo.create_home("org-a", "user-a", portfolio["id"], "Changed", "home-1")
    with pytest.raises(DomainError) as cross_tenant:
        repo.create_home("org-b", "user-b", portfolio["id"], "Attack", "home-attack")
    assert cross_tenant.value.code == "not_found"


def test_all_asset_metadata_round_trips_and_is_normalized(repo: VantageRepository) -> None:
    home, inspection, room, _asset = _inventory(repo)
    asset = repo.create_asset(
        "org-a", "user-a", room["id"], inspection["id"], " Appliance ", " Range ", "full-asset",
        location_description=" Island ", manufacturer=" Acme ", model_number=" M1 ", serial_number=" S1 ",
        quantity=2, condition=" Good ", condition_notes=" Minor wear ", purchase_date="2025-01-02",
        purchase_price="1200.5", estimated_current_value=900,
        estimated_replacement_cost="1500.00", warranty_provider=" Maker ",
        warranty_expiration="2028-01-02", dimensions="30x30", color_finish="Steel",
        installation_date="2025-01-03", last_service_date="2026-01-04",
        product_identifier="UPC-1", notes="Primary range", tags=[" kitchen ", "premium", "kitchen"],
    )
    assert asset["home_id"] == home["id"]
    assert asset["asset_type"] == "Appliance" and asset["name"] == "Range"
    assert asset["quantity"] == 2 and asset["purchase_date"] == "2025-01-02"
    assert asset["purchase_price"] == "1200.50"
    assert asset["estimated_current_value"] == "900.00"
    assert asset["estimated_replacement_cost"] == "1500.00"
    assert asset["tags"] == ["kitchen", "premium"]

    updated = repo.update_asset(
        "org-a", "user-a", asset["id"], quantity=3, purchase_price="1300",
        warranty_expiration=None, tags=["updated"], color_finish="Black",
    )
    assert updated["quantity"] == 3 and updated["purchase_price"] == "1300.00"
    assert updated["warranty_expiration"] is None and updated["tags"] == ["updated"]
    with pytest.raises(DomainError) as bad_quantity:
        repo.update_asset("org-a", "user-a", asset["id"], quantity=0)
    assert bad_quantity.value.code == "validation_error"
    with pytest.raises(DomainError):
        repo.update_asset("org-a", "user-a", asset["id"], purchase_date="01/02/2025")


def test_asset_documents_require_verified_same_asset_photo_or_source_url(repo: VantageRepository) -> None:
    home, inspection, room, asset = _inventory(repo)
    photo = _verified_document_photo(repo, home, inspection, room, asset)
    receipt = repo.record_asset_document(
        "org-a", asset["id"], "receipt", photo_id=photo["id"]
    )
    assert receipt["object_key"] == photo["object_key"] and receipt["source_url"] is None
    replay = repo.record_asset_document("org-a", asset["id"], "receipt", photo_id=photo["id"])
    assert replay["id"] == receipt["id"]
    manual = repo.record_asset_document(
        "org-a", asset["id"], "manual", source_url="https://manufacturer.example/manual.pdf"
    )
    assert manual["source_url"].endswith("manual.pdf") and manual["object_key"] is None
    assert [row["kind"] for row in repo.list_asset_documents("org-a", asset["id"])] == ["receipt", "manual"]
    with pytest.raises(DomainError):
        repo.record_asset_document("org-a", asset["id"], "manual")
    with pytest.raises(DomainError):
        repo.record_asset_document(
            "org-a", asset["id"], "manual", photo_id=photo["id"], source_url="https://example.com"
        )
    with pytest.raises(DomainError):
        repo.record_asset_document("org-a", asset["id"], "unknown", source_url="https://example.com")


def test_asset_research_values_preserve_json_provenance_confidence_and_confirmation(repo: VantageRepository) -> None:
    _home, _inspection, _room, asset = _inventory(repo)
    value = repo.record_asset_research_value(
        "org-a", asset["id"], field_name="estimated_replacement_cost",
        value={"amount": "1599.00", "currency": "USD"},
        provenance="externally_researched", source_reference="https://manufacturer.example/range",
        confidence="0.875", confirmed=False,
    )
    assert value["value"] == {"amount": "1599.00", "currency": "USD"}
    assert value["confidence"] == pytest.approx(0.875)
    assert value["confirmed"] is False
    assert repo.list_asset_research_values("org-a", asset["id"])[0]["id"] == value["id"]
    with pytest.raises(DomainError):
        repo.record_asset_research_value(
            "org-a", asset["id"], field_name="model_number", value="M1",
            provenance="guessed", confidence=0.5,
        )
    with pytest.raises(DomainError):
        repo.record_asset_research_value(
            "org-a", asset["id"], field_name="model_number", value="M1",
            provenance="agent_observed", confidence=1.1,
        )


def test_live_home_migration_is_additive_and_freezes_foundation_migrations() -> None:
    root = Path(__file__).resolve().parents[2]
    migration = root / "backend/migrations/0007_live_home_onboarding.sql"
    sql = migration.read_text()
    assert "ALTER TABLE portfolio ADD COLUMN created_by" in sql
    assert "ALTER TABLE portfolio ADD COLUMN client_id" in sql
    assert "ALTER TABLE home ADD COLUMN created_by" in sql
    assert "ALTER TABLE home ADD COLUMN client_id" in sql
    assert "portfolio_org_name_unique" in sql
    assert "asset_document_kind_check" in sql
    assert "asset_document_reference_xor_check" in sql
    assert "asset_document_object_unique" in sql
    assert "asset_document_source_unique" in sql
    assert "ALTER TYPE photo_purpose ADD VALUE" in sql
    assert "ON CONFLICT (organization_id,name) DO NOTHING" in sql
    assert "Guest House/Casida" not in sql
