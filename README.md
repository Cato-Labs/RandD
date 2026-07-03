# RandD

## AI Chat (Gemini Live) — AI Elements frontend + Strands bidi backend

Live text + voice chat UI built entirely from [Vercel AI Elements](https://github.com/vercel/ai-elements)
components, driven by the repo-vendored Strands bidi agent (`strands-py/`) running
**gemini-3.1-flash-live-preview** with exactly three tools: `editor`, `shell`, `load_tool`
(meta-tooling: the agent creates new tools with the editor and hot-loads them with `load_tool`).
See `DESIGN.md` for the full component plan and architecture.

### Run

Backend (needs a real `GOOGLE_API_KEY` for Gemini Live):

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export GOOGLE_API_KEY=your-key
.venv/bin/uvicorn app.main:app --port 8000
```

Frontend (proxies `/api`, `/ws`, `/workspace` to the backend):

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Test

1. Open http://localhost:5173, pick a voice (VoiceSelector) and mic (MicSelector), press **Connect**.
2. Voice: click **Mic** and speak — persona animates, transcripts stream, model audio plays and is
   replayable per turn via the AudioPlayer.
3. Text: type in the prompt input (attach images by drag-drop/paste); responses stream as markdown.
4. Meta-tooling: say/type *"create a tool that reverses text, then use it on 'hello'"* — watch
   Chain of Thought, Tool, Sandbox (shell), the Agent panel tool list, and the workspace
   artifacts/web-preview update from live events. Toggle **Workflow** for the live session graph.
5. Frontend build check: `cd frontend && npm run build`. Backend import check:
   `cd backend && GOOGLE_API_KEY=dummy .venv/bin/python -c "from app.main import app"`.

Sync vendored AI Elements from upstream (or a fork) at any time:

```bash
./scripts/sync-ai-elements.sh                 # vercel/ai-elements@main
AI_ELEMENTS_REPO=ImRonAI/ai-elements ./scripts/sync-ai-elements.sh
```

## Phase 1 STR QC artifacts

Phase 1 STR QC kickoff artifacts:

- Schema: `/home/runner/work/RandD/RandD/sql/phase1_schema.sql`
- Architecture diagrams (ERD + state machine): `/home/runner/work/RandD/RandD/docs/phase1_architecture.md`
- Migration script: `/home/runner/work/RandD/RandD/scripts/migrate_phase1.py`

## Migration usage

```bash
python /home/runner/work/RandD/RandD/scripts/migrate_phase1.py \
  --master-csv /absolute/path/master.csv \
  --roster-csv /absolute/path/roster.csv \
  --db-path /absolute/path/str_qc.sqlite \
  --fail-on-error
```

Notes:
- The migration enables `PRAGMA foreign_keys=ON` on its connection and the schema also declares it.
- Plaintext secrets found in CSV inputs (for example WiFi password/door code) are surfaced as migration issues and are not stored as raw values.
