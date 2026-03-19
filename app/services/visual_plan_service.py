class VisualPlanService:
    def build(self, clip_id: str, aspect_ratio: str, style: str, broll_prompts: list[str], cta_text: str | None = None) -> dict:
        return {
            "clip_id": clip_id,
            "aspect_ratio": aspect_ratio,
            "caption_timeline": [],
            "broll_timeline": [
                {"start": 2.0 + idx * 2.0, "end": 3.5 + idx * 2.0, "prompt": prompt, "motion": "slow_zoom_in"}
                for idx, prompt in enumerate(broll_prompts)
            ],
            "overlay_timeline": [
                {"type": "cta_overlay", "start": 10.0, "end": 13.5, "text": cta_text or "Book a call today", "placement": "bottom_center"},
                {"type": "lower_third", "start": 0.8, "end": 4.0, "text": "Drafft Insight", "placement": "lower_left"},
            ],
            "transition_timeline": [
                {"type": "fade_in", "start": 0.0, "duration_ms": 400},
                {"type": "fade_out", "start": 13.2, "duration_ms": 400},
            ],
            "zoom_events": [{"start": 1.0, "end": 3.0, "type": "punch_in"}],
            "cut_points": [2.0, 6.0, 10.0],
            "thumbnail_text_options": [
                "The mortgage mistake everyone makes",
                "Do this before you lock your rate",
            ],
            "render_notes": {"style": style, "fade_in_ms": 400, "fade_out_ms": 400, "cta_enabled": True},
        }
