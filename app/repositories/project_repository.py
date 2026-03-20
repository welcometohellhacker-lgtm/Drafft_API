from __future__ import annotations

from app.db.firebase import FirestoreSession
from app.models.project import Project
from app.schemas.project import ProjectCreate


class ProjectRepository:
    def __init__(self, db: FirestoreSession) -> None:
        self.db = db

    def create(self, payload: ProjectCreate, user_id: str | None = None) -> Project:
        project = Project(
            name=payload.name,
            description=payload.description,
            default_style_preset=payload.default_style_preset,
            brand_settings_json=payload.brand_settings_json,
            user_id=user_id,
        )
        self.db.add(project)
        self.db.commit()
        return project

    def get(self, project_id: str) -> Project | None:
        return self.db.get(Project, project_id)

    def list(self, user_id: str | None = None) -> list[Project]:
        q = self.db._db.collection(Project.__tablename__)
        if user_id:
            q = q.where("user_id", "==", user_id)
        docs = q.stream()
        projects = [Project._from_firestore(d.id, d.to_dict()) for d in docs]
        return sorted(projects, key=lambda p: p.created_at, reverse=True)
