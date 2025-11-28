"""
LLM Component - Large Language Model Integration

Provides unified interface for LLM operations:
- Text generation
- Vision/multimodal inference
- Action planning
- Field mapping
- Success evaluation

Supports:
- Ollama (local)
- LangChain integration
"""

from .client import SimpleOllama, OllamaClient
from .factory import setup_llm, get_llm
from .planner import generate_action, ActionPlanner

__all__ = [
    'SimpleOllama',
    'OllamaClient',
    'setup_llm',
    'get_llm',
    'generate_action',
    'ActionPlanner'
]
