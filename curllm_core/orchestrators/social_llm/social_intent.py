import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions


@dataclass
class SocialIntent:
    """User's social media intent - parsed by LLM"""
    action: str  # login, post, message, like, follow, comment, browse
    credentials: Dict[str, str]
    content: Optional[str]
    target: Optional[str]
    confidence: float

