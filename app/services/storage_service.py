from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self.base_path = Path(settings.local_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_upload(self, job_id: str, upload: UploadFile) -> str:
        job_dir = self.base_path / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        target = job_dir / upload.filename
        with target.open("wb") as f:
            f.write(upload.file.read())
        return str(target)
