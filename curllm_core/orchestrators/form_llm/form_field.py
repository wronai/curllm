import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import AtomicFunctions


@dataclass
class FormField:
    """Form field detected by LLM"""
    selector: str
    purpose: str
    field_type: str
    required: bool
    label: str

