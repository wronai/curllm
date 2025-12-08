from typing import Any, List, Callable, Optional, Iterator
import json
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register, create_component
from ..exceptions import ComponentError
from ...diagnostics import get_logger

logger = get_logger(__name__)


@register("split")
class SplitComponent(StreamComponent):
    """
    Split data into multiple items
    
    URI format:
        split://pattern?type=jsonpath|field|batch
        
    Examples:
        split://jsonpath?query=$.items[*]
        split://field?name=items
        split://batch?size=10
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Split each input item"""
        split_type = self.uri.get_param('type', 'jsonpath')
        
        if input_stream:
            for data in input_stream:
                yield from self._split_data(data, split_type)
        else:
            # No input stream, wait for process()
            pass
            
    def process(self, data: Any) -> List[Any]:
        """Split single data item into list"""
        split_type = self.uri.get_param('type', 'jsonpath')
        return list(self._split_data(data, split_type))
        
    def _split_data(self, data: Any, split_type: str) -> Iterator:
        """Split data based on type"""
        if split_type == 'jsonpath':
            query = self.uri.get_param('query', '$[*]')
            yield from self._split_jsonpath(data, query)
            
        elif split_type == 'field':
            field = self.uri.get_param('name', 'items')
            if isinstance(data, dict) and field in data:
                items = data[field]
                if isinstance(items, list):
                    yield from items
                else:
                    yield items
            else:
                yield data
                
        elif split_type == 'batch':
            size = self.uri.get_param('size', 10)
            if isinstance(data, list):
                for i in range(0, len(data), size):
                    yield data[i:i+size]
            else:
                yield data
        else:
            # Default: split list or yield single item
            if isinstance(data, list):
                yield from data
            else:
                yield data
                
    def _split_jsonpath(self, data: Any, query: str) -> Iterator:
        """Split using JSONPath (simplified)"""
        try:
            # Simple JSONPath implementation for common cases
            if query == '$[*]' or query == '$.items[*]':
                if isinstance(data, list):
                    yield from data
                elif isinstance(data, dict):
                    if 'items' in data and isinstance(data['items'], list):
                        yield from data['items']
                    else:
                        for value in data.values():
                            if isinstance(value, list):
                                yield from value
                                return
                        yield data
                else:
                    yield data
            else:
                # For complex queries, just return the data
                yield data
        except Exception as e:
            logger.error(f"JSONPath split error: {e}")
            yield data

