import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.auth import get_current_user
from app.db.firebase import FirestoreSession, get_firestore_session
from app.models.asset import Asset
from app.repositories.job_repository import JobRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.job import JobCreate
from app.schemas.ultimate_clips import UltimateClipsResponse
from app.services.job_orchestrator_service import JobOrchestratorService
from app.services.llm_intelligence_service import LLMIntelligenceService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=UltimateClipsResponse, status_code=status.HTTP_201_CREATED)
def create_ultimate_clip_job(
    project_id: str = Form(...),
    requested_clip_count: int = Form(3),
    user_instructions: str | None = Form(None),
    narration_enabled: bool = Form(True),
    broll_enabled: bool = Form(True),
    file: UploadFile = File(...),
    db: FirestoreSession = Depends(get_firestore_session),
    current_user: dict = Depends(get_current_user),
) -> UltimateClipsResponse:
    project = ProjectRepository(db).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    planner = LLMIntelligenceService()
    creative = planner.choose_creative_direction([], project.brand_settings_json)

    job = JobRepository(db).create(
        JobCreate(
            project_id=project_id,
            requested_platforms_json=["9:16"],
            requested_clip_count=requested_clip_count,
            user_instructions=user_instructions,
            narration_enabled=narration_enabled,
            broll_enabled=broll_enabled,
            style_preset=creative["caption_style"],
        ),
        user_id=current_user["uid"],
    )

    stored_path = StorageService().save_upload(job.id, file)
    logger.info("[job=%s] video uploaded → %s (%.1f MB)", job.id, stored_path,
                (file.size or 0) / 1_048_576)
    job.input_video_url = stored_path
    job.status = "uploaded"
    job.current_step = "uploaded"
    job.progress_percent = 5
    db.add(job)
    db.add(Asset(
        job_id=job.id,
        clip_id=None,
        asset_type="source_video",
        provider="local_storage",
        prompt=None,
        url=stored_path,
        metadata_json={"filename": file.filename, "content_type": file.content_type},
    ))
    db.add(Asset(
        job_id=job.id,
        clip_id=None,
        asset_type="ultimate_clips_plan",
        provider="llm_intelligence_service",
        prompt=user_instructions,
        url=f"ultimate://{job.id}",
        metadata_json=creative,
    ))
    db.commit()
    db.refresh(job)

    logger.info("[job=%s] handing off to JobOrchestratorService.process() …", job.id)
    updated = JobOrchestratorService(db).process(job, render_selected_immediately=True, regenerate_transcript=False)

    assets = db.query_by_job_id(Asset, updated.id)
    renders = [a for a in assets if a.asset_type == "rendered_clip"]
    thumbnails = {a.clip_id: a for a in assets if a.asset_type == "thumbnail"}
    social = {a.clip_id: a for a in assets if a.asset_type == "social_caption"}

    gallery = []
    for render in renders:
        social_asset = social.get(render.clip_id)
        gallery.append({
            "clip_id": render.clip_id,
            "download_url": render.url,
            "thumbnail_url": thumbnails[render.clip_id].url if render.clip_id in thumbnails else None,
            "social_caption": social_asset.metadata_json.get("social_caption") if social_asset else None,
            "cto_score": social_asset.metadata_json.get("cto_score") if social_asset else creative.get("cto_score", 80),
        })

    return UltimateClipsResponse(
        job_id=updated.id,
        status=updated.status,
        current_step=updated.current_step,
        progress_percent=updated.progress_percent,
        llm_model=creative["llm_model"],
        selected_style=creative["caption_style"],
        cto_score=creative.get("cto_score", 80),
        gallery=gallery,
    )
