import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import AtomicFunctions


@dataclass
class FormResult:
    """Form operation result"""
    success: bool
    filled: Dict[str, str]
    submitted: bool
    verification: Optional[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

