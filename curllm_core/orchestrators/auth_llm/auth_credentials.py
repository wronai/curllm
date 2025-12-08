import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import AtomicFunctions


@dataclass
class AuthCredentials:
    """Credentials parsed by LLM"""
    email: Optional[str] = None
    password: Optional[str] = None
    otp_code: Optional[str] = None
    remember: bool = False

