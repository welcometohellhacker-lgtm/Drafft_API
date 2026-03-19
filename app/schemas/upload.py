from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    content_type: str
    stored_path: str
