from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Set

from app.db.models import JobStatus

_ALLOWED: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.RECEIVED: {JobStatus.PREPROCESSED, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.PREPROCESSED: {JobStatus.ROUTED, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.ROUTED: {JobStatus.PLANNED, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.PLANNED: {JobStatus.EXECUTING, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.EXECUTING: {JobStatus.VERIFIED, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.VERIFIED: {JobStatus.ACTED, JobStatus.NEEDS_REVIEW, JobStatus.FAILED},
    JobStatus.ACTED: {JobStatus.SUCCEEDED, JobStatus.NEEDS_REVIEW, JobStatus.FAILED},
    JobStatus.NEEDS_REVIEW: {JobStatus.EXECUTING, JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.SUCCEEDED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}

@dataclass(frozen=True)
class TransitionError(Exception):
    from_status: JobStatus
    to_status: JobStatus
    def __str__(self) -> str:
        return f"invalid transition: {self.from_status} -> {self.to_status}"

def ensure_transition_allowed(from_status: JobStatus, to_status: JobStatus) -> None:
    allowed = _ALLOWED.get(from_status, set())
    if to_status not in allowed:
        raise TransitionError(from_status=from_status, to_status=to_status)
