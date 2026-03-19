class RenderService:
    def create_render_metadata(self, clip_id: str, aspect_ratio: str) -> dict:
        return {
            "clip_id": clip_id,
            "aspect_ratio": aspect_ratio,
            "engine": "ffmpeg_fallback",
            "supports_remotion": True,
            "status": "queued",
        }
