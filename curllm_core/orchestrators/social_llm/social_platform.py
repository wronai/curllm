import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions


class SocialPlatform(Enum):
    """Social platforms - detected by LLM, not hardcoded matching"""
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    UNKNOWN = "unknown"
