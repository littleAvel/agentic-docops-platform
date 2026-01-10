from __future__ import annotations
from typing import Any, Awaitable, Callable, Dict

ToolFn = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {}

    def register(self, name: str, fn: ToolFn) -> None:
        self._tools[name] = fn

    def get(self, name: str) -> ToolFn:
        if name not in self._tools:
            raise KeyError(f"tool not registered: {name}")
        return self._tools[name]
