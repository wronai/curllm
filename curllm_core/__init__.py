"""
curllm_core package: reusable modules for curllm server and executor

API Versions:
    v1 - Legacy implementations with hardcoded selectors (deprecated)
    v2 - LLM-driven implementations (recommended for new code)

Usage:
    # New code - use v2
    from curllm_core.v2 import LLMFormOrchestrator, llm_form_fill
    
    # Legacy code - use v1
    from curllm_core.v1 import FormOrchestrator, deterministic_form_fill
"""
from .config import Config, config
from .executor import CurllmExecutor
from .server import app, run_server
from .llm_config import LLMConfig, LLMPresets
from .llm_factory import setup_llm, create_llm_client

# Streamware component architecture
from . import streamware

# Versioned APIs
from . import v1  # Legacy (deprecated)
from . import v2  # LLM-driven (recommended)

__all__ = [
    # Core
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
    # Versioned APIs
    "v1",
    "v2",
]
