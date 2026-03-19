from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.job_repository import JobRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.job import (
    ClipCandidateResponse,
    JobCreate,
    JobOutputsResponse,
    JobProcessRequest,
    JobResponse,
    TranscriptSegmentResponse,
)
from app.schemas.upload import UploadResponse
from app.services.job_orchestrator_service import JobOrchestratorService
from app.services.storage_service import StorageService

router = APIRouter()


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> JobResponse:
    if not ProjectRepository(db).get(payload.project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    job = JobRepository(db).create(payload)
    return JobResponse.model_validate(job)


@router.get("", response_model=list[JobResponse])
def list_jobs(db: Session = Depends(get_db)) -> list[JobResponse]:
    jobs = JobRepository(db).list()
    return [JobResponse.model_validate(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobResponse:
    job = JobRepository(db).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post("/{job_id}/upload", response_model=UploadResponse)
def upload_video(job_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> UploadResponse:
    repo = JobRepository(db)
    job = repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    stored_path = StorageService().save_upload(job_id, file)
    job.input_video_url = stored_path
    job.status = "uploaded"
    job.current_step = "uploaded"
    job.progress_percent = 5
    db.commit()
    db.refresh(job)
    return UploadResponse(job_id=job.id, filename=file.filename, content_type=file.content_type or "application/octet-stream", stored_path=stored_path)


@router.post("/{job_id}/process", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def process_job(job_id: str, payload: JobProcessRequest, db: Session = Depends(get_db)) -> JobResponse:
    repo = JobRepository(db)
    job = repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    updated = JobOrchestratorService(db).process(job, render_selected_immediately=payload.render_selected_immediately)
    return JobResponse.model_validate(updated)


@router.get("/{job_id}/transcript", response_model=list[TranscriptSegmentResponse])
def get_transcript(job_id: str, db: Session = Depends(get_db)) -> list[TranscriptSegmentResponse]:
    repo = JobRepository(db)
    if not repo.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    segments = repo.transcript(job_id)
    return [TranscriptSegmentResponse.model_validate(segment) for segment in segments]


@router.get("/{job_id}/clips/candidates", response_model=list[ClipCandidateResponse])
def get_clip_candidates(job_id: str, db: Session = Depends(get_db)) -> list[ClipCandidateResponse]:
    repo = JobRepository(db)
    if not repo.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    clips = repo.clip_candidates(job_id)
    return [ClipCandidateResponse.model_validate(clip) for clip in clips]


@router.post("/{job_id}/clips/select", status_code=status.HTTP_200_OK)
def select_clips(job_id: str, clip_ids: list[str], db: Session = Depends(get_db)) -> dict:
    repo = JobRepository(db)
    if not repo.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    clips = repo.clip_candidates(job_id)
    selected = 0
    for clip in clips:
        clip.selected = clip.id in clip_ids
        if clip.selected:
            selected += 1
    db.commit()
    return {"job_id": job_id, "selected_count": selected}


@router.post("/{job_id}/render", status_code=status.HTTP_202_ACCEPTED)
def render_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    repo = JobRepository(db)
    job = repo.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    updated = JobOrchestratorService(db).process(job, render_selected_immediately=True)
    return {"job_id": updated.id, "status": updated.status, "current_step": updated.current_step}


@router.get("/{job_id}/outputs", response_model=JobOutputsResponse)
def get_outputs(job_id: str, db: Session = Depends(get_db)) -> JobOutputsResponse:
    repo = JobRepository(db)
    if not repo.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOutputsResponse(job_id=job_id, outputs=[repo.outputs(job_id)])
