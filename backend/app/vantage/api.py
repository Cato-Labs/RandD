from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from .context import TenantContext
from .domain import ConflictError, DomainError, VantageRepository
from .media_finalizer import OriginalMediaService


class InspectionCreate(BaseModel):
    homeId: str
    type: str
    clientId: str


class PortfolioCreate(BaseModel):
    name: str
    clientId: str


class HomeCreate(BaseModel):
    portfolioId: str
    name: str
    clientId: str
    unitCode: str | None = None
    formattedAddress: str | None = None


class RoomCreate(BaseModel):
    roomTypeId: str
    name: str
    inspectionId: str | None = None
    clientId: str


class AssetCreate(BaseModel):
    assetType: str = ""
    name: str = ""
    inspectionId: str | None = None
    clientId: str
    locationDescription: str | None = None
    manufacturer: str | None = None
    modelNumber: str | None = None
    serialNumber: str | None = None
    quantity: int | None = None
    condition: str | None = None
    conditionNotes: str | None = None
    purchaseDate: str | None = None
    purchasePrice: str | None = None
    estimatedCurrentValue: str | None = None
    estimatedReplacementCost: str | None = None
    warrantyProvider: str | None = None
    warrantyExpiration: str | None = None
    dimensions: str | None = None
    colorFinish: str | None = None
    installationDate: str | None = None
    lastServiceDate: str | None = None
    productIdentifier: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class RoomUpdate(BaseModel):
    roomTypeId: str | None = None
    name: str | None = None
    floorArea: str | None = None
    notes: str | None = None
    displayOrder: int | None = None


class AssetUpdate(BaseModel):
    assetType: str | None = None
    name: str | None = None
    locationDescription: str | None = None
    manufacturer: str | None = None
    modelNumber: str | None = None
    serialNumber: str | None = None
    quantity: int | None = None
    condition: str | None = None
    conditionNotes: str | None = None
    purchaseDate: str | None = None
    purchasePrice: str | None = None
    estimatedCurrentValue: str | None = None
    estimatedReplacementCost: str | None = None
    warrantyProvider: str | None = None
    warrantyExpiration: str | None = None
    dimensions: str | None = None
    colorFinish: str | None = None
    installationDate: str | None = None
    lastServiceDate: str | None = None
    productIdentifier: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    roomId: str | None = None


class AssetDocumentCreate(BaseModel):
    kind: str
    photoId: str | None = None
    sourceUrl: str | None = None


class AssetResearchValueCreate(BaseModel):
    fieldName: str
    value: Any
    provenance: str
    sourceReference: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    confirmed: bool = False


class UploadCreate(BaseModel):
    homeId: str
    roomId: str
    assetId: str
    inspectionId: str | None = None
    clientId: str
    filename: str
    mimeType: str
    byteSize: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)


class UploadComplete(BaseModel):
    versionId: str = Field(min_length=1)


def _raise(error: DomainError) -> None:
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE if error.code in {"database_unavailable", "database_timeout"} else (
        status.HTTP_409_CONFLICT if isinstance(error, ConflictError) else (
        status.HTTP_404_NOT_FOUND if error.code == "not_found" else status.HTTP_422_UNPROCESSABLE_ENTITY
    ))
    raise HTTPException(status_code=status_code, detail={"error": {
        "code": error.code, "message": str(error), "retryable": error.retryable, "fields": error.fields,
    }}) from error


def _require_write(context: TenantContext) -> None:
    if not context.has_role("ORG_ADMIN", "PROPERTY_MANAGER", "INSPECTOR"):
        raise HTTPException(status_code=403, detail={"error": {"code": "forbidden", "message": "This role has read-only access", "retryable": False, "fields": {}}})


def _require_home_read(context: TenantContext, home_id: str) -> None:
    if context.has_role("OWNER") and home_id not in context.home_grants:
        raise HTTPException(status_code=404, detail={"error": {"code": "not_found", "message": "Home was not found", "retryable": False, "fields": {}}})


