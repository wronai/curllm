from typing import Any, Dict, List, Callable
import functools
from ..flow import flow, Flow
from ..registry import list_components, list_schemes
from ...diagnostics import get_logger


def list_available_components() -> List[str]:
    """
    List all available component schemes
    
    Returns:
        List of scheme names
    """
    return list_schemes()
