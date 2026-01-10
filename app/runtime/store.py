from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Artifact, Job

async def upsert_artifact(session: AsyncSession, *, job_id: str, name: str, payload: dict) -> None:
    session.add(Artifact(job_id=job_id, name=name, payload=payload))
    await session.commit()

async def merge_signals(session: AsyncSession, *, job: Job, new_signals: dict) -> Job:
    job.signals = {**(job.signals or {}), **new_signals}
    await session.commit()
    await session.refresh(job)
    return job
