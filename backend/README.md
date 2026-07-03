# RandD Live Backend

```bash
cd backend
python3 -m venv .backend-venv
. .backend-venv/bin/activate
pip install -r requirements.txt
export GOOGLE_API_KEY=your_google_api_key
uvicorn app.main:app --reload --port 8000
```

The server exposes `/api/agent`, `/api/voices`, `/api/workspace`, static workspace files at `/workspace/*`, and the live bridge at `/ws?mode=audio|text&voice=Puck`.
