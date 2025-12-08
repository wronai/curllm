from __future__ import annotations

from typing import Any, List, Callable, Optional, Iterator, TYPE_CHECKING
import json
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register, create_component
from ..exceptions import ComponentError
from ...diagnostics import get_logger

if TYPE_CHECKING:
    from .split_component import SplitComponent

def split(pattern: str = '$[*]', split_type: str = 'jsonpath') -> SplitComponent:
    """
    Create split component
    
    Args:
        pattern: Split pattern (JSONPath query or field name)
        split_type: Type of split (jsonpath, field, batch)
        
    Returns:
        SplitComponent instance
    """
    if split_type == 'jsonpath':
        uri = f"split://{split_type}?query={pattern}"
    elif split_type == 'field':
        uri = f"split://{split_type}?name={pattern}"
    else:
        uri = f"split://{split_type}"
        
    return create_component(uri)
