# Shared Packages & Security Posture Audit

**Scope:** `packages/shared`, `packages/db`, and repo-wide security posture.
**Date:** 2026-07-06
**Auditor:** Kilo
**Status:** READ-ONLY audit — no code files modified.

---

## Executive Summary

The shared foundations are **partially in place but not yet ship-ready from a security standpoint**. The cryptography layer is sound, the repository layer is clean of SQL injection, and the workspace layout is reasonable. However, several critical security requirements from `AGENTS.md` and `TASKS.md` M1/M8 are **unimplemented or incomplete**:

- **CRITICAL:** The local `.env` file contains real, high-value secrets (Google API key, OpenAI API key, AWS credentials, Slack tokens, master encryption key). The file is gitignored and not in tracked history, but it lives on disk in the working tree and is a rotation/secret-management incident waiting to happen.
- **HIGH:** Pydantic settings load secrets as plain `str` rather than `SecretStr`, increasing the risk of accidental logging/exposure in tracebacks and tool dumps.
- **HIGH:** `STRQC_SESSION_SECRET` defaults to an empty string. If this is used to sign session cookies/tokens before a real value is set, sessions become forgeable.
- **MEDIUM:** Addendum-1 and Addendum-2 schema fields are missing from the live Phase-1 schema (`Report.delivery_*`, `Photo.include_in_report`, Escapia native IDs, `SyncCursor`, `HousekeepingStatusMap`).
- **MEDIUM:** PII (stakeholder email/phone, property addresses, future guest data) is stored in plaintext columns with no encryption or tokenization.
- **MEDIUM:** There is no observability, tracing, or audit logging in `packages/shared` or `packages/db`.
- **LOW/MEDIUM:** Python dependencies are loosely pinned (`>=`) with no lock file; CI has a cache-path mismatch for the web job.

The crypto implementation itself is the strongest part of the audit: AES-256-GCM with random 12-byte nonces, versioned ciphertext, AAD binding, and a masking helper that does not leak length.

---

## Workspace / Monorepo Layout Status (M0.1)

| Requirement | Status | Evidence / Notes |
|---|---|---|
| `apps/agent` (Python BIDI agent) | ✅ | `apps/agent/pyproject.toml` |
| `apps/api` (Python service) | ✅ | `apps/api/pyproject.toml` |
| `apps/web` (Next.js PWA) | ✅ | `apps/web/package.json` |
| `packages/db` (schema + migrations) | ✅ | `packages/db/` versioned SQL + `migrate.py` |
| `packages/shared` (config + crypto) | ✅ | `packages/shared/src/strqc_shared/` |

The layout matches `README.md` §Workspace layout and the `M0.1` requirement. Boundaries are clean: `packages/db` has no external runtime dependencies, and `packages/shared` only depends on `pydantic`, `pydantic-settings`, and `cryptography`.

One inconsistency: the repo also contains a `backend/` and `frontend/` directory alongside the newer `apps/` layout. The `Makefile` and root `package.json` currently point at the newer `apps/` packages, but `README.md` still documents `backend/` and `frontend/` quickstart. This duality is a maintenance risk and should be consolidated before v1.

---

## Strands SDK Pin (M0.2)

| Aspect | Status | Evidence |
|---|---|---|
| Vendored/editable SDK | ✅ | `Makefile:14`, `CI:20`, `apps/agent/pyproject.toml:11` reference `pip install -e harness-sdk/strands-py` |
| Published SDK pin | ✅ | `backend/requirements.txt:3` pins `strands-agents>=1.45.0,<2.0.0` |
| Dependency consistency | ⚠️ | Workspace uses editable `harness-sdk/`, while backend pins PyPI `strands-agents`. These may drift. |

The `harness-sdk/` directory is gitignored (`TASKS.md` note). The workspace build is documented but there is no single lock file or constraint file that pins the exact Strands SDK commit or published version across both paths. Consider adding a `requirements.lock` or a constraint file and recording the vendored SDK commit hash.

---

## Secrets Management Audit (M0.3, M1.6, M8.4)

### `.env` file (local, gitignored)

