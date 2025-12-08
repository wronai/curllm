import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from .validation_check import ValidationCheck

@dataclass
class ValidationReport:
    """Complete validation report for a task"""
    task_type: str
    instruction: str
    overall_passed: bool
    overall_score: float
    confidence: float
    checks: List[ValidationCheck]
    summary: str
    recommendations: List[str] = field(default_factory=list)

