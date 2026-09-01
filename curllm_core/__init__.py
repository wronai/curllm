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
from __future__ import annotations

import importlib

from .config import Config, config
from .executor import CurllmExecutor
from .server import app, run_server
from .llm_config import LLMConfig, LLMPresets
from .llm_factory import setup_llm, create_llm_client

# Streamware component architecture
from . import streamware

# Versioned APIs
from . import v1  # Legacy (deprecated)


def __getattr__(name: str):
    """Load the optional v2 API only when a caller actually requests it."""
    if name == "v2":
        module = importlib.import_module(".v2", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
