import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions


@dataclass
class SocialResult:
    """Result of social media action"""
    success: bool
    platform: str
    action: str
    message: Optional[str] = None
    data: Optional[Dict] = None
    error: Optional[str] = None

