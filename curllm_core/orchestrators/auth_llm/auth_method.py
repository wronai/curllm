import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import AtomicFunctions


class AuthMethod(Enum):
    """Authentication methods - detected by LLM"""
    STANDARD = "standard"
    TWO_FACTOR = "2fa"
    OAUTH = "oauth"
    SSO = "sso"
    MAGIC_LINK = "magic_link"
