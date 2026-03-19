class AudioMixService:
    def build_mix_plan(self, clip_id: str, narration_enabled: bool, isolated_voice_enabled: bool) -> dict:
        return {
            "clip_id": clip_id,
            "speech_track": "isolated_voice" if isolated_voice_enabled else "original_audio",
            "narration_track": "narration_audio" if narration_enabled else None,
            "background_music": {
                "enabled": True,
                "duck_under_speech_db": -14,
                "fade_in_ms": 250,
                "fade_out_ms": 400,
            },
            "normalization": {
                "target_lufs": -14,
                "peak_limit_db": -1,
            },
            "mix_notes": [
                "duck music during speech",
                "normalize final loudness",
                "preserve speech clarity for short-form delivery",
            ],
        }
