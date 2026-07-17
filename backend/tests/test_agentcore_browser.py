import asyncio
import json
from typing import Any

import pytest

from app.agentcore_browser import LiveViewAgentCoreBrowser
from app.io import BidiWebSocketInput


_CREATED_BROWSERS: list[LiveViewAgentCoreBrowser] = []


@pytest.fixture(autouse=True)
def clean_up_browser_event_loops():
    try:
        previous_loop = asyncio.get_event_loop()
    except RuntimeError:
        previous_loop = None
    start = len(_CREATED_BROWSERS)
    yield
    for browser in _CREATED_BROWSERS[start:]:
        browser.close_all()
        if not browser._loop.is_closed():
            browser._loop.close()
    asyncio.set_event_loop(previous_loop)


class FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.visited: list[str] = []

    async def goto(self, url: str) -> None:
        self.url = url
        self.visited.append(url)

    async def wait_for_load_state(self, state: str) -> None:
        assert state == "networkidle"

    async def close(self) -> None:
        return


class FakeContext:
    def __init__(self) -> None:
        self.page = FakePage()

    async def new_page(self) -> FakePage:
        return self.page

    async def close(self) -> None:
        return


class FakePlaywrightBrowser:
    def __init__(self) -> None:
        self.contexts = [FakeContext()]

    async def close(self) -> None:
        return


class FakeChromium:
    def __init__(self) -> None:
        self.connections: list[tuple[str, dict[str, str]]] = []
        self.browser = FakePlaywrightBrowser()

    async def connect_over_cdp(self, *, endpoint_url: str, headers: dict[str, str]) -> FakePlaywrightBrowser:
        self.connections.append((endpoint_url, headers))
        return self.browser


class FakePlaywright:
    def __init__(self) -> None:
        self.chromium = FakeChromium()


class FakeBrowserClient:
    def __init__(self) -> None:
        self.session_id = "agentcore-session-1"
        self.identifier = "aws.browser.v1"
        self.started: list[dict[str, Any]] = []
        self.live_view_calls = 0
        self.take_control_calls = 0
        self.release_control_calls = 0
        self.stop_calls = 0
        self.live_view_error: Exception | None = None
        self.stop_error: Exception | None = None

    def start(self, **kwargs: Any) -> str:
        self.started.append(kwargs)
        return self.session_id

    def generate_ws_headers(self) -> tuple[str, dict[str, str]]:
        return "wss://automation.example/cdp", {"x-session": self.session_id}

    def generate_live_view_url(self, *, expires: int = 300) -> str:
        self.live_view_calls += 1
        if self.live_view_error:
            raise self.live_view_error
        return f"https://live.example/{self.session_id}?signature={self.live_view_calls}&expires={expires}"

    def take_control(self) -> None:
        self.take_control_calls += 1

    def release_control(self) -> None:
        self.release_control_calls += 1

    def stop(self) -> bool:
        self.stop_calls += 1
        if self.stop_error:
            raise self.stop_error
        return True


def make_browser(
    events: list[dict[str, Any]],
) -> tuple[LiveViewAgentCoreBrowser, FakeBrowserClient, FakePlaywright]:
    client = FakeBrowserClient()
    browser = LiveViewAgentCoreBrowser(
        region="us-west-2",
        client_factory=lambda **_: client,
        event_sink=events.append,
    )
    _CREATED_BROWSERS.append(browser)
    playwright = FakePlaywright()
    browser._playwright = playwright
    browser._started = True
    # The upstream sync bridge globally applies nest_asyncio. Keep that
    # third-party process-wide mutation out of this unit test module so later
    # pytest-asyncio and AnyIO tests retain their normal event-loop semantics.
    browser._execute_async = browser._loop.run_until_complete
    return browser, client, playwright


def init_browser(browser: LiveViewAgentCoreBrowser) -> dict[str, Any]:
    return browser.browser(
        {
            "action": {
                "type": "init_session",
                "description": "Research an appliance",
                "session_name": "research-session",
            }
        }
    )


def test_init_retains_exact_agentcore_client_and_emits_live_session() -> None:
    events: list[dict[str, Any]] = []
    browser, client, playwright = make_browser(events)

    result = init_browser(browser)

    assert result["status"] == "success"
    assert browser.client_for("research-session") is client
    assert client.started == [
        {"identifier": "aws.browser.v1", "session_timeout_seconds": 3600}
    ]
    assert playwright.chromium.connections == [
        ("wss://automation.example/cdp", {"x-session": "agentcore-session-1"})
    ]
    assert events == [
        {
            "type": "browser_session",
            "sessionName": "research-session",
            "liveViewUrl": "https://live.example/agentcore-session-1?signature=1&expires=300",
            "currentPageUrl": "about:blank",
            "status": "active",
        }
    ]


def test_custom_browser_id_and_region_reach_the_native_client_unchanged() -> None:
    events: list[dict[str, Any]] = []
    client = FakeBrowserClient()
    factory_calls: list[dict[str, Any]] = []

    def client_factory(**kwargs: Any) -> FakeBrowserClient:
        factory_calls.append(kwargs)
        return client

    browser = LiveViewAgentCoreBrowser(
        region="us-east-1",
        identifier="browser_use_tool_ckljx-o9oT8gdjLQ",
        client_factory=client_factory,
        event_sink=events.append,
    )
    _CREATED_BROWSERS.append(browser)
    browser._playwright = FakePlaywright()
    browser._started = True
    browser._execute_async = browser._loop.run_until_complete

    result = init_browser(browser)

    assert result["status"] == "success"
    assert factory_calls == [{"region": "us-east-1"}]
    assert client.started == [
        {
            "identifier": "browser_use_tool_ckljx-o9oT8gdjLQ",
            "session_timeout_seconds": 3600,
        }
    ]


