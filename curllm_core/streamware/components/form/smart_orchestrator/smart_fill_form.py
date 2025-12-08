import json
import re
from typing import Dict, List, Any, Optional
from pathlib import Path

from .smart_form_orchestrator import SmartFormOrchestrator

async def smart_fill_form(
    page,
    llm,
    instruction: str,
    user_data: Dict[str, str],
    run_logger=None
) -> Dict[str, Any]:
    """
    Convenience function for smart form filling.
    
    Args:
        page: Playwright page
        llm: LLM client
        instruction: User instruction
        user_data: Data to fill
        run_logger: Optional logger
        
    Returns:
        Result dict
    """
    orchestrator = SmartFormOrchestrator(page, llm, instruction, run_logger)
    return await orchestrator.orchestrate(user_data)
