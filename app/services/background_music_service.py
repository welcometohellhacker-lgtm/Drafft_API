import logging
import shutil
import subprocess

import httpx

from app.core.config import settings
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

_STYLE_PROMPTS: dict[str, str] = {
    "viral_pop": "upbeat energetic pop background music, electronic beat, trendy, high energy, no vocals",
    "kinetic_bold": "powerful cinematic background music, driving rhythm, motivational, intense, no vocals",
    "strong_cta": "confident persuasive background music, building energy, corporate, no vocals",
    "premium_minimal": "soft minimal ambient background music, elegant piano, luxury, no vocals",
    "finance_clean": "calm professional corporate background music, subtle ambient, trustworthy, no vocals",
}


class BackgroundMusicService:
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self) -> None:
        self.api_key = settings.elevenlabs_api_key
        self.storage = StorageService()

    def generate(self, job_id: str, style: str, clip_duration: float) -> dict | None:
        if not self.api_key:
            logger.info("No ElevenLabs API key — skipping background music")
            return None

        prompt = _STYLE_PROMPTS.get(style, _STYLE_PROMPTS["finance_clean"])
        # ElevenLabs sound-generation max is 22s; we loop in Remotion for longer clips
        duration = round(min(22.0, max(5.0, clip_duration)), 1)

        try:
            resp = httpx.post(
                f"{self.BASE_URL}/sound-generation",
                headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
                json={"text": prompt, "duration_seconds": duration, "prompt_influence": 0.3},
                timeout=90.0,
            )
            if resp.status_code != 200:
                logger.warning(
                    "ElevenLabs sound-generation returned %d: %s",
                    resp.status_code, resp.text[:400],
                )
                return None

            mp3_path = self.storage.job_dir(job_id) / "background_music.mp3"
            mp3_path.write_bytes(resp.content)
            logger.info("Background music saved: %s (%d bytes)", mp3_path, len(resp.content))

            # Convert MP3 → WebM/Opus so Chromium (Remotion's renderer) can always decode it.
            # Open-source Chromium builds on Linux don't support MP3 due to licensing.
            # WebM/Opus is royalty-free and natively supported on all platforms.
            serve_path = mp3_path
            ffmpeg = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
            webm_path = self.storage.job_dir(job_id) / "background_music.webm"
            conv = subprocess.run(
                [ffmpeg, "-y", "-i", str(mp3_path), "-c:a", "libopus", "-b:a", "128k", str(webm_path)],
                capture_output=True, text=True, timeout=60,
            )
            if conv.returncode == 0:
                serve_path = webm_path
                logger.info("Background music converted to WebM/Opus: %s", webm_path)
            else:
                logger.warning("WebM conversion failed, serving MP3 (may not work in Chromium): %s", conv.stderr[-300:])

            return {
                "asset_type": "background_music",
                "provider": "elevenlabs_sound_generation",
                "prompt": prompt,
                "url": self.storage.public_url_for(serve_path),
                "metadata_json": {"style": style, "duration_seconds": duration, "prompt": prompt},
            }
        except Exception as exc:
            logger.error("Background music generation failed: %s", exc)
            return None
