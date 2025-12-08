import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import AtomicFunctions


@dataclass
class AuthResult:
    """Authentication result"""
    success: bool
    method: str
    message: Optional[str] = None
    needs_2fa: bool = False
    needs_captcha: bool = False
    error: Optional[str] = None

