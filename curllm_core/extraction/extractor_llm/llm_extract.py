import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import AtomicFunctions

from .llm_extractor import LLMExtractor

async def llm_extract(
    page,
    llm,
    instruction: str,
    run_logger=None,
) -> Dict[str, Any]:
    """
    Convenience function for LLM-driven extraction.
    
    Args:
        page: Playwright page
        llm: LLM instance
        instruction: What to extract
        run_logger: Optional logger
        
    Returns:
        Dict with extracted data
    """
    extractor = LLMExtractor(page=page, llm=llm, run_logger=run_logger)
    result = await extractor.extract(instruction)
    return result.data if result.success else {}