def create_vantage_router(
    repository: Any,
    context_dependency: Callable[..., TenantContext],
    media_service: OriginalMediaService | None = None,
) -> APIRouter:
    """Build routes without global auth/database state.

    `context_dependency` must verify the secure session and active membership;
    request payloads never contain or override organization/user identity.
    """
    router = APIRouter(prefix="/api", tags=["vantage-v1"])
    Context = Annotated[TenantContext, Depends(context_dependency)]

    def call(context: TenantContext, method: str, *args: Any, read_only: bool = False, **kwargs: Any) -> Any:
        transaction = getattr(repository, "read_only_transaction" if read_only else "transaction", None)
        if transaction is None:
            return getattr(repository, method)(*args, **kwargs)
        with transaction(context) as active:
            return getattr(active, method)(*args, **kwargs)

    def read_asset_collection(
        context: TenantContext, asset_id: str, method: str
    ) -> list[dict[str, Any]]:
        transaction = getattr(repository, "read_only_transaction", None)
        if transaction is None:
            asset = repository.get_asset(context.organization_id, asset_id)
            _require_home_read(context, asset["home_id"])
            return getattr(repository, method)(context.organization_id, asset_id)
        with transaction(context) as active:
            asset = active.get_asset(context.organization_id, asset_id)
            _require_home_read(context, asset["home_id"])
            return getattr(active, method)(context.organization_id, asset_id)

    @router.get("/portfolios")
    def portfolios(context: Context) -> list[dict[str, Any]]:
        try:
            return call(context, "list_portfolios", context.organization_id, read_only=True)
        except DomainError as error:
            _raise(error)

    @router.post("/portfolios", status_code=201)
    def create_portfolio(payload: PortfolioCreate, context: Context) -> dict[str, Any]:
        _require_write(context)
        try:
            return call(
                context,
                "create_portfolio",
                context.organization_id,
                context.user_id,
                payload.name,
                payload.clientId,
            )
        except DomainError as error:
            _raise(error)

    @router.post("/homes", status_code=201)
    def create_home(payload: HomeCreate, context: Context) -> dict[str, Any]:
        _require_write(context)
        try:
            return call(
                context,
                "create_home",
                context.organization_id,
                context.user_id,
                payload.portfolioId,
                payload.name,
                payload.clientId,
                unit_code=payload.unitCode,
                formatted_address=payload.formattedAddress,
            )
        except DomainError as error:
            _raise(error)

    @router.get("/room-types")
    def room_types(context: Context) -> list[dict[str, Any]]:
        try:
            return call(context, "list_room_types", context.organization_id, read_only=True)
        except DomainError as error:
            _raise(error)

    @router.post("/inspections", status_code=201)
    def start_inspection(payload: InspectionCreate, context: Context) -> dict[str, Any]:
        _require_write(context)
        _require_home_read(context, payload.homeId)
        try:
            return call(context, "start_inspection", context.organization_id, context.user_id, payload.homeId, payload.type, payload.clientId)
        except DomainError as error:
            _raise(error)

    @router.get("/inspections/{inspection_id}")
    def get_inspection(inspection_id: str, context: Context) -> dict[str, Any]:
        try:
            inspection = call(context, "get_inspection", context.organization_id, inspection_id, read_only=True)
            _require_home_read(context, inspection["home_id"])
            return inspection
        except DomainError as error:
            _raise(error)

    @router.post("/inspections/{inspection_id}/complete")
    def complete_inspection(inspection_id: str, context: Context) -> dict[str, Any]:
        _require_write(context)
        try:
            return call(context, "complete_onboarding", context.organization_id, context.user_id, inspection_id)
        except DomainError as error:
            _raise(error)

    @router.get("/homes/{home_id}/rooms")
    def rooms(home_id: str, context: Context) -> list[dict[str, Any]]:
        _require_home_read(context, home_id)
        try:
            return call(context, "list_rooms", context.organization_id, home_id, read_only=True)
        except DomainError as error:
            _raise(error)

    @router.post("/homes/{home_id}/rooms", status_code=201)
    def create_room(home_id: str, payload: RoomCreate, context: Context, idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None) -> dict[str, Any]:
        _require_write(context)
        _require_home_read(context, home_id)
        try:
            return call(context, "create_room", context.organization_id, context.user_id, home_id, payload.inspectionId, payload.roomTypeId, payload.name, payload.clientId or idempotency_key or "")
        except DomainError as error:
            _raise(error)

    @router.patch("/rooms/{room_id}")
    def update_room(room_id: str, payload: RoomUpdate, context: Context) -> dict[str, Any]:
        _require_write(context)
        values = {
            "room_type_id": payload.roomTypeId,
            "name": payload.name,
            "floor_area": payload.floorArea,
            "notes": payload.notes,
            "display_order": payload.displayOrder,
        }
        try:
            return call(context, "update_room",
                context.organization_id,
                context.user_id,
                room_id,
                **{key: value for key, value in values.items() if value is not None},
            )
        except DomainError as error:
            _raise(error)

    @router.delete("/rooms/{room_id}")
    def archive_room(room_id: str, context: Context) -> dict[str, Any]:
        _require_write(context)
        try:
            return call(context, "archive_room", context.organization_id, context.user_id, room_id)
        except DomainError as error:
            _raise(error)

    @router.get("/rooms/{room_id}/assets")
    def assets(room_id: str, context: Context) -> list[dict[str, Any]]:
        try:
            transaction = getattr(repository, "read_only_transaction", None)
            if transaction is None:
                room = repository.get_room(context.organization_id, room_id)
                _require_home_read(context, room["home_id"])
                return repository.list_assets(context.organization_id, room_id)
            with transaction(context) as active:
                room = active.get_room(context.organization_id, room_id)
                _require_home_read(context, room["home_id"])
                return active.list_assets(context.organization_id, room_id)
        except DomainError as error:
            _raise(error)

    @router.post("/rooms/{room_id}/assets", status_code=201)
    def create_asset(room_id: str, payload: AssetCreate, context: Context, idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None) -> dict[str, Any]:
        _require_write(context)
        metadata = {
            "location_description": payload.locationDescription,
            "manufacturer": payload.manufacturer,
            "model_number": payload.modelNumber,
            "serial_number": payload.serialNumber,
            "quantity": payload.quantity,
            "condition": payload.condition,
            "condition_notes": payload.conditionNotes,
            "purchase_date": payload.purchaseDate,
            "purchase_price": payload.purchasePrice,
            "estimated_current_value": payload.estimatedCurrentValue,
            "estimated_replacement_cost": payload.estimatedReplacementCost,
            "warranty_provider": payload.warrantyProvider,
            "warranty_expiration": payload.warrantyExpiration,
            "dimensions": payload.dimensions,
            "color_finish": payload.colorFinish,
            "installation_date": payload.installationDate,
            "last_service_date": payload.lastServiceDate,
            "product_identifier": payload.productIdentifier,
            "notes": payload.notes,
            "tags": payload.tags,
        }
        try:
            return call(
                context,
                "create_asset",
                context.organization_id,
                context.user_id,
                room_id,
                payload.inspectionId,
                payload.assetType,
                payload.name,
                payload.clientId or idempotency_key or "",
                **{key: value for key, value in metadata.items() if value is not None},
            )
        except DomainError as error:
            _raise(error)

    @router.patch("/assets/{asset_id}")
    def update_asset(asset_id: str, payload: AssetUpdate, context: Context) -> dict[str, Any]:
        _require_write(context)
        values = {
            "asset_type": payload.assetType, "name": payload.name, "location_description": payload.locationDescription,
            "manufacturer": payload.manufacturer, "model_number": payload.modelNumber, "serial_number": payload.serialNumber,
            "quantity": payload.quantity, "condition": payload.condition, "condition_notes": payload.conditionNotes,
            "purchase_date": payload.purchaseDate, "purchase_price": payload.purchasePrice,
            "estimated_current_value": payload.estimatedCurrentValue,
            "estimated_replacement_cost": payload.estimatedReplacementCost,
            "warranty_provider": payload.warrantyProvider, "warranty_expiration": payload.warrantyExpiration,
            "dimensions": payload.dimensions, "color_finish": payload.colorFinish,
            "installation_date": payload.installationDate, "last_service_date": payload.lastServiceDate,
            "product_identifier": payload.productIdentifier, "notes": payload.notes, "tags": payload.tags,
        }
        try:
            transaction = getattr(repository, "transaction", None)
            if transaction is None:
                active = repository
                if payload.roomId is not None:
                    active.move_asset(context.organization_id, context.user_id, asset_id, payload.roomId)
                return active.update_asset(context.organization_id, context.user_id, asset_id, **{k: v for k, v in values.items() if v is not None})
            with transaction(context) as active:
                if payload.roomId is not None:
                    active.move_asset(context.organization_id, context.user_id, asset_id, payload.roomId)
                return active.update_asset(context.organization_id, context.user_id, asset_id, **{k: v for k, v in values.items() if v is not None})
        except DomainError as error:
            _raise(error)

    @router.get("/assets/{asset_id}/documents")
    def asset_documents(asset_id: str, context: Context) -> list[dict[str, Any]]:
        try:
            return read_asset_collection(context, asset_id, "list_asset_documents")
        except DomainError as error:
            _raise(error)

    @router.post("/assets/{asset_id}/documents", status_code=201)
    def record_asset_document(
        asset_id: str, payload: AssetDocumentCreate, context: Context
    ) -> dict[str, Any]:
        _require_write(context)
        try:
            return call(
                context,
                "record_asset_document",
                context.organization_id,
                asset_id,
                payload.kind,
                photo_id=payload.photoId,
                source_url=payload.sourceUrl,
            )
        except DomainError as error:
            _raise(error)

    @router.get("/assets/{asset_id}/research-values")
    def asset_research_values(asset_id: str, context: Context) -> list[dict[str, Any]]:
        try:
            return read_asset_collection(context, asset_id, "list_asset_research_values")
        except DomainError as error:
            _raise(error)

    @router.post("/assets/{asset_id}/research-values", status_code=201)
    def record_asset_research_value(
        asset_id: str, payload: AssetResearchValueCreate, context: Context
    ) -> dict[str, Any]:
        _require_write(context)
        try:
            return call(
                context,
                "record_asset_research_value",
                context.organization_id,
                asset_id,
                field_name=payload.fieldName,
                value=payload.value,
                provenance=payload.provenance,
                source_reference=payload.sourceReference,
                confidence=payload.confidence,
                confirmed=payload.confirmed,
            )
        except DomainError as error:
            _raise(error)

    @router.post("/media/uploads", status_code=201)
    def create_upload(payload: UploadCreate, context: Context) -> dict[str, Any]:
        _require_write(context)
        _require_home_read(context, payload.homeId)
        if media_service is None:
            raise HTTPException(status_code=503, detail={"error": {
                "code": "original_storage_unavailable", "message": "Original storage is not configured",
                "retryable": True, "fields": {},
            }})
        try:
            return media_service.initiate(
                context.organization_id, context.user_id, home_id=payload.homeId,
                room_id=payload.roomId, asset_id=payload.assetId,
                inspection_id=payload.inspectionId, client_id=payload.clientId,
                filename=payload.filename, mime_type=payload.mimeType,
                byte_size=payload.byteSize, sha256=payload.sha256,
            )
        except DomainError as error:
            _raise(error)

    @router.post("/media/uploads/{upload_id}/complete")
    def complete_upload(upload_id: str, payload: UploadComplete, context: Context) -> dict[str, Any]:
        _require_write(context)
        if media_service is None:
            raise HTTPException(status_code=503, detail={"error": {
                "code": "original_storage_unavailable", "message": "Original storage is not configured",
                "retryable": True, "fields": {},
            }})
        try:
            upload = call(context, "get_original_upload", context.organization_id, upload_id, read_only=True)
            _require_home_read(context, upload["home_id"])
            return media_service.finalize(context.organization_id, upload_id, payload.versionId, user_id=context.user_id)
        except DomainError as error:
            _raise(error)

    @router.get("/media/uploads/{upload_id}")
    def read_original(upload_id: str, context: Context) -> dict[str, Any]:
        if media_service is None:
            raise HTTPException(status_code=503, detail={"error": {
                "code": "original_storage_unavailable", "message": "Original storage is not configured",
                "retryable": True, "fields": {},
            }})
        try:
            upload = call(context, "get_original_upload", context.organization_id, upload_id, read_only=True)
            _require_home_read(context, upload["home_id"])
            return media_service.signed_read(context.organization_id, upload_id, user_id=context.user_id)
        except DomainError as error:
            _raise(error)

    return router
