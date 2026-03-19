# Drafft_API

Drafft is a production-oriented, API-first SaaS backend for AI-powered video optimization in mortgage, insurance, and financial services.

It accepts long-form videos and turns them into short-form clip candidates, caption plans, visual plans, optional AI assets, and render-ready outputs through a modular pipeline.

## Product Scope

Final target: **Version 5**.

### Version 1 — Core Intelligence MVP
- Create jobs
- Upload videos
- Preprocess media metadata
- Generate transcript data through a provider abstraction
- Analyze transcript and return clip candidates as structured JSON
- Persist upload, transcript, visual-plan, and clip-candidate artifacts

### Version 2 — Captions + Simple Rendering
- Subtitle generation artifacts (SRT/VTT)
- Clip-level caption grouping metadata
- Simple rendered output workflow for 9:16 clips
- Burned-in caption render metadata
- Render listing endpoint

### Version 3 — B-roll + Visual Planning
- Dedicated B-roll planning artifacts with insertion windows
- Expanded visual plan JSON with overlays, cuts, and CTA metadata
- Generated image asset flow for B-roll stills
- Thumbnail text ideas

### Version 4 — Audio Enhancement + Narration
- ElevenLabs provider abstraction
- voice isolation seam
- Speech cleanup / isolation seam
- Narration planning and audio mix seam

### Version 5 — Full Automated Pipeline
- Async orchestration
- Reusable styles and branding presets
- Render queue
- Outputs metadata
- Thumbnails
- Social caption suggestions
- Webhooks
- Retries and error handling

## Tech Stack
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PostgreSQL-ready schema
- Redis-ready worker seam
- FFmpeg-ready processing seam
- Docker / docker-compose

## Current State
This repo ships a production-shaped backend scaffold with:
- `/v1` REST API
- typed schemas
- SQLAlchemy models
- initial Alembic migration
- modular services
- local storage abstraction
- mock orchestration for internal testing
- Docker support
- `.env.example`
- basic test

## API Endpoints

### Jobs
- `POST /v1/jobs`
- `GET /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `POST /v1/jobs/{job_id}/upload`
- `POST /v1/jobs/{job_id}/process`
- `GET /v1/jobs/{job_id}/transcript`
- `GET /v1/jobs/{job_id}/clips/candidates`
- `POST /v1/jobs/{job_id}/clips/select`
- `POST /v1/jobs/{job_id}/render`
- `GET /v1/jobs/{job_id}/outputs`

### Projects
- `POST /v1/projects`
- `GET /v1/projects`
- `GET /v1/projects/{project_id}`
- `GET /v1/projects/{project_id}/jobs`

### Platform helpers
- `GET /v1/health`
- `GET /v1/style-presets`
- `POST /v1/assets/generate-image`
- `POST /v1/assets/generate-voice`
- `POST /v1/webhooks/test`

## Run Locally

### 1. Environment
```bash
cp .env.example .env
```

### 2. Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run migrations
```bash
alembic upgrade head
```

### 4. Start API
```bash
uvicorn app.main:app --reload
```

### 5. Run tests
```bash
pytest
```

## Docker
```bash
docker compose up --build
```

## Architecture Notes

### Service modules
- `storage_service`
- `media_probe_service`
- `transcription_service`
- `transcript_intelligence_service`
- `caption_service`
- `visual_plan_service`
- `render_service`
- `webhook_service`
- `job_orchestrator_service`

### Important design decisions
- provider seams are abstracted so transcription, LLM, image generation, and voice services can be swapped later
- orchestration is intentionally lightweight now, but structured to move cleanly to Celery, Temporal, or Inngest later
- visual plan JSON is stored as an asset artifact to stabilize the planning → rendering contract early
- render pipeline is currently a placeholder seam, not a full media renderer yet

## Recommended Next Steps
1. Replace mock transcription with Whisper/OpenAI abstraction
2. Add Celery or Temporal-backed async execution
3. Implement FFmpeg clip cutting + subtitle exports
4. Add presigned upload flow + S3 storage backend
5. Add auth, tenancy, and project-level permissions
6. Add provider-specific ElevenLabs and image generation integrations

## Branching Strategy
- `V1` through `V5` are milestone branches
- finished features are committed incrementally on the active milestone branch
- completed milestones are merged upward progressively
- see `docs/VERSIONING.md` for the release flow
