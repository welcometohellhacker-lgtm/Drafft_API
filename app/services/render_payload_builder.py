from app.models.asset import Asset
from app.models.clip import ClipCandidate
from app.models.job import Job


class RenderPayloadBuilder:
    def build(self, job: Job, clip: ClipCandidate, assets: list[Asset]) -> dict:
        by_type = {}
        for asset in assets:
            by_type.setdefault(asset.asset_type, []).append(asset)
        caption_plan = next((a for a in by_type.get('caption_plan', []) if a.clip_id == clip.id), None)
        visual_plan = next((a for a in by_type.get('visual_plan', []) if a.clip_id == clip.id), None)
        branding = next((a for a in by_type.get('branding_profile', [])), None)
        return {
            'title': clip.title,
            'hook': clip.hook,
            'ctaText': clip.cta_text,
            'aspectRatio': job.requested_platforms_json[0] if job.requested_platforms_json else '9:16',
            'captionGroups': (caption_plan.metadata_json or {}).get('groups', []) if caption_plan else [],
            'brollTimeline': (visual_plan.metadata_json or {}).get('broll_timeline', []) if visual_plan else [],
            'overlayTimeline': (visual_plan.metadata_json or {}).get('overlay_timeline', []) if visual_plan else [],
            'thumbnailTextOptions': (visual_plan.metadata_json or {}).get('thumbnail_text_options', []) if visual_plan else [],
            'branding': branding.metadata_json if branding else {},
            'colorPalette': {
                'primary': ((branding.metadata_json if branding else {}).get('brand_settings', {}) or {}).get('primary_color', '#0A2540'),
                'accent': '#00E5A8',
                'text': '#FFFFFF',
            },
            'animationPack': 'clean_finance_flow',
            'transitionPack': 'smooth_fades',
            'fontFamily': ((branding.metadata_json if branding else {}).get('brand_settings', {}) or {}).get('font_family', 'Inter'),
        }
