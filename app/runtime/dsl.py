from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator


class WhenEquals(BaseModel):
    signal: str
    equals: Any


class WhenIn(BaseModel):
    signal: str
    in_: List[Any] = Field(alias="in")


When = Union[WhenEquals, WhenIn]


class RetryPolicy(BaseModel):
    max_retries: int = 0
    backoff_ms: int = 0


StepType = Literal["extract", "verify", "action", "halt"]


class PlanStep(BaseModel):
    id: str
    type: StepType
    tool: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    when: Optional[When] = None
    retry: Optional[RetryPolicy] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_step(self):
        if self.type == "halt":
            if not self.reason:
                raise ValueError("halt step requires reason")
            return self

        if not self.tool:
            raise ValueError(f"{self.type} step requires tool")

        return self


class PlanLimits(BaseModel):
    max_steps: int = 12
    max_tool_calls: int = 10
    max_cost_units: int = 200
    max_replans: int = 0  # Plan A only


class Plan(BaseModel):
    version: str = "1.0"
    job_id: str
    limits: PlanLimits = Field(default_factory=PlanLimits)
    steps: List[PlanStep]

    @model_validator(mode="after")
    def validate_plan(self):
        if len(self.steps) > self.limits.max_steps:
            raise ValueError("plan exceeds max_steps")

        ids = [s.id for s in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate step ids")

        return self
