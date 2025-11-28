#!/usr/bin/env python3
"""
DEPRECATED: Use curllm_core.streamware.components.navigation instead.

This file is kept for backward compatibility.
"""
import random
from typing import Any, Dict


async def execute_action(page, action: Dict, runtime: Dict[str, Any] = None):
    """Execute action - delegates to streamware.components.navigation."""
    # Lazy import to avoid circular dependency
    from curllm_core.streamware.components.navigation import execute_action as _exec
    return await _exec(page, action, runtime or {})


async def _auto_scroll(page, steps: int = 3, delay_ms: int = 500):
    """Auto scroll - delegates to streamware.components.navigation."""
    from curllm_core.streamware.components.navigation import auto_scroll
    return await auto_scroll(page, steps, delay_ms)


__all__ = ['execute_action', '_auto_scroll']
