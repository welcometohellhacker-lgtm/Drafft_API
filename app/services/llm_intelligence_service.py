class LLMIntelligenceService:
    """Planning seam for GPT-5.4-driven creative decisions."""

    MODEL_NAME = "CHATGPT-5.4"

    def choose_creative_direction(self, transcript_segments: list[dict], project_brand: dict | None = None) -> dict:
        transcript_text = " ".join(segment.get("text", "") for segment in transcript_segments).lower()
        energetic = any(word in transcript_text for word in ["mistake", "warning", "secret", "don’t", "wrong"])
        style = "viral_pop" if energetic else "finance_clean"
        palette = {
            "primary": (project_brand or {}).get("primary_color", "#0A2540"),
            "accent": "#00E5A8" if energetic else "#F4B400",
            "text": "#FFFFFF" if energetic else "#F8FAFC",
        }
        return {
            "llm_model": self.MODEL_NAME,
            "caption_style": style,
            "font_family": (project_brand or {}).get("font_family", "Inter"),
            "color_palette": palette,
            "animation_pack": "high_energy_punch" if energetic else "clean_finance_flow",
            "transition_pack": "dynamic_cuts" if energetic else "smooth_fades",
            "cta_style": "strong_cta",
            "reasoning": [
                "selected style from transcript tone",
                "matched color palette to project brand",
                "chose animation intensity based on hook strength",
            ],
        }
