import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .element_match import ElementMatch
from .llm_element_finder import LLMElementFinder

async def find_element_with_llm(
    page,
    intent: str,
    llm=None,
    element_type: str = "any"
) -> Optional[ElementMatch]:
    """Convenience function for finding elements"""
    finder = LLMElementFinder(llm=llm, page=page)
    return await finder.find_element(intent, element_type)
