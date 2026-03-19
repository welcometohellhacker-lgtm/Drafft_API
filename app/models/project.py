from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, UUIDPrimaryKeyMixin


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    default_style_preset: Mapped[str] = mapped_column(String(100), default="finance_clean")
    brand_settings_json: Mapped[dict] = mapped_column(JSON, default=dict)

    jobs = relationship("Job", back_populates="project")
    webhooks = relationship("Webhook", back_populates="project")
