from pydantic import BaseModel
from app.db.models import JobStatus


class JobCreateRequest(BaseModel):
    filename: str
    content_type: str
    text: str | None = None


class JobResponse(BaseModel):
    id: str
    status: JobStatus
    filename: str
    content_type: str
    domain: str | None = None
    pipeline_id: str | None = None
    schema_id: str | None = None
    error: str | None = None
    signals: dict = {}


class JobStatusUpdateRequest(BaseModel):
    to_status: JobStatus
    reason: str | None = None
