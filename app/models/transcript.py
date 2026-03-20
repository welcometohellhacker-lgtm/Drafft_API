from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar
from uuid import uuid4


def _uuid() -> str:
    return str(uuid4())


@dataclass
class TranscriptSegment:
    __tablename__: ClassVar[str] = "transcript_segments"

    job_id: str
    start_time: float
    end_time: float
    text: str
    id: str = field(default_factory=_uuid)
    speaker: str | None = None
    confidence: float | None = None
    # populated when needed (e.g. regenerate_transcript delete path)
    words: list = field(default_factory=list, repr=False)

    def _to_firestore(self) -> dict:
        return {
            "job_id": self.job_id,
            "speaker": self.speaker,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "confidence": self.confidence,
        }

    @classmethod
    def _from_firestore(cls, doc_id: str, data: dict) -> "TranscriptSegment":
        return cls(
            id=doc_id,
            job_id=data.get("job_id", ""),
            speaker=data.get("speaker"),
            start_time=float(data.get("start_time", 0)),
            end_time=float(data.get("end_time", 0)),
            text=data.get("text", ""),
            confidence=data.get("confidence"),
        )

    def _update_from_firestore(self, data: dict) -> None:
        updated = self._from_firestore(self.id, data)
        for attr in ("job_id", "speaker", "start_time", "end_time", "text", "confidence"):
            setattr(self, attr, getattr(updated, attr))


@dataclass
class TranscriptWord:
    __tablename__: ClassVar[str] = "transcript_words"

    segment_id: str
    word: str
    start_time: float
    end_time: float
    id: str = field(default_factory=_uuid)
    confidence: float | None = None

    def _to_firestore(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "word": self.word,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "confidence": self.confidence,
        }

    @classmethod
    def _from_firestore(cls, doc_id: str, data: dict) -> "TranscriptWord":
        return cls(
            id=doc_id,
            segment_id=data.get("segment_id", ""),
            word=data.get("word", ""),
            start_time=float(data.get("start_time", 0)),
            end_time=float(data.get("end_time", 0)),
            confidence=data.get("confidence"),
        )
