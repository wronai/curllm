"""
curllm Tools System - Specialized, composable tools for web automation

Each tool:
- Has JSON manifest describing interface
- Implements execute() method
- Returns typed output matching schema
- Can be discovered and orchestrated by LLM
"""

from .registry import get_registry, init_tools
from .base import BaseTool

__all__ = ["get_registry", "init_tools", "BaseTool"]
