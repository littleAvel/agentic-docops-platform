from __future__ import annotations

import asyncio
from typing import Any, Dict

from app.extraction.engine import extract_fields
from app.tools.contracts import ExtractionInput, ExtractionOutput


class ToolTimeoutError(RuntimeError):
    pass


class ToolExecutionError(RuntimeError):
    pass


DEFAULT_EXTRACTION_TIMEOUT_S = 20


async def _call_existing_extractor(
    *,
    schema_id: str,
    pipeline_id: str,
    source_text: str,
    ctx: Dict[str, Any],
) -> Dict[str, Any]:
    fields = await extract_fields(
        schema_id=schema_id,
        pipeline_id=pipeline_id,
        source_text=source_text,
    )
    if not isinstance(fields, dict):
        raise ToolExecutionError("extract_fields() must return a dict")
    return {"fields": fields}


async def extraction_run_real(inputs: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    data = ExtractionInput.model_validate(inputs)

    if not data.source_text:
        raise ToolExecutionError("source_text is required for extraction")

    timeout_s_raw = ctx.get("tool_timeout_s", DEFAULT_EXTRACTION_TIMEOUT_S)
    try:
        timeout_s = int(timeout_s_raw)
    except Exception:
        timeout_s = DEFAULT_EXTRACTION_TIMEOUT_S

    try:
        raw = await asyncio.wait_for(
            _call_existing_extractor(
                schema_id=data.schema_id,
                pipeline_id=data.pipeline_id,
                source_text=data.source_text,
                ctx=ctx,
            ),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError as e:
        raise ToolTimeoutError(f"extraction timed out after {timeout_s}s") from e
    except Exception as e:
        raise ToolExecutionError(f"extraction failed: {type(e).__name__}: {e}") from e

    if isinstance(raw, dict) and isinstance(raw.get("fields"), dict):
        fields = raw["fields"]
    elif isinstance(raw, dict):
        fields = raw
    else:
        raise ToolExecutionError("extractor returned invalid type (expected dict)")

    out = ExtractionOutput(
        extracted={
            "schema_id": data.schema_id,
            "pipeline_id": data.pipeline_id,
            "fields": fields,
        }
    )
    return out.model_dump()
