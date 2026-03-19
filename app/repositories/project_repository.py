from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: ProjectCreate) -> Project:
        project = Project(**payload.model_dump())
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get(self, project_id: str) -> Project | None:
        return self.db.get(Project, project_id)

    def list(self) -> list[Project]:
        return self.db.query(Project).order_by(Project.created_at.desc()).all()
