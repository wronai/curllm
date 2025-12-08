from typing import Any, Dict, List, Callable
import functools
from ..flow import flow, Flow
from ..registry import list_components, list_schemes
from ...diagnostics import get_logger


def pipeline(*steps: str) -> Flow:
    """
    Create a pipeline from multiple URI steps
    
    Args:
        *steps: URI strings for each step
        
    Returns:
        Flow instance
        
    Example:
        pipeline(
            "http://api.example.com/data",
            "transform://jsonpath?query=$.items",
            "file://write?path=output.json"
        )
    """
    if not steps:
        raise ValueError("Pipeline requires at least one step")
        
    result = flow(steps[0])
    
    for step in steps[1:]:
        result = result | step
        
    return result
