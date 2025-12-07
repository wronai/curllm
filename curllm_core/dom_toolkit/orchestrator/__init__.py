"""
Orchestrator - Minimal LLM Usage for High-Level Decisions

LLM is used ONLY for:
1. Task interpretation (what to extract)
2. Strategy selection (which approach to use)
3. Result validation (did we get what was asked)

All DOM analysis is done by JavaScript helpers in analyzers/.
"""

from .task_router import ExtractionOrchestrator, AtomicLLMQuery

__all__ = [
    'ExtractionOrchestrator',
    'AtomicLLMQuery',
]
