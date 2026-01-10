from app.tools.registry import ToolRegistry
from app.tools.stubs import (
    verification_run,
    actions_export_json,
    actions_draft_email,
    actions_create_ticket,
)
from app.tools.extraction_adapter import extraction_run_real


def build_tool_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("extraction.run", extraction_run_real)  # REAL adapter
    reg.register("verification.run", verification_run)
    reg.register("actions.export_json", actions_export_json)
    reg.register("actions.draft_email", actions_draft_email)
    reg.register("actions.create_ticket", actions_create_ticket)
    return reg
