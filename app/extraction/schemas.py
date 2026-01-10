from __future__ import annotations

# MVP: один домен general
# Day 7: расширим на legal/finance/hr/medical и сделаем разные схемы
SCHEMA_REGISTRY: dict[str, dict] = {
    "general.v1": {
        "instructions": (
            "Extract key facts into a flat 'fields' object. "
            "Use only what is explicitly in the text. No inventions."
        ),
    },
}
