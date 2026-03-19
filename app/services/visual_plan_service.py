class VisualPlanService:
    def build(self, clip_id: str, aspect_ratio: str, style: str, broll_prompts: list[str]) -> dict:
        return {
            "clip_id": clip_id,
            "aspect_ratio": aspect_ratio,
            "caption_timeline": [],
            "broll_timeline": [
                {"start": 2.0, "end": 4.5, "prompt": prompt, "motion": "slow_zoom_in"}
                for prompt in broll_prompts
            ],
            "overlay_timeline": [],
            "transition_timeline": [{"type": "fade_in", "start": 0.0, "duration_ms": 400}],
            "zoom_events": [{"start": 1.0, "end": 3.0, "type": "punch_in"}],
            "thumbnail_text_options": [
                "The mortgage mistake everyone makes",
                "Do this before you lock your rate",
            ],
            "render_notes": {"style": style, "fade_in_ms": 400, "fade_out_ms": 400},
        }
