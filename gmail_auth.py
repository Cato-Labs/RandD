#!/usr/bin/env python3
"""Headless-friendly Google OAuth for Strands in a dev container / Codespace.

Why the stock command fails here:
    `python -m strands_google.google_auth` calls `flow.run_local_server(port=0)`,
    which starts the OAuth callback server on a random port *inside* the
    container. Your browser runs on the host, so Google's redirect to
    `http://localhost:<port>/` never reaches the container and the page fails
    with ERR_CONNECTION_REFUSED.

What this does instead:
    It listens on a fixed port (8080) and *also* accepts a pasted URL, so a
    single approval finishes the flow either way:
      * If VS Code forwards port 8080 to your host, the redirect lands on the
        server automatically and you do nothing else.
      * If it does not, the browser shows "This site can't be reached" — just
        copy that address bar URL and paste it into the terminal.

Usage:
    python gmail_auth.py

Optional environment overrides:
    GOOGLE_OAUTH_CLIENT   path to the OAuth client json  (default: gmail_credentials.json)
    GOOGLE_OAUTH_TOKEN    path to write the token to     (default: gmail_token.json)
    GOOGLE_OAUTH_SCOPES   space/comma separated scopes   (default: strands_google DEFAULT_SCOPES)
"""

import http.server
import os
import sys
import threading
import webbrowser

# Google echoes back the union of granted scopes, which can differ from the
# requested set; relax the check so the token exchange does not raise.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from strands_google.google_auth import DEFAULT_SCOPES

CREDENTIALS_FILE = os.environ.get("GOOGLE_OAUTH_CLIENT", "gmail_credentials.json")
TOKEN_FILE = os.environ.get("GOOGLE_OAUTH_TOKEN", "gmail_token.json")
CALLBACK_PORT = 8080
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/"
WAIT_SECONDS = 300


def _resolve_scopes() -> list[str]:
    override = os.environ.get("GOOGLE_OAUTH_SCOPES")
    if override:
        return [scope for scope in override.replace(",", " ").split() if scope]
    return DEFAULT_SCOPES


def _save(creds: Credentials) -> None:
    with open(TOKEN_FILE, "w") as handle:
        handle.write(creds.to_json())


def _load_existing(scopes: list[str]) -> Credentials | None:
    if not os.path.exists(TOKEN_FILE):
        return None
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        print("Refreshing expired token...")
        creds.refresh(Request())
        _save(creds)
        return creds
    return None


def _make_handler(
    holder: dict[str, str], done: threading.Event
) -> type[http.server.BaseHTTPRequestHandler]:
    class _CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            holder.setdefault("url", f"http://localhost:{CALLBACK_PORT}{self.path}")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<h2>Authentication received.</h2>"
                b"<p>You can close this tab and return to the terminal.</p>"
            )
            done.set()

        def log_message(self, *args: object) -> None:  # silence per-request logging
            pass

    return _CallbackHandler


def _read_pasted_url(holder: dict[str, str], done: threading.Event) -> None:
    try:
        pasted = input(
            "\n...or if the page won't load, paste the full http://localhost:8080/... URL here: "
        ).strip()
    except EOFError:
        return
    if pasted and "url" not in holder:
        holder["url"] = pasted
        done.set()


def authenticate() -> Credentials:
    scopes = _resolve_scopes()

    existing = _load_existing(scopes)
    if existing:
        print(f"Reusing valid token at {os.path.abspath(TOKEN_FILE)}")
        return existing

    if not os.path.exists(CREDENTIALS_FILE):
        sys.exit(
            f"Missing OAuth client file: {CREDENTIALS_FILE}\n"
            "Download a 'Desktop app' OAuth client from "
            "https://console.cloud.google.com/apis/credentials"
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, scopes)
    flow.redirect_uri = REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    holder: dict[str, str] = {}
    done = threading.Event()

    server = http.server.HTTPServer(("localhost", CALLBACK_PORT), _make_handler(holder, done))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=_read_pasted_url, args=(holder, done), daemon=True).start()

    print("\nOpen this URL and approve access (your browser should open automatically):\n")
    print(auth_url + "\n")
    try:
        webbrowser.open(auth_url)
    except Exception:  # noqa: BLE001 - opening a browser is best-effort
        pass
    print("After you approve, this finishes automatically if the port is forwarded.")
    print("If the browser instead shows 'This site can't be reached', that is fine —")
    print("copy that address bar URL and paste it at the prompt below.")

    if not done.wait(timeout=WAIT_SECONDS):
        server.shutdown()
        sys.exit("\nTimed out waiting for authorization. Re-run: python gmail_auth.py")
    server.shutdown()

    flow.fetch_token(authorization_response=holder["url"])
    creds = flow.credentials
    _save(creds)
    print(f"\nToken saved to {os.path.abspath(TOKEN_FILE)}")
    return creds


def main() -> None:
    creds = authenticate()
    try:
        from googleapiclient.discovery import build

        service = build("gmail", "v1", credentials=creds)
        email = service.users().getProfile(userId="me").execute().get("emailAddress")
        print(f"Connected as: {email}")
    except Exception as exc:  # noqa: BLE001 - a failed smoke test should not lose the token
        print(f"Token generated, but the Gmail smoke test failed: {exc}")

    print("\nNext step — point the Google tools at the token:")
    print(f"  export GOOGLE_OAUTH_CREDENTIALS={os.path.abspath(TOKEN_FILE)}")


if __name__ == "__main__":
    main()
