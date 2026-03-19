from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import UUIDPrimaryKeyMixin


class TranscriptSegment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "transcript_segments"

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), nullable=False, index=True)
    speaker: Mapped[str | None] = mapped_column(String(100))
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)

    job = relationship("Job", back_populates="transcript_segments")
    words = relationship("TranscriptWord", back_populates="segment")


class TranscriptWord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "transcript_words"

    segment_id: Mapped[str] = mapped_column(ForeignKey("transcript_segments.id"), nullable=False, index=True)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)

    segment = relationship("TranscriptSegment", back_populates="words")
