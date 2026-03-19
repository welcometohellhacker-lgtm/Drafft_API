from pathlib import Path
import json

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.base_path = Path(settings.local_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job_id: str) -> Path:
        path = self.base_path / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def clip_dir(self, job_id: str, clip_id: str) -> Path:
        path = self.job_dir(job_id) / 'renders' / clip_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def subtitles_dir(self, job_id: str) -> Path:
        path = self.job_dir(job_id) / 'subtitles'
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_upload(self, job_id: str, upload: UploadFile) -> str:
        target = self.job_dir(job_id) / upload.filename
        with target.open('wb') as f:
            f.write(upload.file.read())
        return str(target)

    def write_text_asset(self, path: Path, content: str) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return str(path)

    def write_json_asset(self, path: Path, payload: dict) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
        return str(path)

    def public_url_for(self, path: Path) -> str:
        rel = path.relative_to(self.base_path)
        return f"/storage/{rel.as_posix()}"
