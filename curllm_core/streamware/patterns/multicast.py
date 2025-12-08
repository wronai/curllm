from __future__ import annotations

from typing import Any, List, Callable, Optional, Iterator, TYPE_CHECKING
import json
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register, create_component
from ..exceptions import ComponentError
from ...diagnostics import get_logger

if TYPE_CHECKING:
    from .multicast_component import MulticastComponent

def multicast(destinations: List[str]) -> MulticastComponent:
    """
    Create multicast component
    
    Args:
        destinations: List of destination URIs
        
    Returns:
        MulticastComponent instance
    """
    dest_str = ','.join(destinations)
    uri = f"multicast://parallel?destinations={dest_str}"
    return create_component(uri)
