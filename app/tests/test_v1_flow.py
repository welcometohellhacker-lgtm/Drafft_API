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
    body = outputs.json()
    assert body["job_id"] == job_id
    asset_types = {asset["asset_type"] for asset in body["outputs"][0]["assets"]}
    assert "source_video" in asset_types
    assert "transcript_json" in asset_types
    assert "subtitle_srt" in asset_types
    assert "subtitle_vtt" in asset_types
    assert "caption_plan" in asset_types
    assert "broll_plan" in asset_types
    assert "clip_candidate_json" in asset_types


def test_v2_render_outputs_flow() -> None:
    project = client.post(
        "/v1/projects",
        json={"name": "Render Project", "default_style_preset": "kinetic_bold", "brand_settings_json": {}},
    )
    project_id = project.json()["id"]
    job = client.post(
        "/v1/jobs",
        json={"project_id": project_id, "requested_platforms_json": ["9:16"], "requested_clip_count": 1, "style_preset": "kinetic_bold"},
    )
    job_id = job.json()["id"]
    client.post(
        f"/v1/jobs/{job_id}/upload",
        files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")},
    )
    render = client.post(f"/v1/jobs/{job_id}/render")
    assert render.status_code == 202
    outputs = client.get(f"/v1/jobs/{job_id}/outputs")
    body = outputs.json()
    asset_types = {asset["asset_type"] for asset in body["outputs"][0]["assets"]}
    assert "rendered_clip" in asset_types
    assert "thumbnail" in asset_types
    renders = client.get(f"/v1/renders/{job_id}")
    assert renders.status_code == 200
    assert len(renders.json()["renders"]) == 1
    assert renders.json()["renders"][0]["status"] == "completed"


