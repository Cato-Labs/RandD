# Plan — Tenant "Connect Google" (zero Google Cloud for tenants)

## Goal

Let each tenant connect a Google account for the agent's Google Workspace tools
(Gmail send, Sheets import, Docs reports, Calendar, Drive) by clicking **one
button and approving Google's consent screen** — and nothing else. No tenant or
operator ever opens Google Cloud Console, creates an OAuth client, or manages an
API key.

## Hard constraint (from the user)

> "I will not look at, or even consider a plan that involves a user having to do
> any diving into Google Cloud."

This is satisfied by the **standard SaaS OAuth model**: the *platform* owns one
Google Cloud project + one OAuth "Web application" client (a one-time setup by
the platform owner, done once, already implicitly in place because Gmail works
today). Tenants only ever hit Google's hosted consent screen.

## Decisions (resolved)

1. **Identity model: one Google account per tenant.** Mirrors the existing Slack
   per-workspace bot-token model and covers every PRD Google use case (org-level
   Sheets/Docs/Calendar/Gmail). Per-user Google linking is explicitly out of scope.
2. **Google Cloud project/OAuth client is platform-owned and singular.** One
   "Web application" OAuth client, redirect URI registered once by the platform
   owner against the existing public origin `https://44-193-208-77.sslip.io`
   (`backend/app/main.py:44`) plus `http://localhost:5173` for dev. Client ID +
   secret live in the platform `.env` (`GOOGLE_OAUTH_WEB_CLIENT_ID`,
   `GOOGLE_OAUTH_WEB_CLIENT_SECRET`) — never per-tenant.
3. **Google Maps is unaffected.** Maps is a platform server-side API key
   (`GOOGLE_MAPS_API_KEY`, used via `http_request` per `backend/app/prompts.py:19`).
   It is not OAuth, not tenant-facing, and stays exactly as-is. Out of scope.
4. **Token storage: encrypted per tenant, reusing existing crypto.** Store the
   OAuth token JSON (incl. refresh token) with
   `strqc_shared.crypto.encrypt_secret(token_json, aad=f"google:{tenant_id}")`.
5. **Token injection: in-memory, tenant-aware, per session.** Do NOT mutate the
   shared process `GOOGLE_OAUTH_CREDENTIALS` env var (races across concurrent
   tenant sessions). Build `google.oauth2.credentials.Credentials` in memory from
   the decrypted token, scoped to the session's `tenant_id`.
 6. **Minimal scopes**, not the strands `DEFAULT_SCOPES` full-access set:
   `openid`, `userinfo.email`, `gmail.send`, `gmail.readonly` (to read inbound
   into the connected mailbox), `spreadsheets`, `documents`, `calendar.events`,
   `drive.file`. (Revisit only if a tool needs more.)
 7. **Multiple org email addresses = aliases of the one connected mailbox
    (Option A).** A tenant can have many send/receive addresses — including
    person-named ones like `maribel@randd.com`, `dan@randd.com`, plus role
    addresses like `reports@`, `noreply@` — by having their Google Workspace
    admin add each as an **alternate address (alias)** of the single connected
    mailbox (e.g. `ops@randd.com`). The agent then:
    - **sends** from any alias by setting the `From`/`sender` (the existing
      `gmail_send` `sender` param already supports this — verified in
      `strands_google/gmail_helpers.py:64,68`), and
    - **receives** mail addressed to any of those aliases, because aliases
      deliver into the one connected mailbox that the agent reads (`userId:"me"`).
    Alias creation is a **tenant-side Workspace admin setting**; the platform
    cannot and does not provision aliases. No schema change beyond
    one-token-per-tenant. A genuinely *separate* mailbox (its own login, not an
    alias) is the only thing that would need a second OAuth connection — that is
    **Option B, explicitly deferred** (see Out of scope).

## Ground truth (verified in-repo)

- Auth is a signed cookie carrying `{user_id, tenant_id, is_platform_admin}`
  (`backend/app/auth.py`); `/api/*` + `/ws` are gated on it.
- `tenant_id` already flows into the agent: WS token validated at
  `backend/app/main.py:487`, then `create_agent(..., tenant_id=tenant_id)` at
  `main.py:505` and `invocation_state={"tenant_id": tenant_id}` at `main.py:509`.
- Agent Google tools today read global env vars only: `use_google` resolves
  `GOOGLE_APPLICATION_CREDENTIALS` → `GOOGLE_OAUTH_CREDENTIALS` →
  `GOOGLE_API_KEY` from `os.environ` (`use_google.py:140-196`). This is the
  single-tenant assumption to replace.
