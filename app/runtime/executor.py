from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_event
from app.db.models import AuditEventType

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
    ) -> Dict[str, Any]:
        if state.steps >= self.limits.max_steps:
            raise StepLimitExceeded("max_steps exceeded")
        if state.tool_calls >= self.limits.max_tool_calls:
            raise BudgetExceeded("max_tool_calls exceeded")

        state.steps += 1
        state.tool_calls += 1
        self._charge(state, cost=1)

        await write_audit_event(
            session,
            job_id=job_id,
            event_type=AuditEventType.TOOL_CALLED,
            payload={"tool": tool_name, "inputs": inputs},
        )

        result = await tool_fn(inputs=inputs, ctx=ctx)

        await write_audit_event(
            session,
            job_id=job_id,
            event_type=AuditEventType.TOOL_RESULT,
            payload={"tool": tool_name, "result_keys": list(result.keys())},
        )

        return result
