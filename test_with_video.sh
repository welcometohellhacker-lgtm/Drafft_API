#!/usr/bin/env bash
set -euo pipefail

VIDEO="${1:-Input.mp4}"
HOST="http://localhost:8000"
SERVER_PID=""

# ── helpers ──────────────────────────────────────────────────────────────────
log()  { echo "▶ $*"; }
ok()   { echo "✔ $*"; }
fail() { echo "✘ $*" >&2; exit 1; }

cleanup() {
  if [[ -n "$SERVER_PID" ]]; then
    log "Stopping server (PID $SERVER_PID)..."
    kill "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# ── preflight ─────────────────────────────────────────────────────────────────
[[ -f "$VIDEO" ]] || fail "Video file not found: $VIDEO  (usage: $0 <path/to/video.mp4>)"
command -v curl    &>/dev/null || fail "curl is required"
command -v python3 &>/dev/null || fail "python3 is required"

# ── start server if not already running ──────────────────────────────────────
if curl -sf "$HOST/" &>/dev/null; then
  ok "Server already running at $HOST"
else
  log "Starting uvicorn server..."
  python3 -m uvicorn app.main:app --port 8000 --log-level info &
  SERVER_PID=$!
  # Wait up to 10s for the server to be ready
  for i in {1..20}; do
    curl -sf "$HOST/" &>/dev/null && break
    sleep 0.5
  done
  curl -sf "$HOST/" &>/dev/null || fail "Server did not start in time"
  ok "Server started (PID $SERVER_PID)"
fi

# ── create project ────────────────────────────────────────────────────────────
log "Creating project..."
PROJECT_RESP=$(curl -sf -X POST "$HOST/v1/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Project",
    "default_style_preset": "finance_clean",
    "brand_settings_json": {"primary_color": "#0A2540"}
  }')
PROJECT_ID=$(echo "$PROJECT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
ok "Project created: $PROJECT_ID"

# ── ultimate-clips (full auto flow) ──────────────────────────────────────────
log "Uploading '$VIDEO' and running ultimate-clips pipeline..."
RESULT=$(curl -sf -X POST "$HOST/v1/ultimate-clips" \
  -F "project_id=$PROJECT_ID" \
  -F "requested_clip_count=2" \
  -F "user_instructions=Focus on the strongest moments." \
  -F "narration_enabled=false" \
  -F "broll_enabled=true" \
  -F "file=@$VIDEO")

# ── print summary ─────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════"
echo " RESULT SUMMARY"
echo "══════════════════════════════════════════"
STORAGE_BASE="$(pwd)/storage"
echo "$RESULT" | python3 -c "
import sys, json, os
body = json.load(sys.stdin)
storage_base = os.environ.get('STORAGE_BASE', './storage')
print(f'  Job ID       : {body.get(\"job_id\", \"—\")}')
print(f'  Style        : {body.get(\"selected_style\", \"—\")}')
print(f'  LLM Model    : {body.get(\"llm_model\", \"—\")}')
print(f'  CTO Score    : {body.get(\"cto_score\", \"—\")}')
gallery = body.get('gallery', [])
print(f'  Clips        : {len(gallery)}')
for i, clip in enumerate(gallery, 1):
    rel = (clip.get('download_url') or '').lstrip('/storage/')
    fs_path = os.path.join(storage_base, rel) if rel else '—'
    thumb_rel = (clip.get('thumbnail_url') or '').lstrip('/storage/')
    thumb_path = os.path.join(storage_base, thumb_rel) if thumb_rel else '—'
    print(f'  [{i}] {clip.get(\"clip_id\",\"?\")[:8]}...')
    print(f'       Video  : {fs_path}')
    print(f'       Thumb  : {thumb_path}')
    print(f'       Caption: {(clip.get(\"social_caption\") or \"\")[:80]}')
    exists = os.path.exists(fs_path)
    size   = os.path.getsize(fs_path) // 1024 // 1024 if exists else 0
    print(f'       File OK: {exists}  ({size} MB)')
" STORAGE_BASE="$STORAGE_BASE"
echo ""
echo "Full JSON saved to: result.json"
echo "$RESULT" | python3 -m json.tool > result.json
