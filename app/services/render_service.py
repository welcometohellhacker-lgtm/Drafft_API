import subprocess
from pathlib import Path

from app.core.config import settings


class RenderService:
    def create_render_metadata(self, clip_id: str, aspect_ratio: str) -> dict:
        return {
            "clip_id": clip_id,
            "aspect_ratio": aspect_ratio,
            "engine": "ffmpeg_fallback" if settings.enable_mock_providers else "ffmpeg",
            "supports_remotion": True,
            "status": "queued",
        }

    def build_render_output(
        self,
        job_id: str,
        clip_id: str,
        aspect_ratio: str,
        caption_style: str,
        source_path: str | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> dict:
        if settings.enable_mock_providers or not source_path:
            return {
                "output_url": f"render://{job_id}/{clip_id}/{aspect_ratio.replace(':', 'x')}.mp4",
                "subtitle_url": f"subtitle://{job_id}.srt",
                "thumbnail_url": f"https://placehold.co/320x568/png?text={clip_id}",
                "metadata_json": {
                    "engine": "ffmpeg_fallback",
                    "caption_burned_in": False,
                    "aspect_ratio": aspect_ratio,
                    "caption_style": caption_style,
                    "export_format": "mp4",
                    "render_mode": "simple_vertical_mvp",
                },
            }

        storage_dir = Path(settings.local_storage_path) / job_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        out_mp4 = storage_dir / f"{clip_id}.mp4"
        out_thumb = storage_dir / f"{clip_id}_thumb.jpg"

        # Cut and scale clip to 9:16 vertical
        cmd = ["ffmpeg", "-y"]
        if start_time is not None:
            cmd += ["-ss", str(start_time)]
        cmd += ["-i", source_path]
        if end_time is not None and start_time is not None:
            cmd += ["-t", str(end_time - start_time)]
        cmd += [
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        # Extract thumbnail from 1 second in
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(out_mp4), "-ss", "00:00:01", "-vframes", "1", "-q:v", "2", str(out_thumb)],
            capture_output=True,
        )

        base_url = f"/files/{job_id}"
        return {
            "output_url": f"{base_url}/{clip_id}.mp4",
            "subtitle_url": f"subtitle://{job_id}.srt",
            "thumbnail_url": f"{base_url}/{clip_id}_thumb.jpg",
            "metadata_json": {
                "engine": "ffmpeg",
                "caption_burned_in": False,
                "aspect_ratio": aspect_ratio,
                "caption_style": caption_style,
                "export_format": "mp4",
                "render_mode": "simple_vertical_mvp",
            },
        }
