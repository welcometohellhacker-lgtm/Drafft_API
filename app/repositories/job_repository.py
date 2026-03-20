from __future__ import annotations

from app.db.firebase import FirestoreSession
from app.models.asset import Asset
from app.models.clip import ClipCandidate
from app.models.job import Job
from app.models.project import Project
from app.models.render import Render
from app.models.transcript import TranscriptSegment
from app.schemas.job import JobCreate


class JobRepository:
    def __init__(self, db: FirestoreSession) -> None:
        self.db = db

    def create(self, payload: JobCreate, user_id: str | None = None) -> Job:
        job = Job(
            project_id=payload.project_id,
            user_id=user_id,
            requested_platforms_json=payload.requested_platforms_json,
            requested_clip_count=payload.requested_clip_count,
            user_instructions=payload.user_instructions,
            narration_enabled=payload.narration_enabled,
            broll_enabled=payload.broll_enabled,
            style_preset=payload.style_preset,
        )
        self.db.add(job)
        self.db.commit()
        # Eagerly attach project
        job.project = self.db.get(Project, job.project_id)
        return job

    def get(self, job_id: str) -> Job | None:
        job = self.db.get(Job, job_id)
        if job is None:
            return None
        # Eagerly load project for orchestrator use
        job.project = self.db.get(Project, job.project_id)
        return job

    def list(self, user_id: str | None = None) -> list[Job]:
        q = self.db._db.collection(Job.__tablename__)
        if user_id:
            q = q.where("user_id", "==", user_id)
        jobs = [Job._from_firestore(d.id, d.to_dict()) for d in q.stream()]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def list_for_project(self, project_id: str) -> list[Job]:
        docs = (
            self.db._db.collection(Job.__tablename__)
            .where("project_id", "==", project_id)
            .stream()
        )
        jobs = [Job._from_firestore(d.id, d.to_dict()) for d in docs]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def transcript(self, job_id: str) -> list[TranscriptSegment]:
        segs = self.db.query_by_job_id(TranscriptSegment, job_id)
        return sorted(segs, key=lambda s: s.start_time)

    def clip_candidates(self, job_id: str) -> list[ClipCandidate]:
        clips = self.db.query_by_job_id(ClipCandidate, job_id)
        return sorted(clips, key=lambda c: c.score, reverse=True)

    def outputs(self, job_id: str) -> dict:
        renders = self.db.query_by_job_id(Render, job_id)
        assets = self.db.query_by_job_id(Asset, job_id)
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
