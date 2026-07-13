# Live Home Onboarding Implementation Plan

**Status:** Implemented

## Objective

Let the authenticated live agent create and enrich this hierarchy during a
video walkthrough:

```text
Organization → Portfolio → Home → Room/outdoor area → Asset
```

Use the repository, RLS, Strands browser and formations, AgentCore live view,
Perplexity Agents API, Smarty MCP server, verified-original media pipeline, and
AI Elements components already present. Do not create parallel abstractions for
capabilities those systems already provide.

## Binding implementation choices

- One AgentCore Chromium session is owned and driven by the Strands browser
  tool.
- AI Elements `WebPreviewBody` receives only that session's native signed
  live-view URL.
- AgentCore's native take/release control methods provide HITL.
- Browser screenshots and the existing `image_reader` provide agent vision.
- Perplexity is a direct Strands tool over the official SDK.
- Smarty is a native MCP connection for Strands and an optional native MCP tool
  in Perplexity requests.
- Native `use_agent`, `batch`, `workflow`, `swarm`, and `graph` remain available
  directly. There is no custom dispatcher or research-provider interface.
- The field-tool restriction layer is removed; the agent receives its runtime,
  discovery, browser, formation, Google, memory, and onboarding tools.
- Session identity, not model input, supplies organization and user IDs.

## Completed work

### 1. Additive schema and catalog

- [x] Add migration `0007_live_home_onboarding.sql`.
- [x] Add nullable `created_by` and `client_id` to portfolio and home.
- [x] Add replay indexes and organization-scoped portfolio-name uniqueness.
- [x] Add `asset_document` photo purpose.
- [x] Add document kind, exactly-one-reference, and duplicate-link constraints.
- [x] Extend the fixed indoor/outdoor room catalog.
- [x] Mirror the PostgreSQL contract in SQLite without changing frozen
  migrations.
- [x] Add PostgreSQL acceptance coverage and run it after migrations `0001–0007`.

### 2. Repository parity

- [x] Implement `list_portfolios` and replay-safe `create_portfolio`.
- [x] Widen `create_home` while retaining legacy importer/bootstrap calls.
- [x] Expose every supported asset metadata field on create and update.
- [x] Share date, money, quantity, tag, and research-value normalization.
- [x] Record/list verified-photo or source-URL asset documents.
- [x] Record/list provenance-bearing JSON research values.
- [x] Keep SQLite and PostgreSQL method signatures aligned.

### 3. REST surface

- [x] Add `GET|POST /api/portfolios`.
- [x] Add `POST /api/homes`.
- [x] Widen asset create/update payloads to the existing full schema.
- [x] Add `GET|POST /api/assets/{asset_id}/documents`.
- [x] Add `GET|POST /api/assets/{asset_id}/research-values`.
- [x] Derive tenant/user identity from authentication only.
- [x] Apply write-role checks and owner home-grant checks.
- [x] Resolve asset and read its child collection in the same read transaction.

### 4. Session-bound agent tools

- [x] Build inventory tools per WebSocket session from the verified
  `TenantContext`.
- [x] Register portfolio, home, inspection, room, asset, document, and research
  operations directly over the existing transaction adapter.
- [x] Keep replay keys explicit on creation operations.
- [x] Remove `tool_policy.py` and the privileged tool split.
- [x] Register `editor`, `shell`, `load_tool`, discovery, MCP, HTTP,
  environment, image reader, formations, Google, Slack, delivery, and memory
  tools for the live agent.
- [x] Persist all requested Strands extras in `requirements.txt`.
- [x] Confirm runtime discovery returns 70 loadable tools and zero unavailable.

### 5. AgentCore browser and Web Preview HITL

- [x] Use installed `AgentCoreBrowser` as the automation implementation.
- [x] Retain its exact native `BrowserClient` per Strands browser session.
- [x] Generate the native AgentCore live-view URL on initialization.
- [x] Publish browser session/current-page/control events through the existing
  WebSocket.
- [x] Render only the live-view URL in the existing AI Elements iframe.
- [x] Display the researched page URL separately in the read-only address bar.
- [x] Auto-open the agent panel when a browser session appears.
- [x] Wire native take-control, release-control, and live-view refresh actions.
- [x] Refresh the signed live-view URL before its five-minute expiry.
- [x] Prevent browser control messages from reaching the model.
- [x] Close the browser deterministically and prevent a close action from
  recreating stale UI session state.

### 6. Perplexity and Smarty

- [x] Add a direct `perplexity_agent` Strands tool using the official
  `perplexityai` SDK.
- [x] Support presets, models/fallback lists, images, continuation, structured
  output, max steps, web search, URL fetching, citations, usage, and cost.
- [x] Add a native streamable-HTTP Smarty `MCPClient` with direct tool
  discovery/registration.
- [x] Allow Perplexity to use Smarty as a native remote MCP tool.
- [x] Read credentials only from server environment variables.
- [x] Redact configured credential values from normalized Perplexity output.
- [x] Continue the live agent without Smarty if it is unconfigured or
  temporarily unavailable.
- [x] Document only blank environment-variable slots; do not commit secrets.

### 7. Asset enrichment instructions

- [x] Direct the agent to ask purchase source/date and request available
  receipt, warranty, or manual evidence.
- [x] Use live vision for labels and document fields.
- [x] Store photo-extracted and externally researched provenance explicitly.
- [x] Preserve exact source URLs and confidence.
- [x] Keep researched values unconfirmed until human confirmation.
- [x] Use the browser, Perplexity, Smarty, or native formations directly based
  on the task.

## Verification record

- [x] Backend: 88 tests passed.
- [x] Python package dependencies: `pip check` clean.
- [x] Runtime tool discovery: 70 loadable, zero unavailable.
- [x] Frontend: TypeScript and Vite production build passed.
- [x] SQL: all seven migrations parsed with pglast.
- [x] PostgreSQL 16: fresh migrations `0001–0007` passed.
- [x] PostgreSQL 16: DAH-124, DAH-126, DAH-131, and live-home onboarding
  acceptance suites passed in CI order.
- [x] Existing RandD Tradesmen data confirmed intact: 96 properties, 65 tasks,
  51 inspection reports, and 11 clusters.
- [x] Independent code review findings resolved: owner grant enforcement,
  expiring live-view refresh, close-event ordering, Smarty availability, and
  local acceptance-runner parity.
- [x] Configured custom AgentCore Browser ID in its own `us-east-1` region.
- [x] Live AgentCore smoke: resource READY, session start/stop, signed CDP and
  live-view endpoints, and native take/release control passed.
- [x] Live Smarty MCP smoke: authenticated and discovered 20 tools.

## Deployment configuration

The implementation is active when the existing runtime credentials are
configured. New server-side variables are:

```dotenv
AGENTCORE_BROWSER_REGION=us-east-1
AGENTCORE_BROWSER_IDENTIFIER=browser_use_tool_ckljx-o9oT8gdjLQ
PERPLEXITY_API_KEY=
SMARTY_MCP_URL=https://mcp.api.smarty.com/
SMARTY_AUTH_ID=
SMARTY_AUTH_TOKEN=
```

The configured AgentCore value is the custom browser ID accepted by
`BrowserClient.start`, not the browser resource ARN or display name. The
browser-specific region prevents the application's other AWS region settings
from pointing this session at the wrong AgentCore endpoint. Secrets belong in
the ignored `backend/.env` or the deployment secret store, never in source
control.
