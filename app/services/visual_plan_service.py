class VisualPlanService:
    def build(self, clip_id: str, aspect_ratio: str, style: str, broll_prompts: list[str], cta_text: str | None = None, clip_duration: float = 15.0) -> dict:
        intro_end = min(2.2, clip_duration * 0.22)
        cta_start = max(clip_duration * 0.78, clip_duration - 3.0)
        broll_timeline = []
        for idx, prompt in enumerate(broll_prompts[:3]):
            start = min(clip_duration - 1.0, 1.5 + idx * max(1.6, clip_duration * 0.14))
            end = min(clip_duration - 0.2, start + max(1.2, clip_duration * 0.16))
            broll_timeline.append(
                {
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "prompt": prompt,
                    "motion": "slow_zoom_in" if style in {"finance_clean", "premium_minimal"} else "parallax_push",
                }
            )

        overlay_timeline = [
            {"type": "lower_third", "start": 0.4, "end": round(intro_end, 3), "text": "Drafft Insight", "placement": "lower_left"},
            {"type": "cta_overlay", "start": round(cta_start, 3), "end": round(min(clip_duration, cta_start + 2.4), 3), "text": cta_text or "Book a call today", "placement": "bottom_center"},
        ]

        transition_timeline = [
            {"type": "fade_in", "start": 0.0, "duration_ms": 320},
            {"type": "flash_cut" if style in {"viral_pop", "kinetic_bold", "strong_cta"} else "fade_out", "start": round(max(0.0, clip_duration - 0.5), 3), "duration_ms": 320},
        ]

        zoom_events = [
            {"start": 0.2, "end": round(min(1.3, clip_duration), 3), "type": "hook_punch_in"},
            {"start": round(max(0.0, clip_duration * 0.42), 3), "end": round(min(clip_duration, clip_duration * 0.58), 3), "type": "emphasis_push"},
        ]

        style_profiles = {
            "viral_pop": {"caption_energy": "high", "background_fx": "glow_burst", "cta_variant": "aggressive"},
            "kinetic_bold": {"caption_energy": "high", "background_fx": "speed_lines", "cta_variant": "bold"},
            "strong_cta": {"caption_energy": "medium_high", "background_fx": "contrast_pulse", "cta_variant": "sales"},
            "premium_minimal": {"caption_energy": "low", "background_fx": "soft_gradient", "cta_variant": "clean"},
            "finance_clean": {"caption_energy": "medium", "background_fx": "clean_grid", "cta_variant": "trust"},
        }

        return {
            "clip_id": clip_id,
            "aspect_ratio": aspect_ratio,
            "broll_timeline": broll_timeline,
            "overlay_timeline": overlay_timeline,
            "transition_timeline": transition_timeline,
            "zoom_events": zoom_events,
            "cut_points": [round(min(clip_duration - 0.2, p), 3) for p in [clip_duration * 0.24, clip_duration * 0.51, clip_duration * 0.74] if p < clip_duration],
            "thumbnail_text_options": [
                "The mistake most buyers make",
                "Watch this before you decide",
                "One move that changes everything",
            ],
            "render_notes": {
                "style": style,
                "fade_in_ms": 320,
                "fade_out_ms": 320,
                "cta_enabled": True,
                **style_profiles.get(style, style_profiles["finance_clean"]),
            },
        }
