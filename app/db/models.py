from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Enum, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class JobStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PREPROCESSED = "PREPROCESSED"
    ROUTED = "ROUTED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    VERIFIED = "VERIFIED"
    ACTED = "ACTED"
    SUCCEEDED = "SUCCEEDED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID string
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.RECEIVED)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)

    domain: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pipeline_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    schema_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    signals: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class AuditEventType(str, enum.Enum):
    JOB_CREATED = "JOB_CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_RESULT = "TOOL_RESULT"
    POLICY_DENIED = "POLICY_DENIED"
    EXECUTOR_HALTED = "EXECUTOR_HALTED"
    ERROR = "ERROR"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[AuditEventType] = mapped_column(Enum(AuditEventType), nullable=False)

    # JSON payload: safe to store structured details (tool inputs, verdicts, error codes)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. extracted_json, verification_report
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
