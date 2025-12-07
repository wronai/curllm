"""
curllm_core package: reusable modules for curllm server and executor
"""
from .config import Config, config
from .executor import CurllmExecutor
from .server import app, run_server
from .llm_config import LLMConfig, LLMPresets
from .llm_factory import setup_llm, create_llm_client

# Streamware component architecture
from . import streamware

__all__ = [
    "Config",
    "config",
    "CurllmExecutor",
    "LLMConfig",
    "LLMPresets",
    "setup_llm",
    "create_llm_client",
    "app",
    "run_server",
    "streamware",
]
