from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from app.core.audit import write_audit_event
from app.db.models import Artifact, AuditEvent, AuditEventType, Job, JobStatus
from app.db.session import get_session
from app.runtime.runner import run_job
from app.tools.init_tools import build_tool_registry

router = APIRouter(tags=["ui"])
templates = Jinja2Templates(directory="app/ui/templates")

# Build registry once (module-level). Tools should be pure / stateless.
tool_registry = build_tool_registry()


# -----------------------
# Home (root UI)
# -----------------------
@router.get("/", response_class=HTMLResponse)
async def ui_home(request: Request, session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Job).order_by(Job.created_at.desc()).limit(20))
    jobs = res.scalars().all()
    return templates.TemplateResponse("index.html", {"request": request, "jobs": jobs})


# -----------------------
# UI actions under /ui/*
# (avoid collisions with API /jobs)
# -----------------------
@router.post("/ui/jobs")
async def ui_create_job(
    request: Request,
    filename: str = Form(default="document.txt"),
    content_type: str = Form(default="text/plain"),
    text: str = Form(...),
    session: AsyncSession = Depends(get_session),
):
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        status=JobStatus.RECEIVED,
        filename=filename,
        content_type=content_type,
        source_text=text,
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

    return RedirectResponse(url=f"/ui/jobs/{job.id}", status_code=303)


@router.get("/ui/jobs/{job_id}", response_class=HTMLResponse)
async def ui_job_detail(
    request: Request,
    job_id: str,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(Job).where(Job.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        return templates.TemplateResponse(
            "not_found.html",
            {"request": request, "job_id": job_id},
            status_code=404,
        )

    ev = await session.execute(
        select(AuditEvent).where(AuditEvent.job_id == job_id).order_by(AuditEvent.id.asc())
    )
    events = ev.scalars().all()

    ar = await session.execute(
        select(Artifact).where(Artifact.job_id == job_id).order_by(Artifact.id.asc())
    )
    artifacts = ar.scalars().all()

    return templates.TemplateResponse(
        "job.html",
        {
            "request": request,
            "job": job,
            "events": events,
            "artifacts": artifacts,
        },
    )


@router.post("/ui/jobs/{job_id}/run")
async def ui_run_job(job_id: str, session: AsyncSession = Depends(get_session)):
    await run_job(session=session, job_id=job_id, tools=tool_registry)
    return RedirectResponse(url=f"/ui/jobs/{job_id}", status_code=303)
