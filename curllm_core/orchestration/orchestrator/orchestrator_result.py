from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from curllm_core.command_parser import ParsedCommand
from curllm_core.task_planner import TaskPlan
from .step_result import StepResult


@dataclass
class OrchestratorResult:
    """Final result of orchestration"""
    success: bool
    command: str
    parsed: Optional[ParsedCommand] = None
    plan: Optional[TaskPlan] = None
    step_results: List[StepResult] = field(default_factory=list)
    final_url: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    log_path: Optional[str] = None

