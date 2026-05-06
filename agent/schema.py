from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


STAGES = ("retrieval", "ranking", "briefing")


class SkillNotImplementedError(NotImplementedError):
    """Raised when a workflow Skill has not been implemented yet."""


@dataclass
class WorkflowInput:
    query: str
    date_range: str = "last 7 days"
    max_results: int = 50
    top_k: int = 5
    method: str = "tfidf"
    allowed_categories: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowResult:
    status: str
    completed_stages: list[str] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    output_paths: dict[str, str] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_stage(stage: str, *, name: str = "stage") -> str:
    if stage not in STAGES:
        raise ValueError(f"Invalid {name}: {stage!r}. Expected one of: {', '.join(STAGES)}")
    return stage
