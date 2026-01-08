from pydantic import BaseModel
from datetime import datetime
from app.db.models import AuditEventType

class AuditEventResponse(BaseModel):
    id: int
    job_id: str
    event_type: AuditEventType
    payload: dict
    created_at: datetime
