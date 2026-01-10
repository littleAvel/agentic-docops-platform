from __future__ import annotations

from typing import Any, Dict
import uuid

from app.runtime.verification_rules import verify as verify_rules
from app.tools.contracts import (
    ExtractionInput,
    ExtractionOutput,
    VerificationInput,
    VerificationOutput,
    ExportJsonInput,
    ExportJsonOutput,
    DraftEmailInput,
    DraftEmailOutput,
    CreateTicketInput,
    CreateTicketOutput,
)


async def extraction_run(inputs: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    data = ExtractionInput.model_validate(inputs)
    # stub extracted
    out = ExtractionOutput(extracted={"schema_id": data.schema_id, "pipeline_id": data.pipeline_id, "fields": {"example": "value"}})
    return out.model_dump()

async def verification_run(inputs: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    data = VerificationInput.model_validate(inputs)
    report = verify_rules(
        domain=data.domain,
        schema_id=data.schema_id,
        source_text=data.source_text,
        extracted=data.extracted,
    )
    out = VerificationOutput(report=report)
    return out.model_dump()

async def actions_export_json(inputs: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    ExportJsonInput.model_validate(inputs)
    out = ExportJsonOutput(exported=True)
    return {"exported": out.exported}

async def actions_draft_email(inputs: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    data = DraftEmailInput.model_validate(inputs)
    out = DraftEmailOutput(
        to=data.to,
        subject=f"[DOCOPS] {data.template_id}",
        body="Draft email body (stub) based on extracted data."
    )
    return out.model_dump()

async def actions_create_ticket(inputs: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    CreateTicketInput.model_validate(inputs)
    out = CreateTicketOutput(ticket_id=f"TCK-{uuid.uuid4().hex[:6]}")
    return out.model_dump()
