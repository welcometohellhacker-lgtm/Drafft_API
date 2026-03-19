from pydantic import BaseModel, Field


class UltimateClipsRequest(BaseModel):
    project_id: str
    requested_platforms_json: list[str] = Field(default_factory=lambda: ["9:16"])
    requested_clip_count: int = 3
    user_instructions: str | None = None
    narration_enabled: bool = True
    broll_enabled: bool = True


class UltimateClipsResponse(BaseModel):
    job_id: str
    status: str
    current_step: str
    progress_percent: int
    llm_model: str
    selected_style: str
    cto_score: int
    gallery: list[dict]
