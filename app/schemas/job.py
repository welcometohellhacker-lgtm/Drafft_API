from pydantic import BaseModel, Field

from app.schemas.common import TimestampedResponse


class JobCreate(BaseModel):
    project_id: str
    requested_platforms_json: list[str] = Field(default_factory=lambda: ["9:16"])
    requested_clip_count: int = Field(default=3, ge=1, le=20)
    user_instructions: str | None = None
    narration_enabled: bool = False
    broll_enabled: bool = False
    style_preset: str = "finance_clean"


class JobProcessRequest(BaseModel):
    regenerate_transcript: bool = False
    render_selected_immediately: bool = False


class ClipCandidateResponse(BaseModel):
    id: str
    start_time: float
    end_time: float
    title: str
    hook: str
    score: int
    topic_label: str
    reasoning_json: list[str]
    caption_style: str
    broll_prompts_json: list[str]
    cta_text: str | None = None
    selected: bool


class JobResponse(TimestampedResponse):
    project_id: str
    status: str
    input_video_url: str | None = None
    input_audio_url: str | None = None
    duration_seconds: int | None = None
    fps: int | None = None
    width: int | None = None
    height: int | None = None
    requested_platforms_json: list
    requested_clip_count: int
    user_instructions: str | None = None
    narration_enabled: bool
    broll_enabled: bool
    style_preset: str
    current_step: str
    progress_percent: int
    failure_reason: str | None = None


class TranscriptSegmentResponse(BaseModel):
    id: str
    speaker: str | None = None
    start_time: float
    end_time: float
    text: str
    confidence: float | None = None


class JobOutputsResponse(BaseModel):
    job_id: str
    outputs: list[dict]


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    current_step: str
    progress_percent: int
    failure_reason: str | None = None
    retryable: bool
    timeline: list[dict]