**Status:** Present in working tree with real secret values. **Not tracked by git** (verified with `git ls-files .env` and `git log --all --oneline -- .env`; no history found).

Keys present in `.env` (values redacted):

- `STRQC_MASTER_KEY` — real 32-byte base64 envelope-encryption key.
- `GOOGLE_API_KEY`
- `GEMINI_LIVE_MODEL`
- `STRQC_GEMINI_THINKING_LEVEL`
- `OPENAI_API_KEY`
- `OPENAI_ORGANIZATION`
- `OPENAI_PROJECT`
- `OPENAI_MODEL`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `STRQC_NOVA_MODEL_ID`
- `AWS_BEARER_TOKEN_BEDROCK`
- `BEDROCK_KB_ID`
- `BEDROCK_KB_DATA_SOURCE_ID`
- `BEDROCK_KB_TYPE`
- `BEDROCK_KB_S3_BUCKET`
- `BEDROCK_KB_S3_PREFIX`
- `SLACK_CLIENT_ID`
- `SLACK_CLIENT_SECRET`
- `SLACK_BOT_REFRESH_TOKEN`
- `SLACK_BOT_TOKEN`
- `SLACK_DEFAULT_CHANNEL_ID`
- `SLACK_APP_TOKEN`
- `ESCAPIA_BASE_URL`
- `ESCAPIA_CLIENT_ID` (empty)
- `ESCAPIA_CLIENT_SECRET` (empty)
- `ESCAPIA_PMC_ID` (empty)
- `ESCAPIA_API_VERSION`
- `ESCAPIA_END_SYSTEM`
- `GOOGLE_APPLICATION_CREDENTIALS` (points to a service-account JSON file on disk)
- `GOOGLE_OAUTH_CLIENT`
- `GOOGLE_OAUTH_TOKEN`
- `GOOGLE_OAUTH_CREDENTIALS`
- `STRQC_API_HOST`
- `STRQC_API_PORT`
- `STRQC_SESSION_SECRET` (empty)

**Risk:** The `.env` file contains live credentials for Google, OpenAI, AWS, Slack, and the master encryption key. Even though it is not committed, any of the following would expose it: container image layers, IDE/cloud sync, backup tooling, `cat`/`grep` accidents, copy-to-clipboard, or shell history. Additionally, `backend/app/slack_token.py` rewrites this file in place when refreshing Slack tokens, which increases the chance of misparses or race conditions and keeps the refresh token in a file rather than a secret manager.

**Recommendation:**
1. Rotate every secret listed above immediately (they are currently live in the local workspace and possibly elsewhere).
2. Move all secrets to a secret manager / runtime env injection (e.g., 1Password secrets, Doppler, AWS Secrets Manager, GitHub Actions secrets) for any deployment.
3. Replace `.env` rewrite logic in `slack_token.py` with secret-manager updates or, at minimum, write to a separate `.env.local` that is also gitignored.
4. Generate a new `STRQC_MASTER_KEY` and re-encrypt any existing ciphertext if the DB has been used with the current key.

### `.gitignore` and tracked-file scan

| File pattern | Ignored? | Notes |
|---|---|---|
| `.env` | ✅ | `.gitignore:5` |
| `*.env` | ✅ | `.gitignore:6`, with exception `!.env.example` |
| `coral-pipe-*.json` | ✅ | `.gitignore:8` |
| `gmail_credentials.json` | ✅ | `.gitignore:9` |
| `gmail_token.json` | ✅ | `.gitignore:10` |
| `*.sqlite` / `*.sqlite3` / `*.db` | ✅ | `.gitignore:13-15` |
| `photostore/` | ✅ | `.gitignore:16` |

**Tracked-file secret scan:**
- Ran `git grep -l "AIzaSy\|sk-proj-\|xoxe\|xapp-\|AKIA[0-9A-Z]{16}"`.
- Only tracked matches: `backend/app/slack_report.py` and `backend/app/slack_token.py`, which contain only comment strings describing token formats, not actual secret values.
- No private keys (`BEGIN RSA/OPENSSH/PGP PRIVATE`) found in tracked files.
- No hardcoded API keys found in `packages/shared`, `packages/db`, or their tests.

