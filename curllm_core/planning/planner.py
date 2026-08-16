"""
Task Planner - Create execution plans from parsed commands.

Public API is re-exported from focused modules.
"""

from curllm_core.command_parser import ParsedCommand

from .plan_types import StepStatus, StepType, TaskPlan, TaskStep
from .task_planner import TaskPlanner


def create_plan(parsed: ParsedCommand) -> TaskPlan:
    """Convenience function for creating plans."""
    return TaskPlanner().plan(parsed)


__all__ = [
    "StepStatus",
    "StepType",
    "TaskPlan",
    "TaskStep",
    "TaskPlanner",
    "create_plan",
]
