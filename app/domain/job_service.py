from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Job, JobStatus, AuditEventType
from app.core.audit import write_audit_event
from app.domain.state_machine import ensure_transition_allowed


async def set_job_status(
    session: AsyncSession,
    *,
    job_id: str,
    to_status: JobStatus,
    reason: str | None = None,
) -> Job:
    res = await session.execute(select(Job).where(Job.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        raise ValueError("job not found")

    from_status = job.status
    ensure_transition_allowed(from_status, to_status)

    job.status = to_status
    await session.commit()
    await session.refresh(job)

    await write_audit_event(
        session,
        job_id=job_id,
        event_type=AuditEventType.STATUS_CHANGED,
        payload={
            "from": from_status.value,
            "to": to_status.value,
            "reason": reason,
        },
    )

    return job
