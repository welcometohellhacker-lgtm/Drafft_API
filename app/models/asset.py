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
class Asset:
    __tablename__: ClassVar[str] = "assets"

    job_id: str
    asset_type: str
    url: str
    id: str = field(default_factory=_uuid)
    clip_id: str | None = None
    provider: str | None = None
    prompt: str | None = None
    metadata_json: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def _to_firestore(self) -> dict:
        return {
            "job_id": self.job_id,
            "clip_id": self.clip_id,
            "asset_type": self.asset_type,
            "provider": self.provider,
            "prompt": self.prompt,
            "url": self.url,
            "metadata_json": self.metadata_json or {},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def _from_firestore(cls, doc_id: str, data: dict) -> "Asset":
        return cls(
            id=doc_id,
            job_id=data.get("job_id", ""),
            clip_id=data.get("clip_id"),
            asset_type=data.get("asset_type", ""),
            provider=data.get("provider"),
            prompt=data.get("prompt"),
            url=data.get("url", ""),
            metadata_json=data.get("metadata_json") or {},
            created_at=_ts(data.get("created_at")),
            updated_at=_ts(data.get("updated_at")),
        )

    def _update_from_firestore(self, data: dict) -> None:
        updated = self._from_firestore(self.id, data)
        for f_name in updated.__dataclass_fields__:
            if f_name != "id":
                setattr(self, f_name, getattr(updated, f_name))
