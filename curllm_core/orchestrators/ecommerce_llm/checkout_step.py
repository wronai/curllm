import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import AtomicFunctions


class CheckoutStep(Enum):
    """Checkout steps - detected by LLM"""
    CART = "cart"
    SHIPPING = "shipping"
    PAYMENT = "payment"
    CONFIRMATION = "confirmation"
