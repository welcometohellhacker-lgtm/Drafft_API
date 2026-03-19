class CaptionService:
    PRESETS = {
        "kinetic_bold": {
            "font_family": "Inter",
            "font_size_rules": "large",
            "emphasis_rules": ["highlight_keywords"],
            "chunk_length_rules": "short",
            "animation_hints": ["pop", "word_highlight"],
            "placement": "lower_third",
            "shadow_outline": "heavy",
        },
        "premium_minimal": {
            "font_family": "Inter",
            "font_size_rules": "medium",
            "emphasis_rules": ["clean_weight_shift"],
            "chunk_length_rules": "medium",
            "animation_hints": ["fade"],
            "placement": "center_lower",
            "shadow_outline": "light",
        },
        "finance_clean": {
            "font_family": "Inter",
            "font_size_rules": "medium",
            "emphasis_rules": ["numbers_emphasis"],
            "chunk_length_rules": "medium",
            "animation_hints": ["fade", "underline"],
            "placement": "lower_third",
            "shadow_outline": "medium",
        },
        "viral_pop": {
            "font_family": "Anton",
            "font_size_rules": "xlarge",
            "emphasis_rules": ["all_caps_keywords"],
            "chunk_length_rules": "short",
            "animation_hints": ["pop", "bounce"],
            "placement": "center",
            "shadow_outline": "heavy",
        },
        "strong_cta": {
            "font_family": "Inter",
            "font_size_rules": "large",
            "emphasis_rules": ["cta_highlight"],
            "chunk_length_rules": "short",
            "animation_hints": ["slide_up"],
            "placement": "bottom",
            "shadow_outline": "heavy",
        },
    }

    def list_presets(self) -> dict:
        return self.PRESETS
