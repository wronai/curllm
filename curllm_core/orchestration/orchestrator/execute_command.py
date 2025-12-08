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

from .orchestrator_result import OrchestratorResult
from .orchestrator_config import OrchestratorConfig
from .orchestrator import Orchestrator

async def execute_command(
    command: str,
    config: Optional[OrchestratorConfig] = None
) -> OrchestratorResult:
    """Convenience function to execute a command"""
    orchestrator = Orchestrator(config)
    return await orchestrator.execute(command)
