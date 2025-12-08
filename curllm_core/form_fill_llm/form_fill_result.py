import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions
from curllm_core.llm_dsl.atoms import AtomResult

from .field_mapping import FieldMapping

@dataclass 
class FormFillResult:
    """Result of form filling"""
    success: bool
    filled_fields: List[FieldMapping]
    submitted: bool
    message: Optional[str] = None
    errors: List[str] = None

