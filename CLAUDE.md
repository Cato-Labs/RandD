# CLAUDE.md — Agent working rules for this repository

## Native Strands runtime

- Production uses the published `strands-agents` package from site-packages.
- One `BidiAgent` is created per WebSocket connection and runs only through
  `await agent.run(inputs=[...], outputs=[...], invocation_state=...)`.
- Register direct native tools, project `@tool` functions, memory-manager tools,
  and discovered MCP `ProxyTool` objects before the connection starts.
- Do not vendor or copy the Strands loop, dynamically redeclare tools, supervise
  reconnects, wrap native tools, handwrite native schemas or tool-use IDs, patch
  site-packages, or add fallback implementations.

## General rules

- Prefer documented Strands framework primitives and inspect the installed source
  before changing SDK integration.
- Preserve unrelated dirty worktree changes.
- No mocks, stubs, fake media, fake providers, or simulated results.
- Test changes through the actual visible UI with Playwright.
- Never print credentials or tokens.
- See `AGENTS.md` for product requirements.
