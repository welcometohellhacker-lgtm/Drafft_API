class OutputEnrichmentService:
    def build_social_caption(self, clip_title: str, hook: str, cta_text: str | None) -> dict:
        caption = f"{hook} — {clip_title}."
        if cta_text:
            caption += f" {cta_text}."
        return {
            "social_caption": caption,
            "hashtags": ["#mortgage", "#finance", "#shorts"],
            "thumbnail_notes": ["Use bold rate-lock text", "Show key paperwork visual"],
            "cto_score": 91 if "mistake" in hook.lower() else 83,
        }
