from __future__ import annotations

from typing import Any, List, Callable, Optional, Iterator, TYPE_CHECKING
import json
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register, create_component
from ..exceptions import ComponentError
from ...diagnostics import get_logger

if TYPE_CHECKING:
    from .join_component import JoinComponent

def join(join_type: str = 'list') -> JoinComponent:
    """
    Create join component
    
    Args:
        join_type: Type of join (list, dict)
        
    Returns:
        JoinComponent instance
    """
    uri = f"join://collect?type={join_type}"
    return create_component(uri)
