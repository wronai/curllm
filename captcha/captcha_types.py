"""Shared CAPTCHA types and configuration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    """Types of CAPTCHAs we can handle."""

    SLIDING_PUZZLE = "sliding_puzzle"
    IMAGE_SELECTION = "image_selection"
    TEXT_RECOGNITION = "text_recognition"
    AUDIO = "audio"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    GEETEST = "geetest"


@dataclass
class CaptchaConfig:
    """Configuration for CAPTCHA solving."""

    use_2captcha: bool = False
    api_key_2captcha: str = ""
    use_local_solver: bool = True
    max_retries: int = 3
    timeout: int = 30
    screenshot_dir: Path = Path("./captcha_screenshots")
    debug_mode: bool = False