def test_native_navigation_emits_current_page_without_creating_another_browser() -> None:
    events: list[dict[str, Any]] = []
    browser, client, playwright = make_browser(events)
    init_browser(browser)

    result = browser.browser(
        {
            "action": {
                "type": "navigate",
                "session_name": "research-session",
                "url": "https://example.com/product",
            }
        }
    )

    assert result["status"] == "success"
    assert playwright.chromium.browser.contexts[0].page.visited == [
        "https://example.com/product"
    ]
    assert client.started == [
        {"identifier": "aws.browser.v1", "session_timeout_seconds": 3600}
    ]
    assert events[-1] == {
        "type": "browser_session",
        "sessionName": "research-session",
        "currentPageUrl": "https://example.com/product",
        "status": "active",
    }
    assert "liveViewUrl" not in events[-1]


def test_failed_strands_session_setup_stops_the_started_remote_client() -> None:
    events: list[dict[str, Any]] = []
    browser, client, playwright = make_browser(events)
    playwright.chromium.browser.contexts = []

    result = init_browser(browser)

    assert result["status"] == "error"
    assert client.stop_calls == 1
    assert browser.client_for("research-session") is None


def test_live_view_failure_emits_error_without_discarding_working_browser() -> None:
    events: list[dict[str, Any]] = []
    browser, client, _ = make_browser(events)
    client.live_view_error = RuntimeError("presigning unavailable")

    result = init_browser(browser)

    assert result["status"] == "success"
    assert browser.client_for("research-session") is client
    assert events[-1] == {
        "type": "browser_control",
        "sessionName": "research-session",
        "state": "error",
        "error": "presigning unavailable",
    }


def test_setup_failure_keeps_original_error_when_remote_stop_also_fails() -> None:
    events: list[dict[str, Any]] = []
    browser, client, playwright = make_browser(events)
    playwright.chromium.browser.contexts = []
    client.stop_error = RuntimeError("stop unavailable")

    result = init_browser(browser)

    assert result["status"] == "error"
    assert "CDP connection has no contexts" in result["content"][0]["text"]
    assert browser.client_for("research-session") is None


@pytest.mark.parametrize(
    ("action", "expected_state", "counter"),
    [
        ("take", "human", "take_control_calls"),
        ("release", "agent", "release_control_calls"),
    ],
)
def test_human_control_delegates_to_native_client(
    action: str, expected_state: str, counter: str
) -> None:
    events: list[dict[str, Any]] = []
    browser, client, _ = make_browser(events)
    init_browser(browser)

    result = browser.handle_control(
        {"action": action, "sessionName": "research-session"}
    )

    assert result == {
        "type": "browser_control",
        "sessionName": "research-session",
        "state": expected_state,
    }
    assert getattr(client, counter) == 1
    assert events[-1] == result


def test_refresh_generates_a_new_live_view_url_for_the_same_client() -> None:
    events: list[dict[str, Any]] = []
    browser, client, _ = make_browser(events)
    init_browser(browser)

    result = browser.handle_control(
        {"action": "refresh_live_view", "sessionName": "research-session"}
    )

    assert client.live_view_calls == 2
    assert result == {
        "type": "browser_session",
        "sessionName": "research-session",
        "liveViewUrl": "https://live.example/agentcore-session-1?signature=2&expires=300",
        "currentPageUrl": "about:blank",
        "status": "active",
    }
    assert events[-1] == result


def test_close_stops_exact_client_once_and_emits_closed_without_signed_url() -> None:
    events: list[dict[str, Any]] = []
    browser, client, _ = make_browser(events)
    init_browser(browser)

    browser.close_all()
    browser.close_all()

    assert client.stop_calls == 1
    assert browser.client_for("research-session") is None
    assert events[-1] == {
        "type": "browser_control",
        "sessionName": "research-session",
        "state": "closed",
    }
    assert all("liveViewUrl" not in event for event in events if event["type"] == "browser_control")


def test_browser_close_action_does_not_reopen_closed_session_in_ui() -> None:
    events: list[dict[str, Any]] = []
    browser, client, _ = make_browser(events)
    init_browser(browser)
    events.clear()

    result = browser.browser(
        {"action": {"type": "close", "session_name": "research-session"}}
    )

    assert result["status"] == "success"
    assert client.stop_calls == 1
    assert events == [
        {
            "type": "browser_control",
            "sessionName": "research-session",
            "state": "closed",
        }
    ]


class FakeWebSocket:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = [json.dumps(message) for message in messages]

    async def receive_text(self) -> str:
        return self.messages.pop(0)


@pytest.mark.asyncio
async def test_browser_control_input_is_consumed_without_becoming_model_text() -> None:
    handled: list[dict[str, Any]] = []
    websocket = FakeWebSocket(
        [
            {
                "type": "browser_control",
                "action": "take",
                "sessionName": "research-session",
            },
            {"type": "bidi_text_input", "text": "continue research"},
        ]
    )

    async def resolve(payload: dict[str, Any]) -> None:
        handled.append(payload)

    input_channel = BidiWebSocketInput(
        websocket, browser_control_resolver=resolve
    )

    event = await input_channel()

    assert handled == [
        {"action": "take", "sessionName": "research-session"}
    ]
    assert event["type"] == "bidi_text_input"
    assert event["text"] == "continue research"
