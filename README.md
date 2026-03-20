# Drafft API

Drafft is a production-oriented, API-first SaaS backend for AI-powered video optimization. It accepts long-form videos and turns them into short-form viral clips with captions, background music, and 9:16 vertical rendering via a modular pipeline powered by Whisper, FFmpeg, and Remotion.

---

## EC2 Deployment Guide

### Architecture Overview

```
Internet
    │
    ▼
Nginx (port 80/443)  ← SSL via Let's Encrypt
    │
    ▼
Uvicorn (port 8000, local only)
    │
    ├── FastAPI routes  → Firebase Auth token verification
    ├── Firestore       → projects, jobs, assets, renders, clips (per-user)
    ├── Local storage   → /srv/drafft/storage/  (video files, renders)
    ├── Whisper         → audio transcription (CPU)
    ├── FFmpeg          → video processing / vertical conversion
    └── Remotion CLI    → Node.js video rendering (Chromium headless)
```

---

### 1. Launch an EC2 Instance

**Recommended specs:**

| Setting | Value |
|---------|-------|
| AMI | Ubuntu 22.04 LTS |
| Instance type | `t3.xlarge` (4 vCPU, 16 GB RAM) minimum |
| Storage | 100 GB gp3 SSD |
| Security group | Inbound: SSH (22), HTTP (80), HTTPS (443) |

---

### 2. Connect and Install System Dependencies

```bash
ssh -i your-key.pem ubuntu@<ec2-public-ip>

sudo apt-get update && sudo apt-get upgrade -y

sudo apt-get install -y \
  python3.12 python3.12-venv python3-pip \
  ffmpeg curl git build-essential \
  nginx certbot python3-certbot-nginx
```

---

### 3. Install Node.js (required for Remotion)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version   # should be v20.x
```

---

### 4. Clone and Set Up the Application

```bash
sudo mkdir -p /srv/drafft && sudo chown ubuntu:ubuntu /srv/drafft
cd /srv/drafft

git clone <your-repo-url> api
cd api

python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install openai-whisper       # not in requirements.txt (large install)

# Install Remotion dependencies
cd remotion_renderer && npm install && cd ..

# Create local storage directory
mkdir -p /srv/drafft/storage
```

---

### 5. Firebase Setup

#### 5a. Enable Firestore in your Firebase project

1. [console.firebase.google.com](https://console.firebase.google.com) → your project
2. **Firestore Database** → Create database → **Native mode** → choose region
3. **Authentication** → ensure Email/Google/etc. providers are enabled (for your frontend)

#### 5b. Generate a service account key

1. Project Settings → **Service accounts** → **Generate new private key**
2. Download `serviceAccountKey.json`
3. Upload to EC2:

```bash
# From your local machine:
scp -i your-key.pem serviceAccountKey.json ubuntu@<ec2-ip>:/srv/drafft/api/
chmod 600 /srv/drafft/api/serviceAccountKey.json
```

#### 5c. Deploy Firestore composite indexes

```bash
npm install -g firebase-tools
firebase login --no-localhost    # follow the URL prompt

cd /srv/drafft/api
firebase deploy --only firestore:indexes --project <your-firebase-project-id>
```

---

### 6. Configure Environment Variables

```bash
nano /srv/drafft/api/.env
```

```env
APP_NAME=Drafft API
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Storage (local filesystem on the EC2 instance)
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=/srv/drafft/storage

# Firebase
FIREBASE_PROJECT_ID=your-firebase-project-id
GOOGLE_APPLICATION_CREDENTIALS=/srv/drafft/api/serviceAccountKey.json
ENABLE_AUTH=true

# AI providers
ENABLE_MOCK_PROVIDERS=false
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4o
ELEVENLABS_API_KEY=sk_...

DEFAULT_STYLE_PRESET=finance_clean
WEBHOOK_TIMEOUT_SECONDS=10
```

> Set `ENABLE_AUTH=false` only for local development or CLI testing. In production
> every request must carry a valid Firebase ID token.

---

### 7. Test the App

```bash
cd /srv/drafft/api
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
```

Open `http://<ec2-public-ip>:8000/docs`. Stop with `Ctrl+C`.

---

### 8. Systemd Service

```bash
sudo nano /etc/systemd/system/drafft-api.service
```

```ini
[Unit]
Description=Drafft API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/srv/drafft/api
Environment="PATH=/srv/drafft/api/.venv/bin:/usr/bin:/bin"
ExecStart=/srv/drafft/api/.venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    --timeout-keep-alive 300
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

> `--workers 1` is intentional — Whisper + Remotion together use ~8–12 GB RAM.
> Multiple workers would OOM a standard instance.

```bash
sudo systemctl daemon-reload
sudo systemctl enable drafft-api
sudo systemctl start drafft-api
sudo systemctl status drafft-api

# Live logs:
sudo journalctl -u drafft-api -f
```

---

### 9. Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/drafft-api
```

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    # Large video uploads
    client_max_body_size 2G;
    client_body_timeout 600s;
    proxy_read_timeout 1200s;
    proxy_send_timeout 1200s;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    # Serve rendered files directly (bypass Python)
    location /storage/ {
        alias /srv/drafft/storage/;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/drafft-api /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

---

### 10. SSL (HTTPS)

> Requires a domain name with an A record pointing to the EC2 IP.

```bash
sudo certbot --nginx -d api.yourdomain.com
sudo certbot renew --dry-run   # verify auto-renewal
```

---

### 11. Frontend Integration

Set your API base URL to `https://api.yourdomain.com/v1`.

All requests must include the Firebase ID token:

```js
const token = await firebase.auth().currentUser.getIdToken();

const res = await fetch('https://api.yourdomain.com/v1/projects', {
  headers: { Authorization: `Bearer ${token}` },
});
```

For real-time job status updates (no polling needed), subscribe directly in Firestore:

```js
import { doc, onSnapshot } from 'firebase/firestore';

onSnapshot(doc(db, 'jobs', jobId), (snap) => {
  const { status, progress_percent, current_step } = snap.data();
  // update UI progress bar in real time
});
```

---

### 12. Updating the App

```bash
cd /srv/drafft/api
git pull
source .venv/bin/activate
pip install -r requirements.txt          # only if changed
cd remotion_renderer && npm install && cd ..  # only if package.json changed
sudo systemctl restart drafft-api
```

---

### 13. Firestore Collections

```
projects/{project_id}     — name, brand settings, user_id
jobs/{job_id}             — status, progress, video urls, settings
clip_candidates/{id}      — title, hook, score, timing, selected
assets/{id}               — any generated/stored file (video, audio, plan)
renders/{id}              — output_url, thumbnail_url, status
transcript_segments/{id}  — text, start_time, end_time
transcript_words/{id}     — word, start_time, end_time
```

---

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `NotFoundError` on startup | Check `FIREBASE_PROJECT_ID` and that Firestore is enabled in Native mode |
| `DefaultCredentialsError` | Verify `GOOGLE_APPLICATION_CREDENTIALS` path is correct |
| `401 Invalid token` | Frontend must send `Authorization: Bearer <idToken>`, not the UID |
| `FAILED_PRECONDITION: indexes not ready` | Run `firebase deploy --only firestore:indexes` and wait ~2 min |
| Large upload fails (413) | Ensure `client_max_body_size 2G` in Nginx config |
| Out of memory | Upgrade to `t3.xlarge` (16 GB) or higher |
| Render timeout | Increase `proxy_read_timeout` in Nginx (pipeline can take 15–20 min) |
