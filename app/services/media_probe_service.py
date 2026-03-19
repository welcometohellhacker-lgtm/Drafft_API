import json
import subprocess
from pathlib import Path

from app.core.config import settings


class MediaProbeService:
    def probe(self, file_path: str) -> dict:
        if settings.enable_mock_providers:
            suffix = Path(file_path).suffix.lower()
            return {
                "duration_seconds": 60,
                "fps": 30,
                "width": 1080,
                "height": 1920,
                "audio_presence": True,
                "file_size": Path(file_path).stat().st_size if Path(file_path).exists() else 0,
                "format": suffix.lstrip("."),
            }

        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-show_format", file_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
        audio_stream = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)

        fps = 30
        if "r_frame_rate" in video_stream:
            num, den = video_stream["r_frame_rate"].split("/")
            fps = round(int(num) / max(int(den), 1))

        return {
            "duration_seconds": float(data["format"].get("duration", 60)),
            "fps": fps,
            "width": int(video_stream.get("width", 1080)),
            "height": int(video_stream.get("height", 1920)),
            "audio_presence": audio_stream is not None,
            "file_size": int(data["format"].get("size", 0)),
            "format": data["format"].get("format_name", "mp4"),
        }
