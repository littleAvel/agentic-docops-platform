from __future__ import annotations
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent, AuditEventType

async def write_audit_event(
    session: AsyncSession,
    *,
    job_id: str,
    event_type: AuditEventType,
    payload: Dict[str, Any],
    commit: bool = True
) -> None:
    session.add(AuditEvent(job_id=job_id, event_type=event_type, payload=payload))
    if commit:
        await session.commit()
