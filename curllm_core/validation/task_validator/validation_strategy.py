import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


class ValidationStrategy(Enum):
    """Available validation strategies"""
    SEMANTIC = "semantic"       # LLM-based understanding
    STRUCTURAL = "structural"   # Data structure check
    RULES = "rules"             # Business rules
    VISUAL = "visual"           # Screenshot analysis
    DOM_DIFF = "dom_diff"       # DOM before/after
    SCHEMA = "schema"           # JSON schema validation
    CUSTOM = "custom"
