"""initial schema

Revision ID: 0001_initial
Revises: None
Create Date: 2026-03-19 17:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_style_preset", sa.String(length=100), nullable=False),
        sa.Column("brand_settings_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "jobs",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("input_video_url", sa.String(length=500), nullable=True),
        sa.Column("input_audio_url", sa.String(length=500), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("fps", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("requested_platforms_json", sa.JSON(), nullable=False),
        sa.Column("requested_clip_count", sa.Integer(), nullable=False),
        sa.Column("user_instructions", sa.Text(), nullable=True),
        sa.Column("narration_enabled", sa.Boolean(), nullable=False),
        sa.Column("broll_enabled", sa.Boolean(), nullable=False),
        sa.Column("style_preset", sa.String(length=100), nullable=False),
        sa.Column("current_step", sa.String(length=100), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_project_id", "jobs", ["project_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_table(
        "transcript_segments",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("speaker", sa.String(length=100), nullable=True),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcript_segments_job_id", "transcript_segments", ["job_id"])
    op.create_table(
        "transcript_words",
        sa.Column("segment_id", sa.String(), nullable=False),
        sa.Column("word", sa.String(length=255), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["segment_id"], ["transcript_segments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transcript_words_segment_id", "transcript_words", ["segment_id"])
    op.create_table(
        "clip_candidates",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("hook", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("topic_label", sa.String(length=100), nullable=False),
        sa.Column("reasoning_json", sa.JSON(), nullable=False),
        sa.Column("caption_style", sa.String(length=100), nullable=False),
        sa.Column("broll_prompts_json", sa.JSON(), nullable=False),
        sa.Column("cta_text", sa.Text(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clip_candidates_job_id", "clip_candidates", ["job_id"])
    op.create_table(
        "assets",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("clip_id", sa.String(), nullable=True),
        sa.Column("asset_type", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["clip_id"], ["clip_candidates.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_clip_id", "assets", ["clip_id"])
    op.create_index("ix_assets_job_id", "assets", ["job_id"])
    op.create_table(
        "renders",
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("clip_id", sa.String(), nullable=False),
        sa.Column("output_format", sa.String(length=50), nullable=False),
        sa.Column("output_url", sa.String(length=500), nullable=True),
        sa.Column("subtitle_url", sa.String(length=500), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["clip_id"], ["clip_candidates.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_renders_clip_id", "renders", ["clip_id"])
    op.create_index("ix_renders_job_id", "renders", ["job_id"])
    op.create_table(
        "webhooks",
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("target_url", sa.String(length=500), nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhooks_project_id", "webhooks", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_webhooks_project_id", table_name="webhooks")
    op.drop_table("webhooks")
    op.drop_index("ix_renders_job_id", table_name="renders")
    op.drop_index("ix_renders_clip_id", table_name="renders")
    op.drop_table("renders")
    op.drop_index("ix_assets_job_id", table_name="assets")
    op.drop_index("ix_assets_clip_id", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_clip_candidates_job_id", table_name="clip_candidates")
    op.drop_table("clip_candidates")
    op.drop_index("ix_transcript_words_segment_id", table_name="transcript_words")
    op.drop_table("transcript_words")
    op.drop_index("ix_transcript_segments_job_id", table_name="transcript_segments")
    op.drop_table("transcript_segments")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_project_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("projects")
