from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RenderStatus


class Render(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "renders"

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    clip_id: Mapped[str] = mapped_column(ForeignKey("clip_candidates.id"), nullable=False, index=True)
    output_format: Mapped[str] = mapped_column(String(50), nullable=False)
    output_url: Mapped[str | None] = mapped_column(String(500))
    subtitle_url: Mapped[str | None] = mapped_column(String(500))
    thumbnail_url: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(50), default=RenderStatus.queued.value)
    error_message: Mapped[str | None] = mapped_column(Text())

    job = relationship("Job", back_populates="renders")
    clip = relationship("ClipCandidate", back_populates="renders")