def test_v3_visual_plan_contains_overlay_and_broll_metadata() -> None:
    project = client.post(
        "/v1/projects",
        json={"name": "Visual Plan Project", "default_style_preset": "finance_clean", "brand_settings_json": {}},
    )
    project_id = project.json()["id"]
    job = client.post(
        "/v1/jobs",
        json={"project_id": project_id, "requested_platforms_json": ["9:16"], "requested_clip_count": 1, "broll_enabled": True},
    )
    job_id = job.json()["id"]
    client.post(f"/v1/jobs/{job_id}/upload", files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")})
    client.post(f"/v1/jobs/{job_id}/process", json={"regenerate_transcript": False, "render_selected_immediately": False})
    outputs = client.get(f"/v1/jobs/{job_id}/outputs")
    assets = outputs.json()["outputs"][0]["assets"]
    visual_plan = next(asset for asset in assets if asset["asset_type"] == "visual_plan")
    metadata = visual_plan["metadata_json"]
    assert len(metadata["broll_timeline"]) >= 1
    assert len(metadata["overlay_timeline"]) >= 1
    assert len(metadata["thumbnail_text_options"]) >= 1


def test_v3_generated_images_created_when_broll_enabled() -> None:
    project = client.post(
        "/v1/projects",
        json={"name": "Image Asset Project", "default_style_preset": "finance_clean", "brand_settings_json": {}},
    )
    project_id = project.json()["id"]
    job = client.post(
        "/v1/jobs",
        json={
            "project_id": project_id,
            "requested_platforms_json": ["9:16"],
            "requested_clip_count": 1,
            "broll_enabled": True,
        },
    )
    job_id = job.json()["id"]
    client.post(f"/v1/jobs/{job_id}/upload", files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")})
    client.post(f"/v1/jobs/{job_id}/process", json={"regenerate_transcript": False, "render_selected_immediately": False})
    outputs = client.get(f"/v1/jobs/{job_id}/outputs")
    assets = outputs.json()["outputs"][0]["assets"]
    generated_images = [asset for asset in assets if asset["asset_type"] == "generated_image"]
    assert len(generated_images) >= 1


def test_v4_narration_assets_created_when_enabled() -> None:
    project = client.post(
        "/v1/projects",
        json={"name": "Narration Project", "default_style_preset": "finance_clean", "brand_settings_json": {}},
    )
    project_id = project.json()["id"]
    job = client.post(
        "/v1/jobs",
        json={
            "project_id": project_id,
            "requested_platforms_json": ["9:16"],
            "requested_clip_count": 1,
            "narration_enabled": True,
        },
    )
    job_id = job.json()["id"]
    client.post(f"/v1/jobs/{job_id}/upload", files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")})
    client.post(f"/v1/jobs/{job_id}/process", json={"regenerate_transcript": False, "render_selected_immediately": False})
    outputs = client.get(f"/v1/jobs/{job_id}/outputs")
    assets = outputs.json()["outputs"][0]["assets"]
    asset_types = {asset["asset_type"] for asset in assets}
    assert "isolated_voice" in asset_types
    assert "narration_script" in asset_types
    assert "narration_audio" in asset_types


def test_v4_audio_mix_plan_created_for_clip() -> None:
    project = client.post(
        "/v1/projects",
        json={"name": "Audio Mix Project", "default_style_preset": "finance_clean", "brand_settings_json": {}},
    )
    project_id = project.json()["id"]
    job = client.post(
        "/v1/jobs",
        json={
            "project_id": project_id,
            "requested_platforms_json": ["9:16"],
            "requested_clip_count": 1,
            "narration_enabled": True,
        },
    )
    job_id = job.json()["id"]
    client.post(f"/v1/jobs/{job_id}/upload", files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")})
    client.post(f"/v1/jobs/{job_id}/process", json={"regenerate_transcript": False, "render_selected_immediately": False})
    outputs = client.get(f"/v1/jobs/{job_id}/outputs")
    assets = outputs.json()["outputs"][0]["assets"]
    audio_mix = next(asset for asset in assets if asset["asset_type"] == "audio_mix_plan")
    assert audio_mix["metadata_json"]["background_music"]["enabled"] is True
    assert audio_mix["metadata_json"]["normalization"]["target_lufs"] == -14


def test_v5_status_endpoint_returns_timeline() -> None:
    project = client.post(
        "/v1/projects",
        json={"name": "Status Project", "default_style_preset": "finance_clean", "brand_settings_json": {}},
    )
    project_id = project.json()["id"]
    job = client.post(
        "/v1/jobs",
        json={"project_id": project_id, "requested_platforms_json": ["9:16"], "requested_clip_count": 1},
    )
    job_id = job.json()["id"]
    client.post(f"/v1/jobs/{job_id}/upload", files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")})
    process = client.post(f"/v1/jobs/{job_id}/process", json={"regenerate_transcript": False, "render_selected_immediately": False})
    assert process.status_code == 202
    status_response = client.get(f"/v1/jobs/{job_id}/status")
    assert status_response.status_code == 200
    assert len(status_response.json()["timeline"]) >= 3


def test_v5_branding_profile_propagates_to_visual_plan() -> None:
    project = client.post(
        "/v1/projects",
        json={
            "name": "Brand Project",
            "default_style_preset": "finance_clean",
            "brand_settings_json": {"primary_color": "#123456", "font_family": "Manrope"},
        },
    )
    project_id = project.json()["id"]
    job = client.post(
        "/v1/jobs",
        json={"project_id": project_id, "requested_platforms_json": ["9:16"], "requested_clip_count": 1, "style_preset": "strong_cta"},
    )
    job_id = job.json()["id"]
    client.post(f"/v1/jobs/{job_id}/upload", files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")})
    client.post(f"/v1/jobs/{job_id}/process", json={"regenerate_transcript": False, "render_selected_immediately": False})
    outputs = client.get(f"/v1/jobs/{job_id}/outputs")
    assets = outputs.json()["outputs"][0]["assets"]
    branding = next(asset for asset in assets if asset["asset_type"] == "branding_profile")
    assert branding["metadata_json"]["brand_settings"]["primary_color"] == "#123456"
    visual_plan = next(asset for asset in assets if asset["asset_type"] == "visual_plan")
    assert visual_plan["metadata_json"]["branding"]["style_preset"] == "strong_cta"


def test_v5_output_enrichment_assets_created_after_render() -> None:
    project = client.post(
        "/v1/projects",
        json={"name": "Enrichment Project", "default_style_preset": "finance_clean", "brand_settings_json": {}},
    )
    project_id = project.json()["id"]
    job = client.post(
        "/v1/jobs",
        json={
            "project_id": project_id,
            "requested_platforms_json": ["9:16"],
            "requested_clip_count": 1,
            "narration_enabled": True,
            "broll_enabled": True,
        },
    )
    job_id = job.json()["id"]
    client.post(f"/v1/jobs/{job_id}/upload", files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")})
    client.post(f"/v1/jobs/{job_id}/render")
    outputs = client.get(f"/v1/jobs/{job_id}/outputs")
    assets = outputs.json()["outputs"][0]["assets"]
    asset_types = {asset["asset_type"] for asset in assets}
    assert "social_caption" in asset_types
    assert "webhook_event" in asset_types
    rendered = next(asset for asset in assets if asset["asset_type"] == "rendered_clip")
    assert "social_caption" in rendered["metadata_json"]


def test_ultimate_clips_endpoint_runs_full_auto_flow() -> None:
    project = client.post(
        "/v1/projects",
        json={"name": "Ultimate Project", "default_style_preset": "finance_clean", "brand_settings_json": {"primary_color": "#123456"}},
    )
    project_id = project.json()["id"]
    response = client.post(
        "/v1/ultimate-clips",
        data={
            "project_id": project_id,
            "requested_clip_count": 2,
            "user_instructions": "Make this automatic and high-converting.",
            "narration_enabled": "true",
            "broll_enabled": "true",
        },
        files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["llm_model"] == "CHATGPT-5.4"
    assert body["selected_style"] in {"viral_pop", "finance_clean"}


def test_ultimate_clips_response_contains_gallery_and_cto_score() -> None:
    project = client.post(
        "/v1/projects",
        json={"name": "Ultimate Gallery Project", "default_style_preset": "finance_clean", "brand_settings_json": {"primary_color": "#123456"}},
    )
    project_id = project.json()["id"]
    response = client.post(
        "/v1/ultimate-clips",
        data={
            "project_id": project_id,
            "requested_clip_count": 2,
            "user_instructions": "Make this automatic and high-converting.",
            "narration_enabled": "true",
            "broll_enabled": "true",
        },
        files={"file": ("sample.mp4", io.BytesIO(b"fake-video"), "video/mp4")},
    )
    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["gallery"], list)
    assert body["cto_score"] >= 0