- Envelope crypto exists and is tested:
  `packages/shared/src/strqc_shared/crypto.py`
  (`encrypt_secret`/`decrypt_secret`, AES-256-GCM, AAD).
- Slack already demonstrates the "one connected external account per workspace +
  refresh" pattern (`backend/app/slack_token.py`).
- Multitenancy migration ledger runner: `backend/app/migrate_runtime.py`; tenant
  schema in `sql/0003_multitenancy.sql`. New migrations must go through the
  ledger runner (never bare-run against the live DB).

## Tenant-facing experience (the entire UX)

1. Tenant opens Settings → sees "Google: Not connected" + **Connect Google**.
2. Click → redirected to Google's consent screen (platform's app name shown).
3. Approve → redirected back → "Connected as ops@theirdomain.com".
4. Done. Agent Google tools now act as that account for that tenant.
5. A **Disconnect** button deletes the stored token.

No Cloud Console, no keys, no JSON downloads for the tenant — ever.

## Implementation tasks (ordered)

### 1. Migration — encrypted per-tenant Google token
- Add `sql/0004_tenant_google_credential.sql` (additive; ledger-guarded):
  ```sql
  CREATE TABLE IF NOT EXISTS tenant_google_credential (
    tenant_id            INTEGER PRIMARY KEY
                         REFERENCES tenant(tenant_id) ON DELETE CASCADE,
    token_ciphertext     TEXT NOT NULL,
    google_account_email TEXT,
    scopes               TEXT,
    connected_by_user_id INTEGER REFERENCES app_user(user_id),
    connected_at         TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now'))
  );
  ```
- Register it in the ledger runner (`backend/app/migrate_runtime.py`) alongside
  `0003`. Prove on a **copy** of `str_qc.sqlite` before touching live.

### 2. Config / secrets (platform-level, one-time)
- Add to `.env` / `.env.example`: `GOOGLE_OAUTH_WEB_CLIENT_ID`,
  `GOOGLE_OAUTH_WEB_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_BASE`
  (defaults to the request origin; overridable). Never commit values.
- One-time platform-owner action (documented, not tenant-facing): in the
  platform's existing Google Cloud project, create/confirm a **Web application**
  OAuth client and register redirect `…/api/google/callback` for both prod and
  dev origins, and publish the consent screen. This is the *only* Google Cloud
  step and it is the platform owner's, done once.

### 3. Backend — `/api/google/*` endpoints (all `Depends(current_user)`, tenant-scoped)
New module `backend/app/google_connect.py` + routes in `main.py`:
- `GET /api/google/status` → `{connected: bool, email, scopes}` for the tenant.
- `GET /api/google/connect` → build Google auth URL (`access_type=offline`,
  `prompt=consent`, minimal scopes, `state` = signed JWT binding
  `{tenant_id, user_id, nonce}` via existing `auth` secret). Return `{url}`.
- `GET /api/google/callback?code&state` → verify `state` (reject cross-tenant),
  exchange code for tokens, fetch `userinfo` email, `encrypt_secret(token_json,
  aad="google:<tenant_id>")`, upsert row. Redirect back to the Settings screen.
- `DELETE /api/google/connect` → delete the tenant's row (disconnect).
- Helper `load_google_credentials(tenant_id) -> Credentials | None`: read + decrypt,
  build `Credentials`, refresh if expired using platform client id/secret, and on
  refresh re-`encrypt_secret` + update row (mirrors `slack_token.py` refresh, but
  writes to the DB, not `.env`).

