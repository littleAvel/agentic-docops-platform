from __future__ import annotations
from app.runtime.policy import ToolPolicy

DEFAULT_POLICY = ToolPolicy(
    allowed_tools={
        "extraction.run",
        "verification.run",
        "actions.export_json",
        "actions.draft_email",
        "actions.create_ticket",
    },
    audit_allow_keys={
        # extraction/verification: НЕ логируем source_text, только метадату
        "extraction.run": {"schema_id", "pipeline_id"},
        "verification.run": {"domain", "schema_id"},
        # actions: логируем только безопасные поля
        "actions.export_json": set(),
        "actions.draft_email": {"to", "template_id"},
        "actions.create_ticket": {"queue", "title"},
    },
)
