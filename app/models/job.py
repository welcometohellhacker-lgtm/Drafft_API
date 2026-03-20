from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import uuid4

from app.models.enums import JobStatus


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
class Job:
    __tablename__: ClassVar[str] = "jobs"

    project_id: str
    id: str = field(default_factory=_uuid)
    user_id: str | None = None
    status: str = JobStatus.created.value
    input_video_url: str | None = None
    input_audio_url: str | None = None
    duration_seconds: int | None = None
    fps: int | None = None
    width: int | None = None
    height: int | None = None
    requested_platforms_json: list = field(default_factory=list)
    requested_clip_count: int = 3
    user_instructions: str | None = None
    narration_enabled: bool = False
    broll_enabled: bool = False
    style_preset: str = "finance_clean"
    current_step: str = "created"
    progress_percent: int = 0
    failure_reason: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    # Eagerly loaded relationship — populated by JobRepository.get()
    project: Any = field(default=None, repr=False)

    def _to_firestore(self) -> dict:
        return {
            "project_id": self.project_id,
            "user_id": self.user_id,
            "status": self.status,
            "input_video_url": self.input_video_url,
            "input_audio_url": self.input_audio_url,
            "duration_seconds": self.duration_seconds,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "requested_platforms_json": self.requested_platforms_json or [],
            "requested_clip_count": self.requested_clip_count,
            "user_instructions": self.user_instructions,
            "narration_enabled": self.narration_enabled,
            "broll_enabled": self.broll_enabled,
            "style_preset": self.style_preset,
            "current_step": self.current_step,
            "progress_percent": self.progress_percent,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def _from_firestore(cls, doc_id: str, data: dict) -> "Job":
        return cls(
            id=doc_id,
            project_id=data.get("project_id", ""),
            user_id=data.get("user_id"),
            status=data.get("status", JobStatus.created.value),
            input_video_url=data.get("input_video_url"),
            input_audio_url=data.get("input_audio_url"),
            duration_seconds=data.get("duration_seconds"),
            fps=data.get("fps"),
            width=data.get("width"),
            height=data.get("height"),
            requested_platforms_json=data.get("requested_platforms_json") or [],
            requested_clip_count=data.get("requested_clip_count", 3),
            user_instructions=data.get("user_instructions"),
            narration_enabled=data.get("narration_enabled", False),
            broll_enabled=data.get("broll_enabled", False),
            style_preset=data.get("style_preset", "finance_clean"),
            current_step=data.get("current_step", "created"),
            progress_percent=data.get("progress_percent", 0),
            failure_reason=data.get("failure_reason"),
            created_at=_ts(data.get("created_at")),
            updated_at=_ts(data.get("updated_at")),
        )

    def _update_from_firestore(self, data: dict) -> None:
        updated = self._from_firestore(self.id, data)
        skip = {"id", "project"}
        for f_name in updated.__dataclass_fields__:
            if f_name not in skip:
                setattr(self, f_name, getattr(updated, f_name))
