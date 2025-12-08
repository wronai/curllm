import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

from .validation_report import ValidationReport
from .task_validator import TaskValidator

async def validate_task(
    instruction: str,
    result: Dict[str, Any],
    llm=None,
    page_context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ValidationReport:
    """
    Convenience function for quick task validation.
    
    Usage:
        report = await validate_task(
            instruction="Fill form with name=John",
            result={"form_fill": {"submitted": True}},
            llm=llm_client
        )
    """
    validator = TaskValidator(llm=llm)
    return await validator.validate(
        instruction=instruction,
        result=result,
        page_context=page_context,
        **kwargs
    )
