from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user
from app.db.firebase import FirestoreSession, get_firestore_session
from app.models.render import Render
from app.repositories.job_repository import JobRepository

router = APIRouter()


@router.get("/{job_id}")
def list_renders(
    job_id: str,
    db: FirestoreSession = Depends(get_firestore_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    if not JobRepository(db).get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    renders = db.query_by_job_id(Render, job_id)
    return {
        "job_id": job_id,
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
    }
