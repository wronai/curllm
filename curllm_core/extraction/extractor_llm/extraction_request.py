import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import AtomicFunctions


@dataclass
class ExtractionRequest:
    """What to extract - parsed by LLM"""
    data_types: List[str]  # emails, phones, links, products, etc.
    limit: int
    filter_text: Optional[str]

