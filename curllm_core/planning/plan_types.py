"""Task plan types for curllm planning."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from curllm_core.command_parser import ParsedCommand


class StepType(Enum):
    """Types of execution steps."""

    NAVIGATE = "navigate"
    RESOLVE = "resolve"
    ANALYZE = "analyze"
    WAIT = "wait"
    SEARCH = "search"
    FILL_FIELD = "fill_field"
    FILL_FORM = "fill_form"
    CLICK = "click"
    SUBMIT = "submit"
    EXTRACT = "extract"
    VERIFY = "verify"
    SCREENSHOT = "screenshot"


class StepStatus(Enum):
    """Status of a step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskStep:
    """Single execution step."""

    step_type: StepType
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    timeout_ms: int = 30000
    retry_count: int = 2
    optional: bool = False
    depends_on: List[int] = field(default_factory=list)
    fallback: Optional["TaskStep"] = None
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class TaskPlan:
    """Complete execution plan."""

    steps: List[TaskStep] = field(default_factory=list)
    description: str = ""
    expected_outcome: str = ""
    total_timeout_seconds: int = 120
    stop_on_failure: bool = True
    parsed_command: Optional[ParsedCommand] = None

    def add_step(
        self,
        step_type: StepType,
        params: Dict[str, Any] | None = None,
        description: str = "",
        **kwargs: Any,
    ) -> int:
        step = TaskStep(
            step_type=step_type,
            params=params or {},
            description=description,
            **kwargs,
        )
        self.steps.append(step)
        return len(self.steps) - 1

    def get_pending_steps(self) -> List[TaskStep]:
        pending: List[TaskStep] = []
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            deps_met = all(
                self.steps[dep].status == StepStatus.COMPLETED
                for dep in step.depends_on
            )
            if deps_met:
                pending.append(step)
        return pending

    def is_complete(self) -> bool:
        return all(
            step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
            for step in self.steps
        )

    def has_failed(self) -> bool:
        return any(
            step.status == StepStatus.FAILED and not step.optional
            for step in self.steps
        )
