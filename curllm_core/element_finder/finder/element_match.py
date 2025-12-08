import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ElementMatch:
    """Result of LLM element finding"""
    selector: str
    confidence: float
    reasoning: str
    element_type: str  # input, button, link, textarea, etc.
    attributes: Dict[str, str]

