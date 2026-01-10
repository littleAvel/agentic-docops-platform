from __future__ import annotations
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Job, JobStatus, AuditEventType
from app.core.audit import write_audit_event
from app.domain.job_service import set_job_status
from app.runtime.executor import BoundedExecutor, ExecLimits, ExecState
from app.runtime.planner import build_plan
from app.runtime.store import upsert_artifact, merge_signals
from app.runtime.default_policy import DEFAULT_POLICY
from app.tools.registry import ToolRegistry


# -----------------------
# helpers (resume-safe)
# -----------------------

def _when_matches(when: dict | None, signals: dict) -> bool:
    if when is None:
        return True

    sig = when.get("signal")
    val = signals.get(sig)

    if "equals" in when:
        return val == when["equals"]
    if "in" in when:
        return val in when["in"]
    if "in_" in when:  # defensive: non-aliased dump
        return val in when["in_"]

    return False


def _status_order(s: JobStatus) -> int:
    return {
        JobStatus.RECEIVED: 10,
        JobStatus.PREPROCESSED: 20,
        JobStatus.ROUTED: 30,
        JobStatus.PLANNED: 40,
        JobStatus.EXECUTING: 50,
        JobStatus.VERIFIED: 60,
        JobStatus.ACTED: 70,
        JobStatus.SUCCEEDED: 80,
        JobStatus.NEEDS_REVIEW: 90,
        JobStatus.FAILED: 100,
    }.get(s, 999)


async def _advance_status(
    session: AsyncSession,
    *,
    job: Job,
    to_status: JobStatus,
    reason: str,
) -> None:
    if job.status == to_status:
        return
    if _status_order(job.status) > _status_order(to_status):
        return

    await set_job_status(
        session,
        job_id=job.id,
        to_status=to_status,
        reason=reason,
    )
    await session.refresh(job)


