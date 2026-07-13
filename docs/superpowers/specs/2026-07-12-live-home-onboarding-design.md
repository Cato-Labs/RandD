# Live Home Onboarding: agent-driven house, room, and asset creation with research formations

**Date:** 2026-07-12
**Status:** Approved design, pending implementation plan
**Owner:** Tim Hunter
**Relates to:** DAH-112 (PostgreSQL runtime + FORCE RLS, merged in PR #7)

## Goal

Let a field inspector onboard a never-before-seen house during a live video
walkthrough. The agent creates the house, its rooms (including outdoor areas
such as front yard and back yard), and the assets in each room — with full
asset metadata, warranty/receipt documents, and externally researched product
facts gathered by browser-equipped research formations the inspector can
watch live — all persisted in real time under the organization's tenant,
preserving the hierarchy:

```
Organization → Portfolio → Home → Room → Asset → {metadata, documents, research values}
```

The hierarchy is enforced by the database (composite foreign keys +
FORCE row-level security), not by application discipline.

## What already exists (build on, do not rebuild)

- `asset` table models the full metadata set (manufacturer, model/serial,
  quantity, condition, purchase date/price, estimated current value,
  replacement cost, warranty provider/expiration, dimensions, color/finish,
  install/service dates, product identifier, tags, notes).
- `asset_document` (kind, `object_key` or `source_url`) and
  `asset_research_value` (field_name, jsonb value, provenance enum
  `user_entered | agent_observed | photo_extracted | externally_researched`,
  source reference, confidence 0–1, confirmed flag) exist under RLS with
  runtime grants.
- Agent walkthrough tools: `create_room`, `create_asset`, `update_asset`,
  `identify_asset_from_view`, `take_photo`, `attach_original_photo`,
  `record_check`, `record_research_result`, `mark_low_confidence_value`,
  `lookup_product_information`, `request_approval`,
  `complete_onboarding_assessment` (`tool_policy.py`).
- WORM original-media pipeline (KMS + S3 Object Lock COMPLIANCE + SHA-256
  verification) from DAH-131.
- Replay-idempotency pattern: `UNIQUE(org, created_by, …, client_id)` +
  `_reject_conflicting_replay`, used by rooms/assets/inspections.
- `VantageRepository.create_home()` exists but has **no callers** — this
  feature exposes it (widened) rather than inventing a new path.
- **Multi-agent + browser tooling installed** (`strands-agents-tools`):
  `use_agent`, `batch`, `workflow`, `swarm`, `graph`, and `browser`
  (Playwright `LocalChromiumBrowser`). Verified action surface:
  `init_session`, `navigate`, `click`, `type`, `press_key`, `evaluate`,
  `get_text`, `get_html`, `screenshot`, tab management, cookies,
  `network_intercept`, and raw CDP via `execute_cdp`. Nothing to build —
  this feature only wires sessions and streams state. Also available:
  `research`, `exa`, `tavily`, `http_request`.
- **Frontend**: AI Elements `web-preview.tsx` (URL-driven preview panel with
  navigation and console) ready to render the research browser session.
- Field tool policy forbids `shell`, `editor`, `environment`,
  `http_request`, `load_tool` for the **field agent**
  (`FORBIDDEN_FIELD_TOOLS`). This stays — research formations carry the
  network tools instead (see Research Formations).

## Decisions made

1. **Portfolio:** the agent can create portfolios (`create_portfolio` tool),
   not just pick one. `home.portfolio_id` stays NOT NULL.
2. **Room types:** extend the fixed seeded catalog only — no free-form
   room-type creation. New entries: `Front Yard`, `Back Yard`, `Garage`,
   `Deck / Patio`, `Driveway`, `Laundry Room`, `Office`.
3. **Asset metadata:** expose the full column set through agent tools and
   REST.
4. **Surface:** both agent tools and REST endpoints, one domain method per
   operation.
5. **Documents:** receipts/warranties ride the existing WORM photo pipeline
   (new photo purpose `asset_document`); product pages are stored by URL.
   Both become `asset_document` rows.
6. **Research runs in formations, not in the field agent.** The field agent
   keeps its locked-down policy and remains the only database writer.
   Research formations get browser + research tools and no write tools.
7. **The inspector can watch research live** via the AI Elements Web-Preview
   slide-out.
8. **Perplexity Agent API** is an in-scope research provider (OpenAPI spec
   to be supplied by Tim; integration lands behind the same provider seam
   the browser formation uses).

## Migration `0007_live_home_onboarding.sql` (additive only)

0001/0002 are SHA-256-frozen; all DDL goes in 0007. The SQLite mirror in
`schema.py` is updated to match.

- `portfolio`: add `created_by uuid REFERENCES app_user(id)`,
  `client_id uuid` (both nullable — existing rows), partial unique index
  `(organization_id, created_by, client_id) WHERE client_id IS NOT NULL`,
  and `UNIQUE (organization_id, name)`.
- `home`: add nullable `created_by`, `client_id`, same partial replay index.
  Nullable keeps the 96 legacy-synced RandD Tradesmen homes and the importer
  untouched.
- `photo_purpose` enum: add value `asset_document` (PG16-safe pattern —
  `ALTER TYPE … ADD VALUE` cannot run inside the migration's transaction
  block; use a separate transaction or the checked DO-block idiom).
- `asset_document.kind`: `CHECK (kind IN
  ('receipt','warranty','manual','product_page','other'))`.
- No new roles, grants, or policies: `portfolio`, `asset_document`,
  `asset_research_value` are already in the 0003 ownership/RLS/grant loops.
- Superuser not required (unlike 0006): plain DDL owned by the migration
  owner.

## Domain layer (`backend/app/vantage/domain.py`)

All methods replay-safe via `client_id` following the `start_inspection`
pattern; all writes stay inside the tenant transaction so RLS applies.

- `list_portfolios(org)` → active portfolios ordered by name.
- `create_portfolio(org, user, name, client_id)` → conflict on duplicate
  name; replay returns the existing row.
- `create_home(org, user, portfolio_id, name, client_id, unit_code=None,
  formatted_address=None)` → validates the portfolio exists in-tenant
  (composite FK is the backstop); returns the home row ready for
  `start_inspection(home_id, "onboarding")`.
- `create_asset` / `update_asset`: widen payload to the full column set.
  Validation: dates parse ISO-8601, numerics non-negative, `quantity > 0`,
  `tags` is a JSON array of strings. Unknown fields rejected.
- `record_asset_document(org, user, asset_id, kind, object_key=None,
  source_url=None)` → exactly one of `object_key`/`source_url` (XOR
  enforced); asset must be active and in-tenant; `object_key` must reference
  a verified original upload owned by the same org.
- `list_asset_documents(org, asset_id)` for the review UI.

## Agent tools (`inventory_tools.py`, `tool_policy.py`, `field_api.py`)

New tools in the field policy allowlist: `create_portfolio`,
`list_portfolios`, `create_home`, `record_asset_document`,
`list_asset_documents`, `dispatch_research` (see below). Widened schemas for
`create_asset`/`update_asset`. Every mutating tool requires an idempotency
key (client_id), exactly like `create_room` today. `FORBIDDEN_FIELD_TOOLS`
unchanged for the field agent.

## Research formations (`use_agent` / `batch` / `workflow` / `swarm` / `graph`)

`lookup_product_information` becomes `dispatch_research` — the field agent's
handle on a research formation:

- **Formation composition** (assembled in `apps/agent` alongside the
  existing agent assembly): a research agent (or swarm for multi-retailer
  comparison, or graph/workflow for capture → identify → research → price
  pipelines, or batch for researching several assets discovered in one room
  at once) equipped with `browser`, `research`, `exa`/`tavily`, and
  `http_request`.
- **Write isolation:** formation agents receive **no** inventory write
  tools and no tenant database credentials. They return structured results
  `{source_url, fields{name: {value, confidence}}, notes}` to the field
  agent, which is the only writer (`record_research_result`,
  `record_asset_document`) under the tenant transaction. Prompt-injected web
  content can therefore at worst produce a bad *unconfirmed research value*
  (provenance `externally_researched`, `confirmed=false`), never a bad
  write — the same posture `FORBIDDEN_FIELD_TOOLS` already encodes.
- **Provider seam:** `ProductResearchProvider` protocol
  (`lookup(query, context) → structured result`). Implementations:
  1. `BrowserFormationProvider` (V1) — strands browser formation above.
  2. `PerplexityAgentProvider` — Perplexity Agent API:
     `POST /v1/agent` (create agent response, sync or async) +
     `GET /v1/agent/{id}` (retrieve), with built-in `web_search` and
     `fetch_url_content` tools, image attachments, and conversation state.
     OpenAPI spec vendored at `docs/integrations/perplexity-openapi.json`
     (source: https://docs.perplexity.ai/llms.txt → openapi.json).
     Selected by configuration.
- **Concurrency:** formations run async so the walkthrough continues while
  research completes; results attach to the asset when they arrive.

## Live browser in the UI (Web-Preview slide-out)

`WebPreviewBody` is an **iframe** (sandboxed:
`allow-scripts allow-same-origin allow-forms allow-popups
allow-presentation`) whose `src` follows the component's shared URL context;
`WebPreviewUrl` is the address bar and `WebPreviewConsole` renders a `logs`
prop. The browser lives in the UI:

- **The tool houses the browser.** The strands `Browser` tool
  (declared in `backend/requirements.txt`, imported like the other
  `strands_tools` in `backend/app/agent.py`) owns the session outright:
  `LocalChromiumBrowser` launches and holds the Chromium process itself
  (headed by default, persistent-profile support), and the same tool
  abstraction attaches over a CDP websocket to a hosted browser
  (`connect_over_cdp`) when remote execution is wanted. There is exactly
  **one** browser session: the agent acts on it, the agent sees it, and
  the inspector watches it. Web-Preview is the window onto the tool's own
  browser — not a copy, not a screencast.
- When research begins, the Web-Preview panel slides open and the session
  renders **live in the iframe**.
- Agent actions (navigate/click/type/evaluate/`execute_cdp`) run against
  the housed session. Navigation events stream over the existing
  `field_api` websocket and update the iframe URL via the component's
  context (`setUrl`/`onUrlChange`); page console output feeds
  `WebPreviewConsole` logs.
- **The agent sees the page through its vision**, the same way it sees the
  inspector's camera: the established browser-camera bridge pattern
  (`agent.py` — frontend executes, agent perceives frames over the bidi
  stream) extends to the Web-Preview view, so the rendered page is inside
  the agent's visual context while it works.
- For sites that refuse to render in an iframe (`X-Frame-Options`/CSP
  `frame-ancestors`), the same panel falls back to the browser tool's
  `screenshot` frames — the inspector still watches, nothing else changes.
- This is composition of existing pieces (strands `browser` tool ↔
  AI Elements `web-preview.tsx` ↔ existing vision bridge), not new
  infrastructure.

## REST (`backend/app/vantage/api.py`)

- `GET /portfolios`, `POST /portfolios` (201)
- `POST /homes` (201)
- `POST /assets/{asset_id}/documents` (201), `GET /assets/{asset_id}/documents`
- Same conventions as existing endpoints: `Idempotency-Key` header maps to
  `client_id`, `_require_write` role gate on mutations, domain errors map to
  HTTP codes via the existing `_raise`.

## Room-type catalog (`schema.py`)

Append to `ROOM_TYPES`: `Front Yard`, `Back Yard`, `Garage`, `Deck / Patio`,
`Driveway`, `Laundry Room`, `Office`. Per-org seeding is `INSERT OR IGNORE`
with `UNIQUE(org, name)`, so existing orgs pick the new types up on the next
seed pass.

## Asset enrichment loop (`prompts.py`)

For each significant asset the agent:

1. Extracts model/serial from the camera frame
   (`identify_asset_from_view`; provenance `photo_extracted`).
2. **Asks the inspector where the asset was purchased.**
3. Dispatches a research formation (`dispatch_research`) to find the product
   page and extract specs, current price, and replacement cost — visible in
   the Web-Preview slide-out.
4. Writes each returned fact via `record_research_result` with provenance
   `externally_researched`, confidence, and source URL.
5. Attaches the product page as `asset_document(kind='product_page')`.
6. Offers to photograph any receipt or warranty on hand → WORM pipeline →
   `asset_document(kind='receipt'|'warranty', object_key=…)`.
7. **Reads the document in frame as it's captured** (same live vision that
   reads model plates): vendor, purchase date, purchase price, warranty
   provider and expiration. Extracted values land via
   `record_research_result` with provenance `photo_extracted` + confidence,
   and matching asset columns (`purchase_date`, `purchase_price`,
   `warranty_provider`, `warranty_expiration`) are filled through
   `update_asset`.
8. Routes uncertain values through `mark_low_confidence_value` for later
   human confirmation.

## Error handling

- Domain errors keep the existing taxonomy: `not_found`, `conflict`
  (replay mismatch, duplicate portfolio name, duplicate unit_code),
  `validation` (bad dates/numerics/tags, XOR violation), `forbidden`
  (role gate).
- Postgres constraint violations map through the existing
  `map_postgres_error`.
- Formation failures (browser crash, no results, provider timeout) return a
  structured error to the field agent, which continues the walkthrough and
  marks the asset for later research — research is enrichment, never a
  walkthrough blocker.
- The agent surfaces tool errors conversationally and retries with the same
  idempotency key — replays are safe by construction.

## Testing

- Domain: replay-idempotent `create_portfolio`/`create_home`, full metadata
  round-trip, document XOR enforcement, cross-tenant/cross-home rejection,
  room-type seeding picks up new catalog entries for an existing org.
- Contract: 0007 freeze test; frozen 0001/0002 hashes unchanged.
- SQL acceptance: extend the DAH-124 suite with SQLSTATE expectations for
  the new unique indexes and CHECK; RLS suite already covers the tables.
- Research: provider-seam unit tests with a fake provider; formation
  integration test asserting write isolation (formation result containing a
  hostile instruction still only lands as unconfirmed research values);
  event-stream test that research events carry URL updates for Web-Preview.
- End-to-end (pytest): create portfolio → home → onboarding inspection →
  room (Front Yard) → asset with full metadata → dispatched research →
  research values + product_page document → receipt document with extracted
  purchase/warranty fields (`photo_extracted` provenance) →
  `complete_onboarding_assessment` gates satisfied.
- CI: all four existing gates stay green; `postgres-schema` applies
  0001–0007 from zero on PG16.

## Sequencing (single branch, reviewable milestones)

1. Migration 0007 + schema.py mirror + room-type catalog + contract tests.
2. Domain methods + REST endpoints + domain tests.
3. Agent tools + tool policy + enrichment prompt.
4. Research formation + provider seam + `dispatch_research` + write-isolation
   tests.
5. Web-Preview event stream + frontend slide-out.
6. Perplexity provider (lands when Tim supplies the OpenAPI spec; seam and
   config switch ship in milestone 4).

