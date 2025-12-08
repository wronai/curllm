"""
Running module - Task execution and runtime management

Functions for running tasks with planning cycles,
retry management, and execution orchestration.
"""

from curllm_core.running.runner import (
    run_task,
)

__all__ = [
    'run_task',
]
