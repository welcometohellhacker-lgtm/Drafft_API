import io
import os
import tempfile
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test_drafft.db"
os.environ["LOCAL_STORAGE_PATH"] = tempfile.mkdtemp(prefix="drafft-storage-")

from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DB_URL = "sqlite:///./test_drafft.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_v1_end_to_end_flow() -> None:
    project = client.post(
        "/v1/projects",
        json={
            "name": "Drafft Internal Testing",
            "description": "Mortgage marketing pilot",
            "default_style_preset": "finance_clean",
            "brand_settings_json": {"primary_color": "#0A2540"},
        },
    )
    assert project.status_code == 201
    project_id = project.json()["id"]

    job = client.post(
        "/v1/jobs",
        json={
            "project_id": project_id,
            "requested_platforms_json": ["9:16"],
            "requested_clip_count": 2,
            "user_instructions": "Focus on mortgage mistakes and rate lock timing.",
            "narration_enabled": False,
            "broll_enabled": True,
            "style_preset": "finance_clean",
        },
    )
    assert job.status_code == 201
    job_id = job.json()["id"]

    upload = client.post(
        f"/v1/jobs/{job_id}/upload",
        files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")},
    )
    assert upload.status_code == 200

    process = client.post(
        f"/v1/jobs/{job_id}/process",
        json={"regenerate_transcript": False, "render_selected_immediately": False},
    )
    assert process.status_code == 202
    assert process.json()["status"] == "completed"

    transcript = client.get(f"/v1/jobs/{job_id}/transcript")
    assert transcript.status_code == 200
    assert len(transcript.json()) >= 1

    clips = client.get(f"/v1/jobs/{job_id}/clips/candidates")
    assert clips.status_code == 200
    assert len(clips.json()) == 2

    clip_ids = [clip["id"] for clip in clips.json()[:1]]
    select = client.post(f"/v1/jobs/{job_id}/clips/select", json={"clip_ids": clip_ids})
    assert select.status_code == 200
    assert select.json()["selected_count"] == 1

    outputs = client.get(f"/v1/jobs/{job_id}/outputs")
    assert outputs.status_code == 200
    assert outputs.json()["job_id"] == job_id
