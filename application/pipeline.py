# application/pipeline.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Any


@dataclass(frozen=True)
class Step:
    fn: Callable[[Dict[str, Any]], Dict[str, Any]]
    name: str


class Pipeline:
    def __init__(self, *steps: Step) -> None:
        self._steps = list(steps)

    def __call__(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        for step in self._steps:
            ctx = step.fn(ctx)
        return ctx
