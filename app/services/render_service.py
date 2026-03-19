class RenderService:
    def create_render_metadata(self, clip_id: str, aspect_ratio: str) -> dict:
        return {
            "clip_id": clip_id,
            "aspect_ratio": aspect_ratio,
            "engine": "ffmpeg_fallback",
            "supports_remotion": True,
            "status": "queued",
        }

    def build_render_output(self, job_id: str, clip_id: str, aspect_ratio: str, caption_style: str) -> dict:
        return {
            "output_url": f"render://{job_id}/{clip_id}/{aspect_ratio.replace(':', 'x')}.mp4",
            "subtitle_url": f"subtitle://{job_id}.srt",
            "thumbnail_url": f"https://placehold.co/320x568/png?text={clip_id}",
            "metadata_json": {
                "engine": "ffmpeg_fallback",
                "caption_burned_in": True,
                "aspect_ratio": aspect_ratio,
                "caption_style": caption_style,
                "export_format": "mp4",
                "render_mode": "simple_vertical_mvp",
            },
        }
