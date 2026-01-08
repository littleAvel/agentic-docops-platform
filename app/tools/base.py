from __future__ import annotations
from typing import Any, Dict, Protocol

class Tool(Protocol):
    name: str
    async def run(self, *, inputs: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        ...
