from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar
from uuid import uuid4


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
class ClipCandidate:
    __tablename__: ClassVar[str] = "clip_candidates"

    job_id: str
    start_time: float
    end_time: float
    title: str
    hook: str
    score: int
    topic_label: str
    id: str = field(default_factory=_uuid)
    reasoning_json: list = field(default_factory=list)
    caption_style: str = "finance_clean"
    broll_prompts_json: list = field(default_factory=list)
    cta_text: str | None = None
    selected: bool = False
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def _to_firestore(self) -> dict:
        return {
            "job_id": self.job_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "title": self.title,
            "hook": self.hook,
            "score": self.score,
            "topic_label": self.topic_label,
            "reasoning_json": self.reasoning_json or [],
            "caption_style": self.caption_style,
            "broll_prompts_json": self.broll_prompts_json or [],
            "cta_text": self.cta_text,
            "selected": self.selected,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def _from_firestore(cls, doc_id: str, data: dict) -> "ClipCandidate":
        return cls(
            id=doc_id,
            job_id=data.get("job_id", ""),
            start_time=float(data.get("start_time", 0)),
            end_time=float(data.get("end_time", 0)),
            title=data.get("title", ""),
            hook=data.get("hook", ""),
            score=int(data.get("score", 0)),
            topic_label=data.get("topic_label", ""),
            reasoning_json=data.get("reasoning_json") or [],
            caption_style=data.get("caption_style", "finance_clean"),
            broll_prompts_json=data.get("broll_prompts_json") or [],
            cta_text=data.get("cta_text"),
            selected=bool(data.get("selected", False)),
            created_at=_ts(data.get("created_at")),
            updated_at=_ts(data.get("updated_at")),
        )

    def _update_from_firestore(self, data: dict) -> None:
        updated = self._from_firestore(self.id, data)
        for f_name in updated.__dataclass_fields__:
            if f_name != "id":
                setattr(self, f_name, getattr(updated, f_name))
