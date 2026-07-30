"""Native ToolContext-backed photo approval tool."""

from __future__ import annotations

from strands import ToolContext, tool

from app.approval_registry import ApprovalRegistry


@tool(context=True)
async def request_photo_approval(
    tool_context: ToolContext,
    inspection_id: str,
    media_id: str,
    rationale: str,
    item_id: str = "",
    result_id: str = "",
    asset_id: str = "",
    proposed_verdict: str = "",
) -> dict:
    """Show a persisted original in the product UI and await human approval.

    Args:
        inspection_id: Persisted inspection identifier.
        media_id: Persisted original-media identifier.
        rationale: Reason approval is required.
        item_id: Optional checklist item destination.
        result_id: Optional checklist result destination.
        asset_id: Optional asset destination.
        proposed_verdict: Optional proposed inspection verdict.

    Returns:
        The real approval decision and optional feedback.
    """
    state = tool_context.invocation_state
    registry = state.get("approval_registry")
    session_id = str(state.get("session_id") or "")
    if not isinstance(registry, ApprovalRegistry) or not session_id:
        raise RuntimeError("approval registry is unavailable in Strands invocation_state")
    request = registry.request(
        session_id=session_id,
        inspection_id=inspection_id,
        media_id=media_id,
        rationale=rationale,
        item_id=item_id or None,
        result_id=result_id or None,
        asset_id=asset_id or None,
        proposed_verdict=proposed_verdict or None,
        timeout_seconds=300,
    )
    resolution = await registry.wait(
        session_id=session_id,
        approval_id=request.approval_id,
    )
    return {
        "approval_id": request.approval_id,
        "decision": resolution.decision,
        "feedback": resolution.feedback,
        "input_mode": resolution.input_mode,
    }
