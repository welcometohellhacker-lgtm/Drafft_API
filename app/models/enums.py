from enum import Enum


class JobStatus(str, Enum):
    created = "created"
    uploaded = "uploaded"
    queued = "queued"
    preprocessing = "preprocessing"
    transcribing = "transcribing"
    analyzing = "analyzing"
    generating_assets = "generating_assets"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"


class RenderStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
