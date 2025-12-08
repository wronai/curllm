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
from curllm_core.llm_dsl.element_finder import LLMElementFinder, ElementMatch, find_element_by_purpose
from curllm_core.llm_dsl.selector_generator import LLMSelectorGenerator, GeneratedSelector, generate_selector

__all__ = [
    'DSLExecutor',
    'DSLQueryGenerator', 
    'AtomicFunctions',
    'LLMElementFinder',
    'ElementMatch',
    'find_element_by_purpose',
    'LLMSelectorGenerator',
    'GeneratedSelector',
    'generate_selector',
]
