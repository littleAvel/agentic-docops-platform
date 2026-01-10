from __future__ import annotations

from app.runtime.dsl import Plan, PlanLimits, PlanStep, WhenEquals


def build_plan(*, job_id: str, source_text: str) -> tuple[Plan, dict]:
    # Routing decision (single source of truth)
    domain = "general"
    pipeline_id = "general.default"
    schema_id = "general.v1"

    limits = PlanLimits(
        max_steps=12,
        max_tool_calls=8,
        max_cost_units=20,
    )

    steps = [
        PlanStep(
            id="extract",
            type="extract",
            tool="extraction.run",
            inputs={
                "schema_id": schema_id,
                "pipeline_id": pipeline_id,
            },
        ),
        PlanStep(
            id="verify",
            type="verify",
            tool="verification.run",
            inputs={
                "domain": domain,
                "schema_id": schema_id,
            },
        ),
        PlanStep(
            id="export_json",
            type="action",
            tool="actions.export_json",
            inputs={},
        ),
        PlanStep(
            id="ticket_warn",
            type="action",
            tool="actions.create_ticket",
            when=WhenEquals(signal="verification.verdict", equals="WARN"),
            inputs={"reason": "verification_warn"},
        ),
        PlanStep(
            id="ticket_fail",
            type="action",
            tool="actions.create_ticket",
            when=WhenEquals(signal="verification.verdict", equals="FAIL"),
            inputs={"reason": "verification_fail"},
        ),
        PlanStep(
            id="email_pass",
            type="action",
            tool="actions.draft_email",
            when=WhenEquals(signal="verification.verdict", equals="PASS"),
            inputs={
                "to": "ops@example.com",
                "template_id": f"{domain}_processed",
            },
        ),
        PlanStep(
            id="halt_on_fail",
            type="halt",
            when=WhenEquals(signal="verification.verdict", equals="FAIL"),
            reason="verification_failed",
        ),
    ]

    plan = Plan(
        job_id=job_id,
        domain=domain,
        pipeline_id=pipeline_id,
        schema_id=schema_id,
        limits=limits,
        steps=steps,
    )

    routing = {
        "domain": domain,
        "pipeline_id": pipeline_id,
        "schema_id": schema_id,
    }

    return plan, routing
