from typing import Any, List, Callable, Optional, Iterator
import json
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register, create_component
from ..exceptions import ComponentError
from ...diagnostics import get_logger

@register("join")
class JoinComponent(Component):
    """
    Join split data back into collection
    
    URI format:
        join://strategy?type=list|dict
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self._buffer: List[Any] = []
        
    def process(self, data: Any) -> Any:
        """Add data to buffer and return accumulated result"""
        if isinstance(data, list):
            self._buffer.extend(data)
        else:
            self._buffer.append(data)
            
        join_type = self.uri.get_param('type', 'list')
        
        if join_type == 'list':
            return self._buffer.copy()
        elif join_type == 'dict':
            # Create dict with index keys
            return {str(i): item for i, item in enumerate(self._buffer)}
        else:
            return self._buffer.copy()

