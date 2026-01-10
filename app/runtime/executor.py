from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_event
from app.db.models import AuditEventType
from app.runtime.policy import ToolPolicy


@dataclass
class ExecLimits:
    max_steps: int = 12
    max_tool_calls: int = 10
    max_cost_units: int = 200

@dataclass
class ExecState:
    steps: int = 0
    tool_calls: int = 0
    cost_units: int = 0

class BudgetExceeded(RuntimeError): ...
class StepLimitExceeded(RuntimeError): ...

class BoundedExecutor:
    def __init__(self, *, limits: ExecLimits) -> None:
        self.limits = limits

    def _charge(self, state: ExecState, cost: int = 1) -> None:
        state.cost_units += cost
        if state.cost_units > self.limits.max_cost_units:
            raise BudgetExceeded("max_cost_units exceeded")

    async def run_tool(
        self,
        *,
        session: AsyncSession,
        job_id: str,
        tool_name: str,
        tool_fn,
        inputs: Dict[str, Any],
        ctx: Dict[str, Any],
        state: ExecState,
        policy: ToolPolicy,
    ) -> Dict[str, Any]:
        # 0) POLICY CHECK (deny-by-default) — before any logging or budget charging
        if not policy.is_allowed(tool_name):
            await write_audit_event(
                session,
                job_id=job_id,
                event_type=AuditEventType.POLICY_DENIED,
                payload={"tool": tool_name, "reason": "deny_by_default"},
            )
            raise PermissionError(f"tool not allowed by policy: {tool_name}")

        # 1) BUDGET / LIMITS
        if state.steps >= self.limits.max_steps:
            raise StepLimitExceeded("max_steps exceeded")
        if state.tool_calls >= self.limits.max_tool_calls:
            raise BudgetExceeded("max_tool_calls exceeded")

        state.steps += 1
        state.tool_calls += 1
        self._charge(state, cost=1)

        # 2) REDACT INPUTS FOR AUDIT
        allow_keys = policy.allowed_audit_keys(tool_name)
        safe_inputs = {k: inputs.get(k) for k in allow_keys if k in inputs}

        await write_audit_event(
            session,
            job_id=job_id,
            event_type=AuditEventType.TOOL_CALLED,
            payload={"tool": tool_name, "inputs": safe_inputs},
        )

        # 3) EXECUTE TOOL
        result = await tool_fn(inputs=inputs, ctx=ctx)

        # 4) AUDIT RESULT (no sensitive content, only keys)
        await write_audit_event(
            session,
            job_id=job_id,
            event_type=AuditEventType.TOOL_RESULT,
            payload={"tool": tool_name, "result_keys": list(result.keys())},
        )

        return result
