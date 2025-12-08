import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from curllm_core.url_types import TaskGoal

from .goal_detection_result import GoalDetectionResult
from .goal_detector_hybrid import GoalDetectorHybrid

async def detect_navigation_goal(
    instruction: str,
    llm=None,
    page_context: Optional[dict] = None
) -> GoalDetectionResult:
    """
    Convenience function to detect navigation goal.
    
    Args:
        instruction: User instruction
        llm: LLM client (optional)
        page_context: Current page context (optional, for enhanced detection)
        
    Returns:
        GoalDetectionResult
    """
    detector = GoalDetectorHybrid(llm)
    return await detector.detect_goal(instruction)
