"""
CurLLM v2 - LLM-driven implementations without hardcoded selectors

This package contains the new implementations that use LLM
for dynamic element detection, intent parsing, and action execution.

NO HARDCODED:
- CSS selectors
- Keyword lists
- Regex patterns
- Platform-specific configs

Usage:
    from curllm_core.v2 import LLMFormOrchestrator, LLMAuthOrchestrator
    from curllm_core.v2 import llm_form_fill
    
Architecture:
    All v2 modules use the llm_dsl package which provides:
    - AtomicFunctions: Low-level LLM-driven DOM operations
    - DSLQueryGenerator: Converts natural language to DSL queries
    - DSLExecutor: Executes DSL queries using atomic functions
"""

# LLM-DSL core (the foundation)
from curllm_core.llm_dsl import (
    AtomicFunctions,
    DSLQueryGenerator,
    DSLExecutor as DSLQueryExecutor,
)

# LLM-driven form filling
from curllm_core.form_fill_llm import (
    llm_form_fill,
    smart_form_fill,
    FormFillResult,
)

# LLM-driven orchestrators
from curllm_core.orchestrators.form_llm import LLMFormOrchestrator
from curllm_core.orchestrators.auth_llm import LLMAuthOrchestrator
from curllm_core.orchestrators.social_llm import LLMSocialOrchestrator
from curllm_core.orchestrators.ecommerce_llm import LLMECommerceOrchestrator

# LLM-driven extraction
from curllm_core.extraction.extractor_llm import (
    LLMExtractor,
    llm_extract,
    extract_with_llm,
)

# LLM-driven planning
from curllm_core.hierarchical.planner_llm import (
    LLMHierarchicalPlanner,
    should_use_hierarchical_llm,
    extract_strategic_context,
)

# LLM-driven DSL execution
from curllm_core.dsl.executor_llm import (
    LLMDSLExecutor,
    LLMExecutionResult,
)

# LLM-driven URL resolution
from curllm_core.url_resolution.goal_detector_llm import (
    GoalDetectorHybrid,
    GoalDetectionResult,
    detect_navigation_goal,
)

__all__ = [
    # Core LLM-DSL
    'AtomicFunctions',
    'DSLQueryGenerator',
    'DSLQueryExecutor',
    
    # Form filling
    'llm_form_fill',
    'smart_form_fill',
    'FormFillResult',
    
    # Orchestrators
    'LLMFormOrchestrator',
    'LLMAuthOrchestrator',
    'LLMSocialOrchestrator',
    'LLMECommerceOrchestrator',
    
    # Extraction
    'LLMExtractor',
    'llm_extract',
    'extract_with_llm',
    
    # Planning
    'LLMHierarchicalPlanner',
    'should_use_hierarchical_llm',
    'extract_strategic_context',
    
    # DSL
    'LLMDSLExecutor',
    'LLMExecutionResult',
    
    # URL Resolution
    'GoalDetectorHybrid',
    'GoalDetectionResult',
    'detect_navigation_goal',
]
