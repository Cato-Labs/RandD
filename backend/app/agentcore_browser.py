"""Native AgentCore browser with live-view and human-control lifecycle.

The Strands browser implementation owns Playwright and every automation action.
This subclass only retains the ``BrowserClient`` created for each Strands
session so the application can expose AgentCore's live view and native HITL
controls for that exact session.
"""

import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import Any

from bedrock_agentcore.tools.browser_client import BrowserClient
from playwright.async_api import Browser as PlaywrightBrowser
from strands import tool
from strands_tools.browser import AgentCoreBrowser
from strands_tools.browser.models import BrowserInput


logger = logging.getLogger(__name__)

BrowserEventSink = Callable[[dict[str, Any]], Any]
BrowserClientFactory = Callable[..., BrowserClient]


class LiveViewAgentCoreBrowser(AgentCoreBrowser):
    """AgentCoreBrowser that exposes the native session's live HITL view."""

    def __init__(
        self,
        *,
        region: str | None = None,
        identifier: str | None = None,
        session_timeout: int = 3600,
        live_view_expires: int = 300,
        event_sink: BrowserEventSink | None = None,
        client_factory: BrowserClientFactory = BrowserClient,
    ) -> None:
        super().__init__(
            region=region,
            identifier=identifier,
            session_timeout=session_timeout,
        )
        self.live_view_expires = live_view_expires
        self._event_sink = event_sink
        self._client_factory = client_factory
        self._pending_session_name: str | None = None

    @tool
    def browser(self, browser_input: BrowserInput) -> dict[str, Any]:
        """Run a native Strands browser action and publish its session state."""
        action = (
            BrowserInput.model_validate(browser_input).action
            if isinstance(browser_input, dict)
            else browser_input.action
        )
        session_name = getattr(action, "session_name", None)
        action_type = getattr(action, "type", "")
        if action_type == "init_session":
            self._pending_session_name = session_name

        try:
            result = super().browser(browser_input)
        finally:
            self._pending_session_name = None

        if result.get("status") != "success" and action_type == "init_session":
            client = self._client_dict.pop(str(session_name), None)
            if client is not None:
                self._stop_client(str(session_name), client)
        elif (
            result.get("status") == "success"
            and session_name
            and action_type != "close"
        ):
            try:
                self._emit(
                    self._session_event(
                        session_name,
                        include_live_view=action_type == "init_session",
                    )
                )
            except Exception as exc:
                self._control_error(session_name, str(exc))
        return result

    async def create_browser_session(self) -> PlaywrightBrowser:
        """Create the native remote browser and retain its exact client."""
        if not self._playwright:
            raise RuntimeError("Playwright not initialized")
        if not self._pending_session_name:
            raise RuntimeError("AgentCore browser session name is unavailable")

        session_name = self._pending_session_name
        client = self._client_factory(region=self.region)
        client.start(
            identifier=self.identifier,
            session_timeout_seconds=self.session_timeout,
        )
        self._client_dict[session_name] = client
        try:
            cdp_url, cdp_headers = client.generate_ws_headers()
            return await self._playwright.chromium.connect_over_cdp(
                endpoint_url=cdp_url,
                headers=cdp_headers,
            )
        except Exception:
            self._client_dict.pop(session_name, None)
            self._stop_client(session_name, client)
            raise

    def client_for(self, session_name: str) -> BrowserClient | None:
        """Return the retained native client for a Strands session."""
        return self._client_dict.get(session_name)

    def handle_control(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Apply a UI control action without forwarding it to the model."""
        action = str(payload.get("action") or "")
        session_name = self._resolve_session_name(payload.get("sessionName"))
        client = self._client_dict.get(session_name)
        if client is None:
            return self._control_error(session_name, "Browser session not found")

        try:
            if action == "take":
                client.take_control()
                event = self._control_event(session_name, "human")
            elif action == "release":
                client.release_control()
                event = self._control_event(session_name, "agent")
            elif action == "refresh_live_view":
                event = self._session_event(session_name, include_live_view=True)
            else:
                return self._control_error(
                    session_name, f"Unsupported browser control action: {action}"
                )
        except Exception as exc:
            logger.warning(
                "session=<%s> | AgentCore browser control failed: %s",
                session_name,
                exc,
            )
            return self._control_error(session_name, str(exc))

        self._emit(event)
        return event

    def close_platform(self) -> None:
        """Stop each retained AgentCore client exactly once."""
        clients = list(self._client_dict.items())
        self._client_dict.clear()
        for session_name, client in clients:
            self._stop_client(session_name, client)
            self._emit(self._control_event(session_name, "closed"))

    def close_all(self) -> None:
        """Deterministically close Playwright and all retained remote sessions."""
        self._cleanup()

    def _resolve_session_name(self, requested: Any) -> str:
        if requested:
            return str(requested)
        if len(self._client_dict) == 1:
            return next(iter(self._client_dict))
        return ""

    @staticmethod
    def _stop_client(session_name: str, client: BrowserClient) -> None:
        try:
            client.stop()
        except Exception as exc:
            logger.error(
                "session=<%s>, exception=<%s> | failed to close AgentCore browser session",
                session_name,
                exc,
            )

    def _session_event(
        self, session_name: str, *, include_live_view: bool
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "type": "browser_session",
            "sessionName": session_name,
        }
        if include_live_view:
            client = self._client_dict.get(session_name)
            if client is None:
                raise RuntimeError(f"Browser session '{session_name}' not found")
            event["liveViewUrl"] = client.generate_live_view_url(
                expires=self.live_view_expires
            )
        page = self.get_session_page(session_name)
        event["currentPageUrl"] = str(page.url if page else "")
        event["status"] = "active"
        return event

    @staticmethod
    def _control_event(session_name: str, state: str) -> dict[str, Any]:
        return {
            "type": "browser_control",
            "sessionName": session_name,
            "state": state,
        }

    def _control_error(self, session_name: str, message: str) -> dict[str, Any]:
        event = {
            **self._control_event(session_name, "error"),
            "error": message,
        }
        self._emit(event)
        return event

    def _emit(self, event: dict[str, Any]) -> None:
        if self._event_sink is None:
            return
        result = self._event_sink(event)
        if inspect.isawaitable(result):
            try:
                asyncio.get_running_loop().create_task(result)
            except RuntimeError:
                self._loop.run_until_complete(result)
