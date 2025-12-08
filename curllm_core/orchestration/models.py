"""Data models for orchestrator"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from curllm_core.command_parser import ParsedCommand
from curllm_core.task_planner import TaskPlan


@dataclass
class StepResult:
    """Result of a single step execution"""
    step_index: int
    step_type: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    screenshot_path: Optional[str] = None


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


@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator"""
    headless: bool = True
    stealth_mode: bool = True
    timeout_seconds: int = 120
    screenshot_on_error: bool = True
    screenshot_on_success: bool = True
    screenshot_each_step: bool = False
    log_to_file: bool = True
    log_dir: str = "logs"
    screenshot_dir: str = "screenshots"
    dry_run: bool = False
    auto_captcha_visible: bool = True
    captcha_wait_seconds: int = 60