### Crypto / envelope encryption (M1.6)

File: `packages/shared/src/strqc_shared/crypto.py`

Implemented scheme: AES-256-GCM with a 32-byte base64 master key from `STRQC_MASTER_KEY`.

| Control | Status | Evidence |
|---|---|---|
| AES-256-GCM | ✅ | `crypto.py:16`, `AESGCM(key).encrypt(...)` |
| Random 12-byte nonce | ✅ | `crypto.py:43`, `os.urandom(12)` |
| Versioned ciphertext | ✅ | `crypto.py:18`, `v1.<nonce>.<ct>` format |
| AAD binding | ✅ | `crypto.py:44`, `aad` parameter bound to context |
| Key validation | ✅ | Length and base64 checks in `_load_key` (`crypto.py:25-37`) |
| No plaintext logging | ✅ | `mask_secret()` helper exists; no raw logging in this module |

**Cryptographic observations:**
- The version prefix is hardcoded as `"v1"`; rotation strategy is not documented. Add a migration path if the key or algorithm ever changes.
- `aad` is optional and defaults to `""`. In production, every secret should be bound to its context (e.g., unit code) so a ciphertext cannot be swapped across properties. The current code allows empty AAD, which is a footgun; consider enforcing non-empty AAD in repository-level helpers.

**Tests:** `packages/shared/tests/test_crypto.py` covers round-trip, wrong AAD, wrong key, missing key, bad key length, and masking. All 6 tests passed.

### Config validation (pydantic-settings)

File: `packages/shared/src/strqc_shared/config.py`

| Control | Status | Evidence |
|---|---|---|
| Uses pydantic-settings | ✅ | `config.py:7` |
| Loads `.env` | ✅ | `SettingsConfigDict(env_file=".env")` (`config.py:13`) |
| Extra fields ignored | ✅ | `extra="ignore"` |
| `lru_cache` on `get_settings()` | ✅ | `config.py:62` |
| Secrets typed as `SecretStr` | ❌ | All keys are plain `str` (e.g., `google_api_key: str = ""`) |
| URL validators | ❌ | `escapia_base_url` is plain `str` with default but no URL validation |
| Session-secret default | ❌ | `strqc_session_secret: str = ""` — empty default is dangerous if used for signing |

**Recommendation:** Convert all secret fields to `SecretStr` and access them via `.get_secret_value()`. Add a validator for `strqc_session_secret` that rejects empty/short values. Validate `escapia_base_url` as an HTTPS URL.

---

## Security Risks (OWASP / M8.4)

### A01: Broken Access Control / AuthZ

- **Status:** No access-control enforcement in `packages/shared` or `packages/db`.
- `repositories.py` accepts any open `sqlite3.Connection`; there is no row-level ownership check, role check, or stakeholder mapping before reads/writes.
- `set_task_stage`, `record_item_result`, `create_work_order`, etc. accept `inspector_id`/`completed_by` parameters but do not verify that the caller is authorized to act on that task or property.
- **Recommendation:** Introduce an authorization context (user role, stakeholder ID, property ACL) and validate every repository call against it. This is a v1 requirement per `M6.4` and `M8.4`.

### A02: Cryptographic Failures

- **Envelope encryption:** Implemented correctly (see above).
- **Session secret:** `STRQC_SESSION_SECRET` defaults to empty string (`config.py:59`). If used for signing session cookies or JWTs before configuration, this is equivalent to no signing. Mark as required or generate a strong random default in dev only with a warning.
- **Wi-Fi / door codes:** Schema has `*_ciphertext`/`*_secret_ref` columns (`sql/phase1_schema.sql:33-36`), but no repository helper currently writes encrypted values. The persistence layer must enforce encryption before insert.
- **PII:** Stakeholder `email`/`phone` and property addresses are stored in plaintext. Guest data from Escapia would also be plaintext. Consider encrypting sensitive PII at rest or tokenizing contact fields.

### A03: Injection (SQL Injection)

