import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import AtomicFunctions


@dataclass
class ShoppingIntent:
    """Shopping intent parsed by LLM"""
    action: str  # search, add_to_cart, checkout, browse
    query: Optional[str]
    payment_method: Optional[str]
    shipping: Dict[str, str]
    confidence: float

