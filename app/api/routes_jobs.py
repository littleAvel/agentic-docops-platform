from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas_artifacts import ArtifactResponse
from app.api.schemas_events import AuditEventResponse
from app.api.schemas_jobs import JobCreateRequest, JobResponse, JobStatusUpdateRequest
from app.core.audit import write_audit_event
from app.db.models import Artifact, AuditEvent, AuditEventType, Job, JobStatus  # <-- Artifact added
from app.db.session import get_session
from app.domain.job_service import set_job_status
from app.runtime.runner import run_job
from app.tools.init_tools import build_tool_registry


router = APIRouter(prefix="/jobs", tags=["jobs"])

# Build registry once (module-level). Tools should be pure / stateless.
tool_registry = build_tool_registry()


async def _ensure_job_exists(session: AsyncSession, job_id: str) -> None:
    res = await session.execute(select(Job.id).where(Job.id == job_id))
    exists = res.scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="job not found")


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(req: JobCreateRequest, session: AsyncSession = Depends(get_session)):
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        status=JobStatus.RECEIVED,
        filename=req.filename,
        content_type=req.content_type,
        source_text=req.text,
        signals={},
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    await write_audit_event(
        session,
        job_id=job.id,
        event_type=AuditEventType.JOB_CREATED,
        payload={
            "filename": job.filename,
            "content_type": job.content_type,
            "has_text": bool(job.source_text),
        },
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
    await _ensure_job_exists(session, job_id)

    res = await session.execute(
        select(AuditEvent).where(AuditEvent.job_id == job_id).order_by(AuditEvent.id.asc())
    )
    events = res.scalars().all()
    return [AuditEventResponse.model_validate(e, from_attributes=True) for e in events]


@router.get("/{job_id}/artifacts", response_model=list[ArtifactResponse])
async def get_job_artifacts(job_id: str, session: AsyncSession = Depends(get_session)):
    res = await session.execute(
        select(Artifact).where(Artifact.job_id == job_id).order_by(Artifact.id.asc())
    )
    artifacts = res.scalars().all()
    return [ArtifactResponse.model_validate(a, from_attributes=True) for a in artifacts]


@router.post("/{job_id}/status", response_model=JobResponse)
async def update_job_status(
    job_id: str, req: JobStatusUpdateRequest, session: AsyncSession = Depends(get_session)
):
    try:
        job = await set_job_status(session, job_id=job_id, to_status=req.to_status, reason=req.reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JobResponse.model_validate(job, from_attributes=True)


@router.post("/{job_id}/run")
async def run_job_endpoint(job_id: str, session: AsyncSession = Depends(get_session)):
    """
    Run is idempotent:
    - If job already terminal, runner returns no-op payload.
    - If policy denies a tool, we finalize job as FAILED and return 403.
    - Any unexpected error finalizes job as FAILED to avoid leaving EXECUTING jobs around.
    """
    try:
        return await run_job(session=session, job_id=job_id, tools=tool_registry)

    except PermissionError as e:
        # Policy deny must never leave the job in EXECUTING
        try:
            await set_job_status(session, job_id=job_id, to_status=JobStatus.FAILED, reason="policy_denied")
        except Exception:
            # do not mask original error if status update fails
            pass

        # Optional: audit an ERROR event for HTTP layer (runner already writes POLICY_DENIED)
        await write_audit_event(
            session,
            job_id=job_id,
            event_type=AuditEventType.ERROR,
            payload={"error": str(e), "kind": "policy_denied"},
        )

        raise HTTPException(status_code=403, detail=str(e))

    except Exception as e:
        # Any unexpected error: finalize status to avoid "stuck EXECUTING"
        try:
            await set_job_status(session, job_id=job_id, to_status=JobStatus.FAILED, reason="run_failed")
        except Exception:
            pass

        await write_audit_event(
            session,
            job_id=job_id,
            event_type=AuditEventType.ERROR,
            payload={"error": str(e), "kind": "run_failed"},
        )

        # keep default FastAPI 500 with stacktrace in logs
        raise
