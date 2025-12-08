from typing import Any, Dict, List, Callable
import functools
from ..flow import flow, Flow
from ..registry import list_components, list_schemes
from ...diagnostics import get_logger


def describe_component(scheme: str) -> Dict[str, Any]:
    """
    Get detailed information about a component
    
    Args:
        scheme: Component scheme
        
    Returns:
        Component metadata
    """
    components = list_components()
    
    for comp in components:
        if comp['scheme'] == scheme:
            return comp
            
    return None
