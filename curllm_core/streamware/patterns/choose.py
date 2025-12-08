from __future__ import annotations

from typing import Any, List, Callable, Optional, Iterator, TYPE_CHECKING
import json
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register, create_component
from ..exceptions import ComponentError
from ...diagnostics import get_logger

if TYPE_CHECKING:
    from .choose_component import ChooseComponent

def choose() -> ChooseComponent:
    """
    Create choose component for conditional routing
    
    Returns:
        ChooseComponent instance
        
    Example:
        choose()
            .when("$.priority == 'high'", "kafka://high-priority")
            .when("$.priority == 'low'", "file://low.log")
            .otherwise("file://default.log")
    """
    uri = "choose://router"
    return create_component(uri)
