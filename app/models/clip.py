from sqlalchemy import Boolean, Float, ForeignKey, JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class ClipCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clip_candidates"

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    hook: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    topic_label: Mapped[str] = mapped_column(String(100), nullable=False)
    reasoning_json: Mapped[list] = mapped_column(JSON, default=list)
    caption_style: Mapped[str] = mapped_column(String(100), default="finance_clean")
    broll_prompts_json: Mapped[list] = mapped_column(JSON, default=list)
    cta_text: Mapped[str | None] = mapped_column(Text())
    selected: Mapped[bool] = mapped_column(Boolean, default=False)

    job = relationship("Job", back_populates="clip_candidates")
    renders = relationship("Render", back_populates="clip")
