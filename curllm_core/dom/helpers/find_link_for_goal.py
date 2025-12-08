import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo
from ._find_link_with_llm import _find_link_with_llm
from ._find_link_statistical import _find_link_statistical
from ._find_link_keyword_fallback import _find_link_keyword_fallback

async def find_link_for_goal(
    page,
    goal: str,
    base_url: Optional[str] = None,
    llm=None,
    use_llm: bool = True
) -> Optional[LinkInfo]:
    """
    Find best link for a specific goal using multiple strategies.
    
    Strategy hierarchy:
    1. LLM analysis (if available and use_llm=True)
    2. Statistical/semantic analysis of links
    3. Fallback keyword configurations
    
    The LLM approach analyzes all visible links and picks the best match
    based on semantic understanding, not just keyword matching.
    """
    # Try LLM-based link finding first
    if use_llm and llm:
        result = await _find_link_with_llm(page, goal, llm)
        if result:
            return result
    
    # Fallback to statistical analysis
    result = await _find_link_statistical(page, goal)
    if result:
        return result
    
    # Final fallback to keyword-based config (passes LLM for dynamic keyword generation)
    return await _find_link_keyword_fallback(page, goal, llm=llm)
