import asyncio
import logging
import os
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
from curllm_core.command_parser import CommandParser, ParsedCommand
from curllm_core.task_planner import TaskPlanner, TaskPlan, TaskStep, StepType, StepStatus
from curllm_core.url_resolver import UrlResolver
from curllm_core.url_types import TaskGoal
from curllm_core.stealth import StealthConfig
from curllm_core.llm_element_finder import LLMElementFinder
from curllm_core.orchestrator_steps import StepExecutor
from curllm_core.result_validator import ResultValidator, ValidationLevel, ValidationResult

from .step_result import StepResult
from .orchestrator import Orchestrator

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

