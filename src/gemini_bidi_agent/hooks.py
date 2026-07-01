"""Lifecycle hooks for the Gemini Live agent.

Hooks subscribe to strongly-typed events emitted throughout the bidirectional
streaming lifecycle. All callbacks are asynchronous so they never block the
agent's real-time communication loop.

The hook event classes live in ``strands.experimental.hooks.events``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from strands.experimental.hooks.events import (
    BidiAfterConnectionRestartEvent,
    BidiAfterInvocationEvent,
    BidiAgentInitializedEvent,
    BidiBeforeConnectionRestartEvent,
    BidiBeforeInvocationEvent,
    BidiInterruptionEvent,
    BidiMessageAddedEvent,
)
from strands.hooks import HookProvider, HookRegistry

logger = logging.getLogger("gemini_bidi_agent.hooks")


class ConversationLogger(HookProvider):
    """Log agent lifecycle and every message added to conversation history."""

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register callbacks for lifecycle and message events.

        ``BidiAgentInitializedEvent`` is dispatched synchronously during agent
        construction, so its callback is synchronous. All other callbacks run in
        the async communication loop and are therefore ``async``.
        """
        registry.add_callback(BidiAgentInitializedEvent, self.on_agent_initialized)
        registry.add_callback(BidiBeforeInvocationEvent, self.on_before_invocation)
        registry.add_callback(BidiMessageAddedEvent, self.on_message_added)
        registry.add_callback(BidiAfterInvocationEvent, self.on_after_invocation)

    def on_agent_initialized(self, event: BidiAgentInitializedEvent) -> None:
        logger.info("Agent %s initialized", event.agent.agent_id)

    async def on_before_invocation(self, event: BidiBeforeInvocationEvent) -> None:
        logger.info("Connection starting for agent %s", event.agent.name)

    async def on_message_added(self, event: BidiMessageAddedEvent) -> None:
        message = event.message
        logger.info("Message added (%s)", message.get("role"))

    async def on_after_invocation(self, event: BidiAfterInvocationEvent) -> None:
        logger.info("Connection ended for agent %s", event.agent.name)


class InterruptionTracker(HookProvider):
    """Track how often and why the model is interrupted (barge-in)."""

    def __init__(self) -> None:
        self.interruption_count = 0
        self.interruptions: list[dict[str, Any]] = []

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register the interruption callback."""
        registry.add_callback(BidiInterruptionEvent, self.on_interruption)

    async def on_interruption(self, event: BidiInterruptionEvent) -> None:
        self.interruption_count += 1
        self.interruptions.append(
            {
                "reason": event.reason,
                "response_id": event.interrupted_response_id,
                "timestamp": time.time(),
            }
        )
        logger.info("Interruption #%d: %s", self.interruption_count, event.reason)


class ConnectionMonitor(HookProvider):
    """Monitor connection restarts triggered by model timeouts."""

    def __init__(self) -> None:
        self.restart_count = 0
        self.restart_failures: list[Exception] = []

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register the connection-restart callbacks."""
        registry.add_callback(BidiBeforeConnectionRestartEvent, self.on_before_restart)
        registry.add_callback(BidiAfterConnectionRestartEvent, self.on_after_restart)

    async def on_before_restart(self, event: BidiBeforeConnectionRestartEvent) -> None:
        self.restart_count += 1
        logger.warning(
            "Connection restarting (attempt #%d): %s",
            self.restart_count,
            event.timeout_error,
        )

    async def on_after_restart(self, event: BidiAfterConnectionRestartEvent) -> None:
        if event.exception:
            self.restart_failures.append(event.exception)
            logger.error("Connection restart failed: %s", event.exception)
        else:
            logger.info("Connection successfully restarted")


class ConversationAnalytics(HookProvider):
    """Collect simple metrics about a conversation."""

    def __init__(self) -> None:
        self.start_time: float | None = None
        self.message_count = 0
        self.user_messages = 0
        self.assistant_messages = 0
        self.tool_calls = 0
        self.interruptions = 0

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register analytics callbacks."""
        registry.add_callback(BidiBeforeInvocationEvent, self.on_before_invocation)
        registry.add_callback(BidiMessageAddedEvent, self.on_message_added)
        registry.add_callback(BidiInterruptionEvent, self.on_interruption)
        registry.add_callback(BidiAfterInvocationEvent, self.on_after_invocation)

    async def on_before_invocation(self, event: BidiBeforeInvocationEvent) -> None:
        self.start_time = time.time()

    async def on_message_added(self, event: BidiMessageAddedEvent) -> None:
        self.message_count += 1
        role = event.message.get("role")
        if role == "user":
            self.user_messages += 1
        elif role == "assistant":
            self.assistant_messages += 1
            for content in event.message.get("content", []) or []:
                if isinstance(content, dict) and "toolUse" in content:
                    self.tool_calls += 1

    async def on_interruption(self, event: BidiInterruptionEvent) -> None:
        self.interruptions += 1

    async def on_after_invocation(self, event: BidiAfterInvocationEvent) -> None:
        duration = time.time() - self.start_time if self.start_time else 0.0
        logger.info(
            "Conversation summary: duration=%.1fs messages=%d (user=%d assistant=%d) "
            "tool_calls=%d interruptions=%d",
            duration,
            self.message_count,
            self.user_messages,
            self.assistant_messages,
            self.tool_calls,
            self.interruptions,
        )

    def snapshot(self) -> dict[str, Any]:
        """Return a snapshot of the collected metrics."""
        return {
            "message_count": self.message_count,
            "user_messages": self.user_messages,
            "assistant_messages": self.assistant_messages,
            "tool_calls": self.tool_calls,
            "interruptions": self.interruptions,
        }


def default_hooks() -> list[HookProvider]:
    """Return the default set of hook providers wired into the agent."""
    return [
        ConversationLogger(),
        InterruptionTracker(),
        ConnectionMonitor(),
        ConversationAnalytics(),
    ]
