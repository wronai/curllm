import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import AtomicFunctions

from .llm_extractor import LLMExtractor

async def extract_with_llm(
    page,
    llm,
    data_type: str,
    limit: int = 50,
) -> List[Any]:
    """
    Extract specific data type using LLM.
    
    Args:
        page: Playwright page
        llm: LLM instance
        data_type: What to extract (emails, phones, links, etc.)
        limit: Max items
        
    Returns:
        List of extracted items
    """
    extractor = LLMExtractor(page=page, llm=llm)
    extracted = await extractor._extract_data_type(data_type, limit)
    return extracted
