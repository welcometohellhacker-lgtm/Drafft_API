from app.models.asset import Asset
from app.models.clip import ClipCandidate
from app.models.job import Job


class RenderPayloadBuilder:
    def build(self, job: Job, clip: ClipCandidate, assets: list[Asset]) -> dict:
        by_type = {}
        for asset in assets:
            by_type.setdefault(asset.asset_type, []).append(asset)

        def first(asset_type: str, clip_id=None):
            for asset in by_type.get(asset_type, []):
                if clip_id is None or asset.clip_id == clip_id:
                    return asset
            return None

        caption_plan = first('caption_plan', clip.id)
        visual_plan = first('visual_plan', clip.id)
        branding = first('branding_profile')
        isolated_voice = first('isolated_voice')
        narration_audio = first('narration_audio', clip.id)
        audio_mix = first('audio_mix_plan', clip.id)
        generated_images = [a for a in by_type.get('generated_image', []) if a.clip_id == clip.id]

        source_url = job.input_video_url
        clip_duration = max(0.1, clip.end_time - clip.start_time)
        visual_meta = visual_plan.metadata_json if visual_plan else {}
        branding_meta = branding.metadata_json if branding else {}
        caption_meta = caption_plan.metadata_json if caption_plan else {"words": [], "groups": []}

        broll_timeline = []
        base_windows = visual_meta.get('broll_timeline', [])
        for idx, window in enumerate(base_windows):
            image_asset = generated_images[idx] if idx < len(generated_images) else None
            broll_timeline.append({
                **window,
                'asset_url': image_asset.url if image_asset else None,
                'asset_type': image_asset.asset_type if image_asset else 'prompt_only',
            })

        return {
            'jobId': job.id,
            'clipId': clip.id,
            'sourceVideoUrl': source_url,
            'clipStartSec': clip.start_time,
            'clipEndSec': clip.end_time,
            'clipDurationSec': clip_duration,
            'fps': job.fps or 30,
            'composition': {
                'width': job.width or 1080,
                'height': job.height or 1920,
                'aspectRatio': job.requested_platforms_json[0] if job.requested_platforms_json else '9:16',
            },
            'title': clip.title,
            'hook': clip.hook,
            'ctaText': clip.cta_text,
            'captions': {
                'words': caption_meta.get('words', []),
                'groups': caption_meta.get('groups', []),
                'style': caption_meta.get('style', clip.caption_style),
            },
            'visuals': {
                'brollTimeline': broll_timeline,
                'overlayTimeline': visual_meta.get('overlay_timeline', []),
                'transitionTimeline': visual_meta.get('transition_timeline', []),
                'zoomEvents': visual_meta.get('zoom_events', []),
                'thumbnailTextOptions': visual_meta.get('thumbnail_text_options', []),
                'renderNotes': visual_meta.get('render_notes', {}),
            },
            'audio': {
                'sourceAudioUrl': source_url,
                'isolatedVoiceUrl': isolated_voice.url if isolated_voice else None,
                'narrationAudioUrl': narration_audio.url if narration_audio else None,
                'mixPlan': audio_mix.metadata_json if audio_mix else {},
            },
            'branding': branding_meta,
            'fontFamily': ((branding_meta.get('brand_settings', {}) or {}).get('font_family', 'Inter')),
            'colorPalette': {
                'primary': ((branding_meta.get('brand_settings', {}) or {}).get('primary_color', '#0A2540')),
                'accent': '#00E5A8',
                'text': '#FFFFFF',
            },
            'animationPack': visual_meta.get('render_notes', {}).get('style', 'finance_clean'),
            'transitionPack': 'smooth_fades',
        }
