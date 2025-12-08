import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from curllm_core.url_types import TaskGoal


@dataclass
class GoalDetectionResult:
    """Result of goal detection."""
    goal: TaskGoal
    confidence: float
    reasoning: Optional[str] = None
