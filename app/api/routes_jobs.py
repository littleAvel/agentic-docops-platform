from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_session
from app.db.models import Job, JobStatus, AuditEvent, AuditEventType
from app.api.schemas_jobs import JobCreateRequest, JobResponse, JobStatusUpdateRequest
from app.api.schemas_events import AuditEventResponse
from app.core.audit import write_audit_event
from app.domain.job_service import set_job_status


router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobResponse, status_code=201)
async def create_job(req: JobCreateRequest, session: AsyncSession = Depends(get_session)):
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        status=JobStatus.RECEIVED,
        filename=req.filename,
        content_type=req.content_type,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    await write_audit_event(
        session,
        job_id=job.id,
        event_type=AuditEventType.JOB_CREATED,
        payload={"filename": job.filename, "content_type": job.content_type},
    )
    return JobResponse.model_validate(job, from_attributes=True)

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Job).where(Job.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse.model_validate(job, from_attributes=True)

@router.get("/{job_id}/events", response_model=list[AuditEventResponse])
async def get_job_events(job_id: str, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(AuditEvent)
        .where(AuditEvent.job_id == job_id)
        .order_by(AuditEvent.id.asc())
    )
    events = res.scalars().all()
    return [AuditEventResponse.model_validate(e, from_attributes=True) for e in events]

@router.post("/{job_id}/status", response_model=JobResponse)
async def update_job_status(job_id: str, req: JobStatusUpdateRequest, session: AsyncSession = Depends(get_session)):
    try:
        job = await set_job_status(session, job_id=job_id, to_status=req.to_status, reason=req.reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JobResponse.model_validate(job, from_attributes=True)