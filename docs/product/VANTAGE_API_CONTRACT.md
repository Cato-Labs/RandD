# Vantage v1 API and Event Contract

All authenticated operations derive `user_id`, active `org_id`, and roles from the session. Client-supplied tenant identifiers are rejected. Retryable writes accept `Idempotency-Key`; created domain records also accept stable client UUIDs.

## Authentication

- `POST /api/auth/code/request` `{email}`
- `POST /api/auth/code/verify` `{email, code}`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/auth/active-organization` `{organizationId}`
- `POST /api/auth/ws-token`

## Onboarding and inventory

- `GET /api/room-types`
- `GET|POST /api/homes/{homeId}/rooms`
- `PATCH|DELETE /api/rooms/{roomId}` (`DELETE` archives)
- `GET|POST /api/rooms/{roomId}/assets`
- `PATCH /api/assets/{assetId}` (including authorized room move)
- `POST /api/assets/duplicates/search`
- `POST /api/inspections` `{homeId, type: onboarding|turnover, clientId}`
- `GET /api/inspections/{inspectionId}`
- `POST /api/inspections/{inspectionId}/sync`
- `POST /api/inspections/{inspectionId}/complete`

## Original media

- `POST /api/media/uploads` creates an upload record and signed/resumable target.
- `POST /api/media/uploads/{uploadId}/complete` verifies size, MIME, object existence, and SHA-256 before association.
- `GET /api/media/{mediaId}` returns authorized metadata and a short-lived original/derivative URL.

An asset has `completionStatus: draft|complete`; only a verified original can produce `complete`.

## Error envelope

```json
{
  "error": {
    "code": "stable_machine_code",
    "message": "Human-readable explanation",
    "retryable": false,
    "fields": {"field": "problem"},
    "currentVersion": 3
  }
}
```

## WebSocket approval events

- Server: `approval_requested` `{approvalId, inspectionId, itemId?, assetId?, proposedVerdict?, rationale, mediaId, expiresAt}`
- Client: `approval_resolved` `{approvalId, decision: approve|reshoot|cancel, feedback?}`
- Server: `approval_completed|approval_expired|approval_cancelled`

Approval IDs are scoped to the authenticated WebSocket session and persisted inspection; ordinary chat text cannot resolve them.

