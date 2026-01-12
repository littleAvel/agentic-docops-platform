from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ArtifactResponse(BaseModel):
    id: int
    job_id: str
    name: str
    payload: Optional[Any] = None
    created_at: Optional[datetime] = None
