"""
CurLLM v1 - Legacy implementations with hardcoded selectors

This package contains the original implementations that use
hardcoded selectors, keyword lists, and regex patterns.

For new code, use v2 which provides LLM-driven alternatives.

Usage:
    from curllm_core.v1 import FormOrchestrator, AuthOrchestrator
    from curllm_core.v1.extraction import extractor
"""

# Re-export legacy modules from their original locations
from curllm_core.form_fill import deterministic_form_fill
from curllm_core.orchestrators.form import FormOrchestrator
from curllm_core.orchestrators.auth import AuthOrchestrator
from curllm_core.orchestrators.social import SocialMediaOrchestrator
from curllm_core.orchestrators.ecommerce import ECommerceOrchestrator
from curllm_core.hierarchical.planner import (
    should_use_hierarchical,
    is_simple_form_task,
    requires_multi_step,
    extract_strategic_context,
)
from curllm_core.dsl.executor import DSLExecutor
from curllm_core.url_resolver import UrlResolver

__all__ = [
    # Form filling
    'deterministic_form_fill',
    
    # Orchestrators
    'FormOrchestrator',
    'AuthOrchestrator', 
    'SocialMediaOrchestrator',
    'ECommerceOrchestrator',
    
    # Planning
    'should_use_hierarchical',
    'is_simple_form_task',
    'requires_multi_step',
    'extract_strategic_context',
    
    # DSL
    'DSLExecutor',
    
    # URL
    'UrlResolver',
]
