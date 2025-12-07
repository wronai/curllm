"""Prompt manager for loading and saving prompts"""

import json
import logging
from typing import Dict, List

from curllm_web.config import PROMPTS_FILE
from curllm_web.prompts.default_prompts import DEFAULT_PROMPTS

logger = logging.getLogger(__name__)


def load_prompts() -> List[Dict]:
    """Load prompts from JSON file"""
    if PROMPTS_FILE.exists():
        try:
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
    return DEFAULT_PROMPTS


def save_prompts(prompts: List[Dict]) -> bool:
    """Save prompts to JSON file"""
    try:
        with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving prompts: {e}")
        return False
