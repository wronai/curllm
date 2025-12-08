import json
import logging
from typing import Any, Dict, List, Optional

from .llm_hierarchical_planner import LLMHierarchicalPlanner

async def should_use_hierarchical_llm(
    instruction: str,
    page_context: Dict[str, Any],
    llm=None
) -> bool:
    """
    LLM-driven decision on hierarchical planner usage.
    """
    planner = LLMHierarchicalPlanner(llm=llm)
    return await planner.should_use_hierarchical(instruction, page_context)
