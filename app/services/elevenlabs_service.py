class ElevenLabsService:
    def isolate_voice(self, job_id: str, source_audio_url: str | None, enabled: bool) -> dict | None:
        if not enabled:
            return None
        return {
            "asset_type": "isolated_voice",
            "provider": "elevenlabs",
            "prompt": None,
            "url": f"audio://{job_id}/isolated_voice.wav",
            "metadata_json": {
                "mode": "voice_isolation",
                "source_audio_url": source_audio_url,
                "status": "completed",
            },
        }

    def generate_narration(self, job_id: str, clip_id: str, script: str, enabled: bool) -> dict | None:
        if not enabled:
            return None
        return {
            "asset_type": "narration_audio",
            "provider": "elevenlabs",
            "prompt": script,
            "url": f"audio://{job_id}/{clip_id}/narration.wav",
            "metadata_json": {
                "voice_model": "eleven_multilingual_v2",
                "status": "completed",
                "script": script,
            },
        }
