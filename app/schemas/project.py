from pydantic import BaseModel, Field

from app.schemas.common import TimestampedResponse


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    default_style_preset: str = "finance_clean"
    brand_settings_json: dict = Field(default_factory=dict)


class ProjectResponse(TimestampedResponse):
    name: str
    description: str | None = None
    default_style_preset: str
    brand_settings_json: dict
