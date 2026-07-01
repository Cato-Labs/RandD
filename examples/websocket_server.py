"""WebSocket server example using FastAPI.

Exposes the Gemini Live agent over a WebSocket. Audio I/O is handled by the
client, so this runs server-side without PyAudio. The agent's ``run()`` method
accepts the WebSocket's ``receive_json``/``send_json`` callables directly as
input/output channels.

Run:
    pip install "gemini-bidi-agent[server]"      # or: pip install fastapi uvicorn
    uvicorn examples.websocket_server:app --reload

Then connect a client that sends JSON input events, e.g.:
    {"type": "bidi_text_input", "text": "Hello, how are you?"}

and reads streaming output events (transcripts, audio, tool use, ...).

Requires: a configured GOOGLE_API_KEY.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from gemini_bidi_agent import build_agent

app = FastAPI(title="Gemini Live BidiAgent")


@app.websocket("/chat")
async def chat(websocket: WebSocket) -> None:
    """Stream a bidirectional conversation over a WebSocket connection."""
    # Session persistence is disabled here; each socket is its own conversation.
    agent = build_agent(use_session=False)

    try:
        await websocket.accept()
        await agent.run(
            inputs=[websocket.receive_json],
            outputs=[websocket.send_json],
        )
    except* WebSocketDisconnect:
        print("client disconnected")
    finally:
        await agent.stop()
