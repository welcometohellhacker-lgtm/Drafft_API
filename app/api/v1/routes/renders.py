from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.render import Render
from app.repositories.job_repository import JobRepository

router = APIRouter()


@router.get("/{job_id}")
def list_renders(job_id: str, db: Session = Depends(get_db)) -> dict:
    if not JobRepository(db).get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    renders = db.query(Render).filter(Render.job_id == job_id).all()
    return {
        "job_id": job_id,
        "renders": [
            {
                "id": render.id,
                "clip_id": render.clip_id,
                "output_format": render.output_format,
                "output_url": render.output_url,
                "subtitle_url": render.subtitle_url,
                "thumbnail_url": render.thumbnail_url,
                "status": render.status,
                "metadata_json": render.metadata_json,
            }
            for render in renders
        ],
    }
