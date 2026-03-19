from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import JobStatus


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "jobs"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default=JobStatus.created.value, index=True)
    input_video_url: Mapped[str | None] = mapped_column(String(500))
    input_audio_url: Mapped[str | None] = mapped_column(String(500))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    requested_platforms_json: Mapped[list] = mapped_column(JSON, default=list)
    requested_clip_count: Mapped[int] = mapped_column(Integer, default=3)
    user_instructions: Mapped[str | None] = mapped_column(Text())
    narration_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    broll_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    style_preset: Mapped[str] = mapped_column(String(100), default="finance_clean")
    current_step: Mapped[str] = mapped_column(String(100), default="created")
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[str | None] = mapped_column(Text())

    project = relationship("Project", back_populates="jobs")
    transcript_segments = relationship("TranscriptSegment", back_populates="job")
    clip_candidates = relationship("ClipCandidate", back_populates="job")
    assets = relationship("Asset", back_populates="job")
    renders = relationship("Render", back_populates="job")
