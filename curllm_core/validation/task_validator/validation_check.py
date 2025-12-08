import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


@dataclass
class ValidationCheck:
    """Result of a single validation check"""
    strategy: str
    passed: bool
    score: float  # 0.0 - 1.0
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)