- **Status:** Clean in audited packages.
- All repository queries in `packages/db/src/strqc_db/repositories.py` use parameterized queries (`?` placeholders) and pass parameters as tuples. No dynamic string concatenation of user input into SQL.
- `migrate.py` uses `conn.executescript(sql)` but the SQL is read from packaged migration files, not user input.
- **Recommendation:** Maintain this discipline; add SQL-injection regression tests if any raw query builder is introduced.

### A05: Security Misconfiguration / Insecure Defaults

- `strqc_session_secret: str = ""` — insecure default.
- `strqc_api_host: str = "0.0.0.0"` (`config.py:57`) — acceptable in containerized environments but should bind to `127.0.0.1` in dev if not behind a reverse proxy.
- `aws_region: str = "us-east-1"` — reasonable default, but production should be explicit.
- `strqc_bidi_provider: str = "gemini"` — fine.
- No environment-specific settings (dev/staging/prod). Add a deployment environment enum and stricter defaults in production.

### A07: Identification and Authentication Failures

- No authN implementation in the audited packages.
- Escapia HSAPI tokens are not yet stored or refreshed; implementation is planned in `M4.1`.
- **Recommendation:** Store Escapia bearer tokens encrypted at rest, refresh before expiry, and scope them per-PMC.

### A09: Security Logging and Monitoring Failures / Observability (M8.5)

- **Status:** No observability in `packages/shared` or `packages/db`.
- No OpenTelemetry, structured logging, audit table, or tracing.
- `M8.5` requires "traces/metrics/logs dashboards; per-property audit trail of verdicts + deliveries."
- The schema has `task_stage_event` and `observed_at` timestamps, which provide a basic audit trail, but there is no centralized logging or telemetry integration.
- **Recommendation:** Add structured logging (e.g., `structlog`) and OpenTelemetry traces for all repository operations, tool calls, and decryption events. Ensure audit logs never contain plaintext secrets.

### Prompt Injection Defenses (M8.4)

- **Status:** Not present in audited packages.
- The BIDI agent and tool layer are in `apps/agent` and `backend/`, which are outside the immediate scope of this audit. `packages/shared` and `packages/db` do not handle tool-output parsing or LLM prompts, so injection defense belongs in the agent/bridge layer.
- **Recommendation:** Ensure tool outputs are validated schemas (not raw text inserted into prompts), and agent instructions include anti-injection guardrails.

---

## Data-Access Layer (M1.7)

File: `packages/db/src/strqc_db/repositories.py`

| Requirement | Status | Notes |
|---|---|---|
| Repository pattern | ✅ | Thin functions over `sqlite3.Connection` |
| Parameterized queries | ✅ | All queries use `?` placeholders |
| Transaction context managers | ✅ | `with conn:` used for writes |
| Foreign keys enabled | ✅ | `connection.py:13` and schema `PRAGMA foreign_keys = ON` |
| WAL mode | ✅ | `connection.py:14` |
| Typed models shared with API | ❌ | Returns plain `dict[str, Any]`; no Pydantic models or dataclasses |
| Escapia mapping tables | ❌ | `sync_cursor`, `housekeeping_status_map` not in schema yet |
| Addendum-1 fields | ❌ | `report.delivery_*`, `photo_memory.include_in_report` not in schema |
| Addendum-2 fields | ❌ | Escapia native IDs not in `property`, `task`, `work_order`, `stakeholder` |

The repository layer is well-structured for its current scope, but it is missing the schema extensions required for v1 and lacks typed models. The seed script (`packages/db/src/strqc_db/seed.py`) uses example email addresses and phone numbers, which is fine for local dev but should be flagged as synthetic PII.

---

## CI / Hygiene Status (M0.5)

File: `.github/workflows/ci.yml`

| Job | Status | Notes |
|---|---|---|
| Python lint | ✅ | `python -m ruff check packages apps/agent apps/api` |
| Python tests | ✅ | `pytest packages/shared/tests packages/db/tests apps/agent/tests apps/api/tests -q` |
| Web lint | ✅ | `npm run lint` |
| Web build | ✅ | `npm run build` |
| Type checking | ❌ | No mypy/pyright type-check step |
| Dependency audit | ❌ | No `pip-audit` or similar step |
| Secret scanning | ❌ | No `git-secrets` / `trufflehog` / `detect-secrets` step |
| Web cache path mismatch | ⚠️ | CI uses `cache-dependency-path: apps/web/package-lock.json` (`ci.yml:44`), but `apps/web/` contains `pnpm-lock.yaml`, not `package-lock.json`. |

