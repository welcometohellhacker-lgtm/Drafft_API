from pathlib import Path


class MediaProbeService:
    def probe(self, file_path: str) -> dict:
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
