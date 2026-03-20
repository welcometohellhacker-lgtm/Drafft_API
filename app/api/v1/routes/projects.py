from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.db.firebase import FirestoreSession, get_firestore_session
from app.repositories.job_repository import JobRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.job import JobResponse
from app.schemas.project import ProjectCreate, ProjectResponse

router = APIRouter()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: FirestoreSession = Depends(get_firestore_session),
    current_user: dict = Depends(get_current_user),
) -> ProjectResponse:
    project = ProjectRepository(db).create(payload, user_id=current_user["uid"])
    return ProjectResponse.model_validate(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: FirestoreSession = Depends(get_firestore_session),
    current_user: dict = Depends(get_current_user),
) -> list[ProjectResponse]:
    projects = ProjectRepository(db).list(user_id=current_user["uid"])
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: FirestoreSession = Depends(get_firestore_session),
    current_user: dict = Depends(get_current_user),
) -> ProjectResponse:
    project = ProjectRepository(db).get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}/jobs", response_model=list[JobResponse])
def get_project_jobs(
    project_id: str,
    db: FirestoreSession = Depends(get_firestore_session),
    current_user: dict = Depends(get_current_user),
) -> list[JobResponse]:
    jobs = JobRepository(db).list_for_project(project_id)
    return [JobResponse.model_validate(j) for j in jobs]
