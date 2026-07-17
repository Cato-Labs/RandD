# Live Home Onboarding

**Date:** 2026-07-12

**Status:** Implemented

**Owner:** Tim Hunter

**Relates to:** DAH-112 (PostgreSQL runtime + FORCE RLS, merged in PR #7)

## Goal

During a live video walkthrough, Vantage can create and persist this hierarchy
inside the authenticated tenant:

```text
Organization → Portfolio → Home → Room or outdoor area → Asset
                                                    ├─ metadata
                                                    ├─ documents
                                                    └─ research values
```

The implementation reuses the existing repositories, transaction-scoped RLS,
Strands tools, AgentCore Browser, Perplexity Agents API, Smarty MCP server, and
AI Elements Web Preview. It does not add a second browser, a research-provider
abstraction, a custom dispatcher, or a screenshot-streaming system.

## Data model and migration

Migration `0007_live_home_onboarding.sql` is additive. The SHA-frozen foundation
migrations remain unchanged.

- `portfolio` and `home` receive nullable `created_by` and `client_id` columns.
  Existing imported homes remain valid, while new agent/app writes get replay
  protection through partial unique indexes.
- Portfolio names are unique inside an organization.
- `photo_purpose` gains `asset_document` so receipts and warranties use the
  existing verified-original/WORM media pipeline.
- `asset_document.kind` is limited to `receipt`, `warranty`, `manual`,
  `product_page`, or `other`.
- An asset document must contain exactly one reference: an existing verified
  original object or an HTTP(S) source URL.
- Duplicate asset-document references are rejected.
- Existing tenant tables retain their ownership, grants, composite foreign
  keys, and FORCE RLS policies.

The fixed room catalog includes indoor and outdoor areas such as Front Yard,
Back Yard, Garage, Deck / Patio, Driveway, Laundry Room, Office, Attic,
Storage, Deck, Porch, Boat Deck, Living Room, Hallway, Family Room, Sun Room,
Library, Theater, Pantry, and Walk-in Closet. Agents select from this catalog;
they do not create arbitrary room types.

## Repository and API surface

SQLite and PostgreSQL implement the same operations:

- `list_portfolios`
- replay-safe `create_portfolio`
- replay-safe `create_home`
- full-metadata `create_asset` and `update_asset`
- `record_asset_document` and `list_asset_documents`
- `record_asset_research_value` and `list_asset_research_values`

Asset normalization is shared across both repositories. Dates must be ISO
dates; money is normalized to non-negative two-decimal values; quantity must
be a positive integer; tags are normalized to a unique list of strings.
Research values preserve arbitrary JSON plus provenance, source reference,
confidence from zero to one, and human-confirmation state.

The REST API exposes the same domain methods:

- `GET /api/portfolios`
- `POST /api/portfolios`
- `POST /api/homes`
- full metadata on `POST /api/rooms/{room_id}/assets` and
  `PATCH /api/assets/{asset_id}`
- `GET|POST /api/assets/{asset_id}/documents`
- `GET|POST /api/assets/{asset_id}/research-values`

Organization and user identity always come from the verified session. Request
payloads cannot select a different tenant. Mutations retain the existing role
gate and database transaction boundary.

## Agent tools

Each live WebSocket session receives inventory tools bound to its verified
`TenantContext`. The agent can list/create portfolios, create homes, start
onboarding inspections, list/create/update rooms, create/update/move assets,
and record/list documents and research values. Every repository call runs
inside the existing tenant transaction adapter.

The former field-tool policy and privileged split are removed. The live agent
always receives its existing toolset, including `editor`, `shell`, `load_tool`,
`list_library_tools`, `mcp_client`, `http_request`, `environment`, Google tools,
memory tools, and the native `use_agent`, `batch`, `workflow`, `swarm`, and
`graph` formations. Tools not registered initially remain discoverable through
the existing `load_tool` path.

## One browser session, native HITL

Production browsing uses the installed Strands `AgentCoreBrowser`. It owns the
Playwright/CDP connection and the AgentCore `BrowserClient`; browser actions are
the stock Strands actions. `LiveViewAgentCoreBrowser` only retains the native
client for the session and exposes AgentCore's existing live-view/control
lifecycle.

```text
Strands browser tool ──acts through CDP──> AgentCore Chromium session
                                             │
                                             ├─ screenshots → agent vision
                                             │
                                             └─ signed live-view URL
                                                    │
                                                    v
                                      AI Elements WebPreviewBody iframe
```

The researched website URL is never placed in the iframe. The iframe receives
only `BrowserClient.generate_live_view_url()` for the exact browser instance
the agent is using. `currentPageUrl` is display-only in the Web Preview address
field.

When the agent initializes a browser session, the backend publishes a
`browser_session` event and the existing agent panel opens automatically.
The inspector watches the headful browser live and can invoke AgentCore's
native `take_control()` and `release_control()` through the panel. These control
messages are consumed by the WebSocket input adapter and are not sent to the
model. The agent continues to see pages through the browser tool's native
screenshot output and the already-registered `image_reader` tool. There is no
second Chromium instance, direct website iframe, or custom frame bridge.

AgentCore live-view URLs are refreshed by the frontend before their five-minute
expiry while the browser session remains open.

The browser and any AgentCore resources close in the WebSocket `finally` path.

## Product and address research

`perplexity_agent` is a direct Strands tool over the official Perplexity Python
SDK. It exposes the Agents API capabilities needed here: presets or models,
model fallback lists, images, continuation IDs, structured output, step limits,
`web_search`, and `fetch_url`. Its normalized result retains the answer,
structured output, citations, search/fetch results, token usage, and cost.

The agent may instead browse directly or use native Strands formations. There
is no `ProductResearchProvider`, `dispatch_research`, or duplicate orchestration
layer.

Smarty is integrated two native ways:

1. A Strands `MCPClient` connects to Smarty's streamable-HTTP MCP server,
   discovers tools with `tools/list`, and registers those tools directly on the
   live session with a `smarty_` prefix.
2. Perplexity requests can include the same Smarty server as a native remote
   MCP tool when `use_smarty` is requested.

Smarty credentials are read only from server environment variables and are
never accepted as model arguments or written to source. Returned Perplexity
data is scrubbed defensively so credentials cannot be echoed into the
conversation. If Smarty is not configured or temporarily unavailable, the live
agent continues with its browser, Perplexity, and other tools.

## Enrichment behavior

For each significant asset, the system prompt directs the agent to:

1. observe and store available model, serial, condition, and other metadata;
2. ask where and when it was purchased and whether a receipt, warranty, or
   manual is available;
3. read labels/documents through live vision and store extracted facts with
   `photo_extracted` provenance and confidence;
4. use the AgentCore browser, Perplexity, Smarty, or native formations as the
   task requires;
5. save online product pages/manuals by source URL and captured documents
   through the existing verified-original pipeline;
6. store sourced facts as `externally_researched`, with exact URL, confidence,
   and `confirmed=false` until a person confirms them; and
7. update canonical asset fields only when evidence is adequate rather than
   guessing.

## Verification

- Python unit/domain/integration suite covers the repositories, REST surface,
  session-bound tools, unrestricted agent tool registration, native browser
  lifecycle/HITL events, Perplexity request/response behavior, and Smarty MCP
  configuration.
- The frontend production TypeScript/Vite build validates the Web Preview and
  control UI.
- CI applies migrations `0001` through `0007` to PostgreSQL 16 and runs the
  existing DAH-124, DAH-126, and DAH-131 suites plus the live-home onboarding
  acceptance suite.
- The onboarding SQL suite exercises portfolio/home replay constraints, full
  hierarchy insertion, asset metadata, document XOR/kind/uniqueness rules,
  research provenance, and the new photo purpose.
