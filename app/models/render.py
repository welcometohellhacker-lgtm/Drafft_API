from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar
from uuid import uuid4

from app.models.enums import RenderStatus


def _uuid() -> str:
    return str(uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(val) -> datetime:
    if val is None:
        return _now()
    if hasattr(val, "timestamp"):
        return datetime.fromtimestamp(val.timestamp(), tz=timezone.utc)
    if isinstance(val, datetime) and val.tzinfo is None:
        return val.replace(tzinfo=timezone.utc)
    return val


@dataclass
class Render:
    __tablename__: ClassVar[str] = "renders"

    job_id: str
    clip_id: str
    output_format: str
    id: str = field(default_factory=_uuid)
    output_url: str | None = None
    subtitle_url: str | None = None
    thumbnail_url: str | None = None
    metadata_json: dict = field(default_factory=dict)
    status: str = RenderStatus.queued.value
    error_message: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def _to_firestore(self) -> dict:
        return {
            "job_id": self.job_id,
            "clip_id": self.clip_id,
            "output_format": self.output_format,
            "output_url": self.output_url,
            "subtitle_url": self.subtitle_url,
            "thumbnail_url": self.thumbnail_url,
            "metadata_json": self.metadata_json or {},
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def _from_firestore(cls, doc_id: str, data: dict) -> "Render":
        return cls(
            id=doc_id,
            job_id=data.get("job_id", ""),
            clip_id=data.get("clip_id", ""),
            output_format=data.get("output_format", "9:16"),
            output_url=data.get("output_url"),
            subtitle_url=data.get("subtitle_url"),
            thumbnail_url=data.get("thumbnail_url"),
            metadata_json=data.get("metadata_json") or {},
            status=data.get("status", RenderStatus.queued.value),
            error_message=data.get("error_message"),
            created_at=_ts(data.get("created_at")),
            updated_at=_ts(data.get("updated_at")),
        )

    def _update_from_firestore(self, data: dict) -> None:
        updated = self._from_firestore(self.id, data)
        for f_name in updated.__dataclass_fields__:
            if f_name != "id":
                setattr(self, f_name, getattr(updated, f_name))
