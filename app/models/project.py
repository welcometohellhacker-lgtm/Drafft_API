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
class Project:
    __tablename__: ClassVar[str] = "projects"

    name: str
    id: str = field(default_factory=_uuid)
    description: str | None = None
    default_style_preset: str = "finance_clean"
    brand_settings_json: dict = field(default_factory=dict)
    user_id: str | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def _to_firestore(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "default_style_preset": self.default_style_preset,
            "brand_settings_json": self.brand_settings_json or {},
            "user_id": self.user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def _from_firestore(cls, doc_id: str, data: dict) -> "Project":
        return cls(
            id=doc_id,
            name=data.get("name", ""),
            description=data.get("description"),
            default_style_preset=data.get("default_style_preset", "finance_clean"),
            brand_settings_json=data.get("brand_settings_json") or {},
            user_id=data.get("user_id"),
            created_at=_ts(data.get("created_at")),
            updated_at=_ts(data.get("updated_at")),
        )

    def _update_from_firestore(self, data: dict) -> None:
        updated = self._from_firestore(self.id, data)
        for attr in ("name", "description", "default_style_preset",
                     "brand_settings_json", "user_id", "created_at", "updated_at"):
            setattr(self, attr, getattr(updated, attr))
