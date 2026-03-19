from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.clip import ClipCandidate
from app.models.job import Job
from app.models.render import Render
from app.models.transcript import TranscriptSegment
from app.schemas.job import JobCreate


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: JobCreate) -> Job:
        job = Job(**payload.model_dump())
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self.db.get(Job, job_id)

    def list(self) -> list[Job]:
        return self.db.query(Job).order_by(Job.created_at.desc()).all()

    def list_for_project(self, project_id: str) -> list[Job]:
        return self.db.query(Job).filter(Job.project_id == project_id).order_by(Job.created_at.desc()).all()

    def transcript(self, job_id: str) -> list[TranscriptSegment]:
        return self.db.query(TranscriptSegment).filter(TranscriptSegment.job_id == job_id).order_by(TranscriptSegment.start_time.asc()).all()

    def clip_candidates(self, job_id: str) -> list[ClipCandidate]:
        return self.db.query(ClipCandidate).filter(ClipCandidate.job_id == job_id).order_by(ClipCandidate.score.desc()).all()

    def outputs(self, job_id: str) -> list[dict]:
        renders = self.db.query(Render).filter(Render.job_id == job_id).all()
        assets = self.db.query(Asset).filter(Asset.job_id == job_id).all()
        return {
            "renders": [
                {
                    "id": r.id,
                    "clip_id": r.clip_id,
                    "output_format": r.output_format,
                    "output_url": r.output_url,
                    "subtitle_url": r.subtitle_url,
                    "thumbnail_url": r.thumbnail_url,
                    "status": r.status,
                    "metadata_json": r.metadata_json,
                }
                for r in renders
            ],
            "assets": [
                {
                    "id": a.id,
                    "clip_id": a.clip_id,
                    "asset_type": a.asset_type,
                    "provider": a.provider,
                    "url": a.url,
                    "metadata_json": a.metadata_json,
                }
                for a in assets
            ],
        }
