# Drafft Version Branch Strategy

Drafft is developed progressively across milestone branches:

- `V1` — Core Intelligence MVP
- `V2` — Captions + Simple Rendering
- `V3` — B-roll + Visual Planning
- `V4` — Audio Enhancement + Narration
- `V5` — Full Automated Pipeline

## Rules

1. Finish features on the current milestone branch.
2. Commit each finished feature separately.
3. Merge the completed milestone upward into the next branch.
4. Keep `main` as the integration/default branch.

## V1 Definition of Done

V1 is considered complete when the API can:

- create projects
- create jobs
- upload a video file
- process the job through a mock production-shaped pipeline
- store transcript segments
- generate clip candidates with scores
- return structured JSON through the REST API
- store upload and analysis artifacts for later stages

Rendering is intentionally not required for V1.
