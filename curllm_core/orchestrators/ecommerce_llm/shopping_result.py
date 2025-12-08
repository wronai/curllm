import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import AtomicFunctions


@dataclass 
class ShoppingResult:
    """Shopping operation result"""
    success: bool
    action: str
    products: List[Dict] = None
    cart: List[Dict] = None
    checkout_step: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.products is None:
            self.products = []
        if self.cart is None:
            self.cart = []

