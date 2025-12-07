"""
curllm_server - API Server for Browser Automation with Local LLM
Supports visual analysis, CAPTCHA solving, and stealth mode
"""

from curllm_server.config import Config, config
from curllm_server.executor.curllm_executor import CurllmExecutor
from curllm_server.app import app

__all__ = [
    'Config',
    'config',
    'CurllmExecutor',
    'app',
]
