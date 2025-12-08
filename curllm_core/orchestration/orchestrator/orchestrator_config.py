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

from .orchestrator import Orchestrator

@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator"""
    headless: bool = True
    stealth_mode: bool = True
    timeout_seconds: int = 120
    screenshot_on_error: bool = True
    screenshot_on_success: bool = True
    screenshot_each_step: bool = False  # Capture after each step
    log_to_file: bool = True
    log_dir: str = "logs"
    screenshot_dir: str = "screenshots"
    dry_run: bool = False  # Parse and plan only, don't execute
    auto_captcha_visible: bool = True  # Auto-switch to visible mode on CAPTCHA
    captcha_wait_seconds: int = 60  # How long to wait for user to solve CAPTCHA

