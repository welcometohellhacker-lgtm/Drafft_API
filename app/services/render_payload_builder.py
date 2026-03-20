import json
from pathlib import Path

from app.core.config import settings
from app.models.asset import Asset
from app.models.clip import ClipCandidate
from app.models.job import Job
from app.services.storage_service import StorageService


def _normalize_platform(platforms: list) -> str:
    """Extract a clean aspect ratio string like '9:16' from the stored list."""
    raw = platforms[0] if platforms else "9:16"
    if isinstance(raw, str) and raw.startswith("["):
        try:
            parsed = json.loads(raw)
            return parsed[0] if isinstance(parsed, list) and parsed else raw
        except (json.JSONDecodeError, IndexError):
            pass
    return raw


class RenderPayloadBuilder:
    def __init__(self):
        self._storage = StorageService()
        self._api_base = f"http://localhost:{settings.app_port}"

    def _public_url(self, path_str: str | None) -> str | None:
        """Convert any path form to a full http://localhost:PORT/... URL."""
        if not path_str:
            return None
        if path_str.startswith("http://") or path_str.startswith("https://"):
            return path_str
        if path_str.startswith("/"):
            # Already a URL path like /storage/... — just prepend host
            return f"{self._api_base}{path_str}"
        # Reject mock custom-scheme URLs (audio://, image://, etc.)
        if "://" in path_str:
            return None
        try:
            rel_url = self._storage.public_url_for(Path(path_str))
            return f"{self._api_base}{rel_url}"
        except ValueError:
            return None

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
        processed_video = first('processed_video')
        clip_source_video = first('clip_source_video', clip.id)
        background_music = first('background_music')

        source_url = self._public_url(job.input_video_url)
        # Prefer per-clip pre-merged source (multi-segment stitched), else fall back to processed vertical
        if clip_source_video:
            source_url = self._public_url(clip_source_video.url)
        elif processed_video:
            source_url = self._public_url(processed_video.url)
        clip_duration = max(0.1, clip.end_time - clip.start_time)
        visual_meta = visual_plan.metadata_json if visual_plan else {}
        branding_meta = branding.metadata_json if branding else {}
        caption_meta = caption_plan.metadata_json if caption_plan else {"words": [], "groups": []}

        broll_timeline = []
        base_windows = visual_meta.get('broll_timeline', [])
        for idx, window in enumerate(base_windows):
            image_asset = generated_images[idx] if idx < len(generated_images) else None
            raw_url = image_asset.url if image_asset else None
            # Skip mock placeholder URLs that Remotion cannot load
            asset_url = raw_url if raw_url and not raw_url.startswith("image://") else None
            broll_timeline.append({
                **window,
                'asset_url': asset_url,
                'asset_type': image_asset.asset_type if image_asset else 'prompt_only',
            })

        # Inject highlight video clips at visual cut-points
        highlight_clips = [a for a in assets if a.asset_type == "highlight_clip"]
        cut_points = visual_meta.get("cut_points", [])
        for idx, (cut, hc) in enumerate(zip(cut_points, highlight_clips)):
            seg_start = round(max(0.1, cut - 1.2), 3)
            seg_end = round(min(clip_duration - 0.2, cut + 1.8), 3)
            if seg_end > seg_start + 0.5:
                broll_timeline.append({
                    "start": seg_start,
                    "end": seg_end,
                    "prompt": "source highlight",
                    "motion": "slow_zoom_in",
                    "asset_url": self._public_url(hc.url),
                    "asset_type": "highlight_clip",
                })

        aspect_ratio = _normalize_platform(job.requested_platforms_json)
        # Output dimensions must match the requested aspect ratio, not the source video
        if aspect_ratio == '16:9':
            out_w, out_h = 1920, 1080
        elif aspect_ratio == '1:1':
            out_w, out_h = 1080, 1080
        else:  # 9:16 default
            out_w, out_h = 1080, 1920

        # Pre-merged clips always start at 0 in their own file
        effective_start = 0.0 if clip_source_video else clip.start_time
        effective_end = clip_duration if clip_source_video else clip.end_time

        return {
            'jobId': job.id,
            'clipId': clip.id,
            'sourceVideoUrl': source_url,
            'clipStartSec': effective_start,
            'clipEndSec': effective_end,
            'clipDurationSec': clip_duration,
            'fps': job.fps or 30,
            'composition': {
                'width': out_w,
                'height': out_h,
                'aspectRatio': aspect_ratio,
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
                'isolatedVoiceUrl': self._public_url(isolated_voice.url) if isolated_voice else None,
                'narrationAudioUrl': self._public_url(narration_audio.url) if narration_audio else None,
                'backgroundMusicUrl': self._public_url(background_music.url) if background_music else None,
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
