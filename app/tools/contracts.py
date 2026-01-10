from __future__ import annotations
from typing import Any, Dict, Literal
from pydantic import BaseModel, Field

Verdict = Literal["PASS", "WARN", "FAIL"]

class ExtractionInput(BaseModel):
    schema_id: str
    pipeline_id: str
    source_text: str

class ExtractionOutput(BaseModel):
    extracted: Dict[str, Any]

class VerificationInput(BaseModel):
    domain: str
    schema_id: str
    source_text: str
    extracted: Dict[str, Any]

class VerificationReport(BaseModel):
    verdict: Verdict
    checks: list[dict] = Field(default_factory=list)

class VerificationOutput(BaseModel):
    report: VerificationReport

class ExportJsonInput(BaseModel):
    extracted: Dict[str, Any]

class ExportJsonOutput(BaseModel):
    exported: bool = True

class DraftEmailInput(BaseModel):
    to: str
    template_id: str
    extracted: Dict[str, Any]

class DraftEmailOutput(BaseModel):
    to: str
    subject: str
    body: str

class CreateTicketInput(BaseModel):
    queue: str
    title: str
    report: Dict[str, Any]

class CreateTicketOutput(BaseModel):
    ticket_id: str
    status: str = "CREATED"
