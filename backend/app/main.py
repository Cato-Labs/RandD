import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from strands_tools import editor, load_tool, shell

from app.agent import DEFAULT_MODEL_ID, create_agent
from app.prompts import SYSTEM_PROMPT

os.environ.setdefault("STRANDS_NON_INTERACTIVE", "true")
os.environ.setdefault("BYPASS_TOOL_CONSENT", "true")

WORKSPACE_DIR = Path(__file__).resolve().parent.parent / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="RandD Live Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/workspace", StaticFiles(directory=WORKSPACE_DIR), name="workspace")

VOICES = [
    {"id": "Puck", "name": "Puck", "gender": "male", "accent": "American", "age": "adult", "description": "Upbeat male voice."},
    {"id": "Charon", "name": "Charon", "gender": "male", "accent": "American", "age": "adult", "description": "Informative, deep male voice."},
    {"id": "Kore", "name": "Kore", "gender": "female", "accent": "American", "age": "adult", "description": "Firm female voice."},
    {"id": "Fenrir", "name": "Fenrir", "gender": "male", "accent": "American", "age": "adult", "description": "Excitable male voice."},
    {"id": "Aoede", "name": "Aoede", "gender": "female", "accent": "American", "age": "adult", "description": "Breezy female voice."},
    {"id": "Leda", "name": "Leda", "gender": "female", "accent": "American", "age": "youthful", "description": "Youthful female voice."},
    {"id": "Orus", "name": "Orus", "gender": "male", "accent": "American", "age": "adult", "description": "Firm male voice."},
    {"id": "Zephyr", "name": "Zephyr", "gender": "female", "accent": "American", "age": "adult", "description": "Bright female voice."},
]


@app.on_event("startup")
async def startup() -> None:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(WORKSPACE_DIR)


def _tool_spec(module: Any, name: str) -> dict[str, Any]:
    spec = getattr(module, "TOOL_SPEC", None)
    if spec is None:
        tool = getattr(module, name)
        spec = getattr(tool, "TOOL_SPEC", None) or getattr(tool, "tool_spec", {})
    description = str(spec.get("description", ""))
    if len(description) > 200:
        description = description[:197].rstrip() + "..."
    return {"name": spec.get("name", name), "description": description}


def tool_list() -> list[dict[str, str]]:
    return [
        _tool_spec(editor, "editor"),
        _tool_spec(shell, "shell"),
        _tool_spec(load_tool, "load_tool"),
    ]


@app.get("/api/agent")
async def get_agent() -> dict[str, Any]:
    return {
        "name": "RandD Live",
        "model": os.getenv("GEMINI_LIVE_MODEL", DEFAULT_MODEL_ID),
        "instructions": SYSTEM_PROMPT,
        "tools": tool_list(),
    }


@app.get("/api/voices")
async def get_voices() -> dict[str, Any]:
    return {"voices": VOICES}


@app.get("/api/workspace")
async def get_workspace() -> dict[str, Any]:
    files = [
        str(path.relative_to(WORKSPACE_DIR))
        for path in WORKSPACE_DIR.rglob("*")
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(WORKSPACE_DIR).parts)
    ]
    return {"files": sorted(files)}


def sanitize(value: Any) -> Any:
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, dict):
        return {str(key): sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize(item) for item in value]
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def normalize_event(event: dict[str, Any], tool_uses: dict[str, dict[str, Any]]) -> dict[str, Any]:
    outgoing = sanitize(dict(event))

    if outgoing.get("type") == "tool_use_stream":
        current = outgoing.get("current_tool_use") or {}
        if isinstance(current, dict):
            tool_use_id = current.get("toolUseId")
            if tool_use_id:
                tool_uses[str(tool_use_id)] = {
                    "name": current.get("name"),
                    "input": current.get("input", {}),
                }

    if outgoing.get("type") == "tool_result":
        result = outgoing.get("tool_result") or {}
        if isinstance(result, dict):
            tool_use_id = result.get("toolUseId")
            prior = tool_uses.get(str(tool_use_id), {}) if tool_use_id else {}
            outgoing["tool_name"] = prior.get("name", "")
            outgoing["tool_input"] = prior.get("input", {})

    if outgoing.get("type") == "bidi_usage":
        outgoing["input_tokens"] = outgoing.get("input_tokens", outgoing.get("inputTokens", 0))
        outgoing["output_tokens"] = outgoing.get("output_tokens", outgoing.get("outputTokens", 0))
        outgoing["total_tokens"] = outgoing.get("total_tokens", outgoing.get("totalTokens", 0))

    return outgoing


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    mode: str = Query("audio", pattern="^(audio|text)$"),
    voice: str = Query("Puck"),
) -> None:
    await websocket.accept()
    agent = create_agent(mode=mode, voice=voice)
    tool_uses: dict[str, dict[str, Any]] = {}

    try:
        await agent.start()

        async def reader() -> None:
            async for raw in websocket.iter_text():
                data = json.loads(raw)
                if isinstance(data, dict) and data.get("type") in {
                    "bidi_text_input",
                    "bidi_audio_input",
                    "bidi_image_input",
                }:
                    await agent.send(data)

        async def writer() -> None:
            async for event in agent.receive():
                outgoing = normalize_event(event, tool_uses)
                await websocket.send_text(json.dumps(outgoing, default=str))

        await asyncio.gather(reader(), writer())
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_text(json.dumps({"type": "bidi_error", "error": str(exc)}))
        except Exception:
            pass
    finally:
        await agent.stop()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