Local lint run on the audited packages passed:

```bash
python -m ruff check packages/shared/src packages/shared/tests packages/db/src packages/db/tests
# All checks passed!
```

**Recommendation:** Add a type-check job (mypy/pyright), a `pip-audit` job, and a secret-scanning job (e.g., `trufflehog` or `git-secrets`) to CI. Fix the web cache-dependency-path to point at `pnpm-lock.yaml` or add an npm lockfile.

---

## Test Results

Command run:

```bash
python -m pytest packages/shared/tests -q
```

Result:

```
6 passed in 0.25s
```

All tests in `packages/shared/tests/test_crypto.py` pass. The `packages/db` package has no tests in scope (its tests are excluded from the requested command), and the repository layer currently has no unit coverage. `M1.7` explicitly requires repository unit coverage.

---

## Dependency Pinning & Vulnerabilities

### Shared package (`packages/shared/pyproject.toml`)

```toml
dependencies = [
    "pydantic>=2.7",
    "pydantic-settings>=2.2",
    "cryptography>=42.0",
]
```

- Loose lower-bound pinning only; no upper bounds or lock file.
- `cryptography>=42.0` is current; latest is 49.x. The minimum is still supported, but pinning to a known-good version range is safer.

### DB package (`packages/db/pyproject.toml`)

- No runtime dependencies. Good for a thin data-access package.

### Backend (`backend/requirements.txt`)

- Uses `>=X,<Y` ranges, which is better than open lower bounds.
- Still no lock file; production builds may resolve different versions over time.

### pip-audit results

Installed the shared package in a temporary virtual environment and ran `pip-audit --local`:

```json
{
  "dependencies": [
    ...
    {"name": "pip", "version": "26.1.1", "vulns": [
      {"id": "PYSEC-2026-196", "aliases": ["CVE-2026-8643"],
       "description": "pip would treat console_scripts and gui_scripts as paths instead of file names..."}
    ]}
  ]
}
```

- **Only one finding:** `pip` 26.1.1 has CVE-2026-8643. This is a build/development tool, not a production dependency, and is fixed in pip 26.1.2.
- No production vulnerabilities found in the installed shared-package dependencies.

**Recommendation:** Generate a `requirements.lock` or `uv.lock` from the production environment, add upper bounds where possible, and run `pip-audit` in CI.

---

## Risks and Recommendations (Prioritized)

| Priority | Risk | Recommendation | Owner / Milestone |
|---|---|---|---|
| **CRITICAL** | Real secrets live in `.env` on disk | Rotate all keys; move to secret manager; remove `.env` rewrite in `slack_token.py` | M0.3 / M8.4 |
| **HIGH** | `STRQC_SESSION_SECRET` defaults to empty | Make required or generate a secure dev-only default with a loud warning | M1.6 |
| **HIGH** | Secrets are plain `str` in Pydantic settings | Convert to `SecretStr`; access via `get_secret_value()` | M1.6 |
| **HIGH** | PII at rest is plaintext | Encrypt stakeholder contact fields and property addresses; tokenize guest data | M8.4 |
| **MEDIUM** | Schema missing Addendum-1/2 fields | Add migration for `Report.delivery_*`, `Photo.include_in_report`, Escapia IDs, `SyncCursor`, `HousekeepingStatusMap` | M1.2–M1.5 |
| **MEDIUM** | No authN/Z in repository layer | Add authorization context and validate every write | M6.4 / M8.4 |
| **MEDIUM** | No observability/tracing/audit logs | Add structured logging + OpenTelemetry; per-property audit trail | M8.5 |
| **MEDIUM** | No type-checking in CI | Add mypy/pyright job | M0.5 |
| **MEDIUM** | No secret scanning in CI | Add `trufflehog` or `detect-secrets` | M0.3 / M8.4 |
| **LOW** | Python deps loosely pinned | Add `requirements.lock` / `uv.lock`; run `pip-audit` in CI | M0.5 |
| **LOW** | CI web cache path mismatch | Fix `cache-dependency-path` to `pnpm-lock.yaml` | M0.5 |
| **LOW** | Empty AAD allowed in crypto | Enforce non-empty AAD when writing property secrets | M1.6 |

