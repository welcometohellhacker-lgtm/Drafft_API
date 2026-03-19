class BrandingService:
    def build_brand_profile(self, project, style_preset: str) -> dict:
        brand_settings = project.brand_settings_json or {}
        return {
            "project_id": project.id,
            "style_preset": style_preset or project.default_style_preset,
            "brand_settings": {
                "primary_color": brand_settings.get("primary_color", "#0A2540"),
                "secondary_color": brand_settings.get("secondary_color", "#FFFFFF"),
                "logo_url": brand_settings.get("logo_url"),
                "font_family": brand_settings.get("font_family", "Inter"),
            },
            "cta_preset": brand_settings.get("cta_preset", "finance_clean_cta"),
        }
