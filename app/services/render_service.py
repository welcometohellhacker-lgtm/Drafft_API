from pathlib import Path

from app.services.remotion_cli_service import RemotionCliService
from app.services.storage_service import StorageService


class RenderService:
    def __init__(self) -> None:
        self.storage = StorageService()
        self.remotion = RemotionCliService(Path(__file__).resolve().parents[2])

    def create_render_metadata(self, clip_id: str, aspect_ratio: str) -> dict:
        return {
            'clip_id': clip_id,
            'aspect_ratio': aspect_ratio,
            'engine': 'remotion_cli',
            'supports_remotion': True,
            'composition': 'VerticalClip',
            'status': 'queued',
        }

    def render_clip(self, job_id: str, clip_id: str, props: dict) -> dict:
        clip_dir = self.storage.clip_dir(job_id, clip_id).resolve()
        props_path = clip_dir / 'input-props.json'
        out_path = clip_dir / 'output.mp4'
        thumb_path = clip_dir / 'thumbnail.png'
        self.storage.write_json_asset(props_path, props)
        clip_duration = float(props.get('clipDurationSec') or 30)
        timeout = max(300, int(clip_duration * 10))  # 10s per clip-second, minimum 5 min
        result = self.remotion.render('VerticalClip', str(props_path), str(out_path), str(thumb_path), timeout_seconds=timeout)
        return {
            'output_url': self.storage.public_url_for(out_path),
            'subtitle_url': self.storage.public_url_for(self.storage.subtitles_dir(job_id) / 'job.srt'),
            'thumbnail_url': self.storage.public_url_for(thumb_path),
            'metadata_json': {
                'engine': 'remotion_cli',
                'caption_burned_in': True,
                'export_format': 'mp4',
                'input_props_path': str(props_path),
                'output_path': str(out_path),
                'thumbnail_path': str(thumb_path),
                'stdout': result['stdout'],
                'stderr': result['stderr'],
                'runtime': result['runtime'],
            },
        }
