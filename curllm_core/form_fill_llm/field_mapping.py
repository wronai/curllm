import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions
from curllm_core.llm_dsl.atoms import AtomResult


@dataclass
class FieldMapping:
    """Mapping of user value to form field"""
    user_key: str       # What user called it (e.g., "email")
    user_value: str     # Value to fill
    field_selector: str # Found selector
    field_purpose: str  # LLM-detected purpose
    confidence: float

