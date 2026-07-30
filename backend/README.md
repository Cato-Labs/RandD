# Vantage native Strands backend

The FastAPI backend creates one published Strands `BidiAgent` for each
authenticated WebSocket connection and executes it only through
`BidiAgent.run(inputs=[...], outputs=[...], invocation_state=...)`.

Pinned dependencies are declared in `requirements.txt`:

- `strands-agents==1.48.0`
- `strands-agents-tools==0.8.4`
- `strands-fun-tools==0.4.0`
- `strands-google==0.1.0`

Native tools, direct project `@tool` functions, `MemoryManager.tools`, and
Smarty MCP `ProxyTool` objects are registered before the connection starts.
There is no vendored SDK, copied Bidi loop, runtime tool redeclaration, or
native-tool wrapper layer.