async def _reload_job(session: AsyncSession, job_id: str) -> Job:
    res = await session.execute(select(Job).where(Job.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        raise ValueError("job not found")
    return job


# -----------------------
# main entrypoint
# -----------------------

async def run_job(
    *,
    session: AsyncSession,
    job_id: str,
    tools: ToolRegistry,
) -> dict:
    job = await _reload_job(session, job_id)

    # idempotency: already terminal
    if job.status in {
        JobStatus.SUCCEEDED,
        JobStatus.FAILED,
        JobStatus.NEEDS_REVIEW,
    }:
        return {
            "job_id": job_id,
            "final_status": job.status,
            "signals": dict(job.signals or {}),
            "note": f"no-op: job already terminal ({job.status})",
        }

    if not job.source_text:
        raise ValueError("job has no source_text")

    # PREPROCESSED
    if job.status == JobStatus.RECEIVED:
        await _advance_status(
            session,
            job=job,
            to_status=JobStatus.PREPROCESSED,
            reason="preprocess_done",
        )

    # -----------------------
    # PLAN + ROUTING (planner owns routing)
    # -----------------------

    plan, routing = build_plan(
        job_id=job_id,
        source_text=job.source_text,
    )

    domain = routing["domain"]
    pipeline_id = routing["pipeline_id"]
    schema_id = routing["schema_id"]

    await merge_signals(
        session,
        job=job,
        new_signals={
            "routing.domain": domain,
            "routing.pipeline_id": pipeline_id,
            "routing.schema_id": schema_id,
        },
    )

    await _advance_status(
        session,
        job=job,
        to_status=JobStatus.ROUTED,
        reason="routed",
    )

    await _advance_status(
        session,
        job=job,
        to_status=JobStatus.PLANNED,
        reason="plan_built",
    )

    await _advance_status(
        session,
        job=job,
        to_status=JobStatus.EXECUTING,
        reason="execution_started",
    )

    # -----------------------
    # EXECUTION
    # -----------------------

    executor = BoundedExecutor(
        limits=ExecLimits(
            max_steps=plan.limits.max_steps,
            max_tool_calls=plan.limits.max_tool_calls,
            max_cost_units=plan.limits.max_cost_units,
        )
    )
    state = ExecState()

    signals: Dict[str, Any] = dict(job.signals or {})
    ctx_base = {
        "job_id": job_id,
        "domain": domain,
    }

    extracted: dict | None = None
    verification_report: dict | None = None

    for step in plan.steps:
        if step.type == "halt":
            when_dict = step.when.model_dump(by_alias=True) if step.when else None
            if _when_matches(when_dict, signals):
                await write_audit_event(
                    session,
                    job_id=job_id,
                    event_type=AuditEventType.EXECUTOR_HALTED,
                    payload={"reason": step.reason},
                )
                break
            continue

        when_dict = step.when.model_dump(by_alias=True) if step.when else None
        if not _when_matches(when_dict, signals):
            continue

        tool_fn = tools.get(step.tool)
        inputs = dict(step.inputs)

        if step.type == "extract":
            inputs["source_text"] = job.source_text

        if step.type == "verify":
            inputs["source_text"] = job.source_text
            inputs["extracted"] = extracted or {}

        if step.tool in {"actions.export_json", "actions.draft_email"}:
            inputs["extracted"] = extracted or {}

        if step.tool == "actions.create_ticket":
            inputs["report"] = verification_report or {}

        result = await executor.run_tool(
            session=session,
            job_id=job_id,
            tool_name=step.tool,
            tool_fn=tool_fn,
            inputs=inputs,
            ctx={**ctx_base, "signals": signals},
            state=state,
            policy=DEFAULT_POLICY,
        )

        if step.type == "extract":
            extracted = result.get("extracted", {})
            await upsert_artifact(session, job_id=job_id, name="extracted_json", payload=extracted)
            signals["extraction.ok"] = True

        if step.type == "verify":
            verification_report = result.get("report", {})
            await upsert_artifact(
                session,
                job_id=job_id,
                name="verification_report",
                payload=verification_report,
            )
            signals["verification.verdict"] = verification_report.get("verdict")

        if step.tool == "actions.export_json":
            await upsert_artifact(session, job_id=job_id, name="export_result", payload=result)

        if step.tool == "actions.draft_email":
            await upsert_artifact(session, job_id=job_id, name="email_draft", payload=result)

        if step.tool == "actions.create_ticket":
            await upsert_artifact(session, job_id=job_id, name="ticket", payload=result)

    # -----------------------
    # FINALIZATION
    # -----------------------

    job = await _reload_job(session, job_id)
    await merge_signals(session, job=job, new_signals=signals)
    await session.refresh(job)

    verdict = (job.signals or {}).get("verification.verdict")

    await _advance_status(
        session,
        job=job,
        to_status=JobStatus.VERIFIED,
        reason="verification_completed",
    )

    if verdict == "PASS":
        await _advance_status(session, job=job, to_status=JobStatus.ACTED, reason="actions_completed")
        await _advance_status(session, job=job, to_status=JobStatus.SUCCEEDED, reason="done")

    elif verdict == "WARN":
        await _advance_status(session, job=job, to_status=JobStatus.ACTED, reason="actions_completed_warn")
        await _advance_status(session, job=job, to_status=JobStatus.NEEDS_REVIEW, reason="needs_human_review")

    elif verdict == "FAIL":
        await _advance_status(session, job=job, to_status=JobStatus.ACTED, reason="actions_completed_fail")
        await _advance_status(session, job=job, to_status=JobStatus.FAILED, reason="verification_failed")

    else:
        await _advance_status(session, job=job, to_status=JobStatus.SUCCEEDED, reason="done_no_verdict")

    job = await _reload_job(session, job_id)

    return {
        "job_id": job_id,
        "final_status": job.status,
        "signals": dict(job.signals or {}),
    }
