import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import AtomicFunctions


@dataclass
class ExtractionResult:
    """Extraction result"""
    success: bool
    data: Dict[str, Any]
    method: str  # llm, statistical

