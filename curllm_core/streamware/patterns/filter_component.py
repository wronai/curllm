from typing import Any, List, Callable, Optional, Iterator
import json
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register, create_component
from ..exceptions import ComponentError
from ...diagnostics import get_logger


@register("filter")
class FilterComponent(StreamComponent):
    """
    Filter data based on condition
    
    URI format:
        filter://condition?field=age&min=18
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Filter stream items"""
        if not input_stream:
            return
            
        condition_fn = self._get_condition()
        
        for item in input_stream:
            if condition_fn(item):
                yield item
                
    def process(self, data: Any) -> Any:
        """Filter single item or list"""
        condition_fn = self._get_condition()
        
        if isinstance(data, list):
            return [item for item in data if condition_fn(item)]
        elif condition_fn(data):
            return data
        else:
            return None
            
    def _get_condition(self) -> Callable:
        """Build filter condition from URI params"""
        field = self.uri.get_param('field')
        min_val = self.uri.get_param('min')
        max_val = self.uri.get_param('max')
        equals = self.uri.get_param('equals')
        
        def condition(item: Any) -> bool:
            if not isinstance(item, dict):
                return True
                
            if field not in item:
                return True
                
            value = item[field]
            
            if min_val is not None and value < min_val:
                return False
            if max_val is not None and value > max_val:
                return False
            if equals is not None and value != equals:
                return False
                
            return True
            
        return condition

