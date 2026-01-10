from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Set

@dataclass(frozen=True)
class ToolPolicy:
    allowed_tools: Set[str]
    # какие ключи inputs можно писать в audit (остальное redacted)
    audit_allow_keys: Dict[str, Set[str]]

    def is_allowed(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools

    def allowed_audit_keys(self, tool_name: str) -> Set[str]:
        return self.audit_allow_keys.get(tool_name, set())