### 4. Agent — tenant-aware Google tools (replace global-env reliance)
- Add `backend/app/google_tools.py` wrapping the Google surface the agent needs
  so each call resolves creds from the session tenant:
  - Read `tenant_id` from `ctx.agent.state["tenant_id"]` (already set at
    `agent.py:190` / `main.py:509`).
  - `creds = load_google_credentials(tenant_id)`; if `None`, return a clear
    "Google not connected for this tenant — connect it in Settings" tool result
    (no crash, no fallback to another tenant's token).
  - Provide tenant-scoped equivalents of the Google actions currently exposed
    (`use_google`, `gmail_send`, `gmail_reply`, `gmail_send_with_attachments`):
    build the Google API client with the in-memory `creds` rather than env files.
- In `backend/app/agent.py`: swap the global `use_google`/`gmail_*` tool entries
  (lines 8-10, 94-98) for the tenant-aware wrappers. Keep tool *names/specs*
  stable so the prompt (`prompts.py`) and model behavior don't change.
- Do NOT touch Maps guidance in `prompts.py:19` (API key path stays).

### 5. Frontend — Settings "Connect Google" panel
- Add a Google section to the existing settings/onboarding surface (reuse the
  already-vendored shadcn primitives; no new libs/router):
  - On mount, `GET /api/google/status` (`credentials:"include"`).
  - "Connect Google" → `GET /api/google/connect` then
    `window.location = url`.
  - After callback redirect, re-fetch status; show "Connected as <email>" +
    **Disconnect** (`DELETE /api/google/connect`).
- All fetches include `credentials:"include"` (matches existing auth fetches).

## Failure modes to handle

- **Tenant not connected:** Google tools return a friendly "connect in Settings"
  result; agent surfaces it, no exception, no cross-tenant leakage.
- **Refresh token missing/expired-revoked:** treat as disconnected; prompt
  reconnect. (Forcing `prompt=consent` + `access_type=offline` ensures a refresh
  token is issued on first connect.)
- **`state` mismatch / cross-tenant callback:** reject 400; never write a token
  to a tenant other than the one in the signed `state`.
- **Concurrent sessions, different tenants:** guaranteed isolated because creds
  are built in memory per call from `state["tenant_id"]` — no shared env var.
- **Missing `STRQC_MASTER_KEY`:** `encrypt_secret` already raises; connect fails
  loudly rather than storing plaintext.

## Regression contract (must still pass)

- Existing live voice/text `/ws` session, inspection export, Slack delivery,
  property/inspector endpoints, deploy flow — all unchanged.
- Existing 59 Python tests stay green.
- Never change existing `/api/*` response shapes; new endpoints are additive.
- Never widen CORS; never log/commit secrets, tokens, door codes, wifi.

## Validation

- Migration proven on a copy: table created, ledger recorded, live counts intact.
- New backend tests: state signing/verification (reject cross-tenant + tampered);
  encrypt→store→decrypt round-trip with tenant AAD; `load_google_credentials`
  returns `None` when unconnected; refresh path updates the stored ciphertext.
- Manual E2E on dev origin: Connect → consent → "Connected as …"; run a Sheets
  read and a Gmail send through the agent as that tenant; Disconnect clears it.
- Two-tenant check: tenant A connected, tenant B not → B's Google tool calls get
  the "not connected" result, never A's account.
- Alias send/receive check: with `ops@` connected and `maribel@`/`reports@` set
  as aliases in the tenant's Workspace, the agent sends from each alias and reads
  a reply addressed to an alias out of the one connected mailbox.

## Out of scope

- Google Maps changes (platform API key, already working).
- **Option B — multiple *separate* connected Google accounts per tenant** (a
  second distinct mailbox with its own login, not an alias). Deferred; would
  require many-tokens-per-tenant schema + account-selection logic. Person-named
  *aliases* of the one connected mailbox are IN scope (Decision 7) and cover the
  common "multiple emails per org" need without this.
- Per-end-user (per-inspector) Google linking (Option C).
- Domain-wide delegation / send-on-behalf for arbitrary domain users.
- Broad `DEFAULT_SCOPES` full-access grant.
- Any tenant/operator interaction with Google Cloud Console (aliases are a
  tenant Workspace-admin setting, done in Google Admin, not via this platform).

## Notes for the implementer

- This agent (plan mode) made no source changes. Switch to an
  implementation-capable agent to execute.
- Do all work on `feat/multitenancy-and-auth` (or a branch off it); do not touch
  `main`, `apps/*`, or `packages/*` except keeping their tests green.
- Route new migrations through `backend/app/migrate_runtime.py`; back up the live
  DB before any migrate.

## Resolved decisions (from planning conversation)

- **Platform-owner one-time Google Cloud setup: CONFIRMED acceptable.** The
  platform owner creates/confirms one Web OAuth client + redirect URIs + consent
  screen, once, and stores client id/secret in the platform `.env`. Tenants never
  touch Google Cloud.
- **Each tenant connects THEIR OWN Google account: CONFIRMED.** The agent sends
  as / reads that tenant's connected mailbox; multitenancy isolation holds via
  `tenant_id`.
- **"Multiple emails per organization" = aliases of the one connected mailbox
  (Option A): CONFIRMED.** Person-named aliases (`maribel@`, `dan@`) and role
  aliases (`reports@`, `noreply@`) are alternate addresses of the single
  connected mailbox; the tenant's Workspace admin creates them. Both send and
  receive work through the one connection. Separate distinct mailboxes (Option B)
  are deferred.

No open questions block implementation. Switch to an implementation-capable
agent to execute.
