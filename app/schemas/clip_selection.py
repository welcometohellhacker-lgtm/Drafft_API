from pydantic import BaseModel, Field


class ClipSelectionRequest(BaseModel):
    clip_ids: list[str] = Field(default_factory=list)
