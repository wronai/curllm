import json
import logging
from typing import Any, Dict, List, Optional

from .llm_hierarchical_planner import LLMHierarchicalPlanner

def extract_strategic_context(page_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract strategic context (stateless, no LLM needed).
    """
    planner = LLMHierarchicalPlanner()
    return planner._extract_strategic_context(page_context)
