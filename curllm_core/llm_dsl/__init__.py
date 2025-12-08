"""
LLM-DSL Module - LLM generates DSL queries for atomic functions

Architecture:
1. LLM interprets user intent
2. LLM generates DSL queries
3. DSL executor calls atomic functions
4. Atomic functions use statistics, heuristics, DOM analysis

NO hardcoded keywords or selectors - everything is LLM-driven.
"""

from curllm_core.llm_dsl.executor import DSLExecutor
from curllm_core.llm_dsl.generator import DSLQueryGenerator
from curllm_core.llm_dsl.atoms import AtomicFunctions

__all__ = [
    'DSLExecutor',
    'DSLQueryGenerator', 
    'AtomicFunctions',
]
