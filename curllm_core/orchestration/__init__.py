"""
Orchestration module - Execute task plans step by step

The main coordinator that:
1. Takes a natural language command
2. Parses it into structured format
3. Creates an execution plan
4. Executes each step with proper error handling
5. Logs everything for debugging
6. Returns structured results
"""

from curllm_core.orchestration.models import (
    StepResult,
    OrchestratorResult,
    OrchestratorConfig,
)
from curllm_core.orchestration.orchestrator import Orchestrator
from curllm_core.orchestration.execute import execute_command

__all__ = [
    'StepResult',
    'OrchestratorResult',
    'OrchestratorConfig',
    'Orchestrator',
    'execute_command',
]