---

## Requirement Mapping Checklist

| Requirement | Source | Status | Evidence |
|---|---|---|---|
| M0.1 Workspace layout | `TASKS.md` | ✅ | `apps/`, `packages/`, `sql/`, `scripts/` per `README.md` |
| M0.2 Strands SDK pin | `TASKS.md` | 🟡 | Editable `harness-sdk/` + published pin in `backend/requirements.txt`; no single lock file |
| M0.3 Secrets hygiene | `TASKS.md` | 🟡 | `.gitignore` correct; `.env` not tracked; **real secrets present locally and need rotation** |
| M0.4 README quickstart | `TASKS.md` | ✅ | `README.md` §Quickstart documents `cp .env.example`, `make install`, `make migrate`, etc. |
| M0.5 Baseline CI | `TASKS.md` | 🟡 | Lint + test + web build present; missing type-check, audit, secret-scan; web cache-path bug |
| M1.6 Secrets encryption at rest | `AGENTS.md`, `TASKS.md` | 🟡 | Crypto module correct; schema has ciphertext columns; **not enforced end-to-end; no SecretStr; session secret empty** |
| M1.7 Data-access layer | `TASKS.md` | 🟡 | Repository pattern exists; missing typed models and unit tests |
| M8.4 Security review | `TASKS.md` | 🟡 | SQL injection clean; **authZ, authN, prompt injection, Escapia token storage, signed URLs not implemented** |
| M8.5 Observability | `TASKS.md` | ❌ | No tracing/telemetry/logging in audited packages |
| Addendum 1 fields (`Report.delivery_*`, `Photo.include_in_report`) | `AGENTS.md` | ❌ | Not in `sql/phase1_schema.sql` or repositories |
| Addendum 2 fields (Escapia IDs, `SyncCursor`, `HousekeepingStatusMap`) | `AGENTS.md` | ❌ | Not in `sql/phase1_schema.sql` or repositories |

---

## Appendix: Files Reviewed

- `/Users/tims-stuff/RandD/RandD/packages/shared/src/strqc_shared/config.py`
- `/Users/tims-stuff/RandD/RandD/packages/shared/src/strqc_shared/crypto.py`
- `/Users/tims-stuff/RandD/RandD/packages/shared/tests/test_crypto.py`
- `/Users/tims-stuff/RandD/RandD/packages/db/src/strqc_db/connection.py`
- `/Users/tims-stuff/RandD/RandD/packages/db/src/strqc_db/migrate.py`
- `/Users/tims-stuff/RandD/RandD/packages/db/src/strqc_db/seed.py`
- `/Users/tims-stuff/RandD/RandD/packages/db/src/strqc_db/repositories.py`
- `/Users/tims-stuff/RandD/RandD/.env.example`
- `/Users/tims-stuff/RandD/RandD/.env` (keys only, values redacted)
- `/Users/tims-stuff/RandD/RandD/.gitignore`
- `/Users/tims-stuff/RandD/RandD/gmail_auth.py`
- `/Users/tims-stuff/RandD/RandD/scripts/slack_reinstall.py`
- `/Users/tims-stuff/RandD/RandD/backend/app/slack_token.py` (cross-cutting security review)
- `/Users/tims-stuff/RandD/RandD/backend/app/slack_report.py` (cross-cutting security review)
- `/Users/tims-stuff/RandD/RandD/sql/phase1_schema.sql`
- `/Users/tims-stuff/RandD/RandD/.github/workflows/ci.yml`
- `/Users/tims-stuff/RandD/RandD/Makefile`
- `/Users/tims-stuff/RandD/RandD/README.md`
- `/Users/tims-stuff/RandD/RandD/TASKS.md`
- `/Users/tims-stuff/RandD/RandD/AGENTS.md`
