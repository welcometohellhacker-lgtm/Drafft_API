# Remotion + Drafft API (REMOTION_TEST)

This tree is a **FastAPI + Remotion CLI** pipeline. Common reasons it “doesn’t work”:

## 1. `ENABLE_MOCK_PROVIDERS=true` (recommended for tests / CI)

When this is set, the API **does not** run Node/Remotion. It generates a valid placeholder MP4 with **ffmpeg** instead.

- Avoids: missing Node, Chromium bundle issues, and Remotion trying to `fetch()` `http://localhost:8000/storage/...` while **pytest** is using an in-process client (nothing is listening on port 8000).

```bash
export ENABLE_MOCK_PROVIDERS=true
pytest
```

## 2. Real Remotion renders (`ENABLE_MOCK_PROVIDERS=false`)

Requirements:

- **Node 18+** and `npm install` inside `remotion_renderer/`
- **`render.mjs`** present (already in repo)
- **ffmpeg** and **ffprobe** on `PATH`
- API must be reachable at the same host/port used in `RenderPayloadBuilder` (default `http://localhost:8000`), because Remotion loads `sourceVideoUrl` over HTTP.

```bash
cd remotion_renderer && npm ci && cd ..
cp .env.example .env   # set APP_PORT=8000 to match
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 3. Windows vs WSL

If you run **uvicorn on Windows** but **Node/ffmpeg inside WSL**, paths and `localhost` bridging often break. Prefer **one environment** for API + ffmpeg + node (all WSL or all native Windows).

## 4. ElevenLabs music

Background music is generated only when `ELEVENLABS_API_KEY` is set. Without a key, music is skipped (clips still render).
