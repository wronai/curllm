"""Prompts module"""

from curllm_web.prompts.default_prompts import DEFAULT_PROMPTS
from curllm_web.prompts.prompt_manager import load_prompts, save_prompts

__all__ = ['DEFAULT_PROMPTS', 'load_prompts', 'save_prompts']
