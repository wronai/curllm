"""
Advanced workflow patterns (split, join, multicast, choose)
"""

from typing import Any, List, Callable, Optional, Iterator
import json
from .core import Component, StreamComponent
from .uri import StreamwareURI
from .registry import register, create_component
from .exceptions import ComponentError
from ..diagnostics import get_logger

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


@register("multicast")
class MulticastComponent(Component):
    """
    Send data to multiple destinations
    
    URI format:
        multicast://parallel?destinations=uri1,uri2,uri3
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> List[Any]:
        """Send to all destinations and collect results"""
        destinations = self.uri.get_param('destinations', [])
        
        if isinstance(destinations, str):
            destinations = [d.strip() for d in destinations.split(',')]
            
        if not destinations:
            logger.warning("Multicast has no destinations")
            return [data]
            
        results = []
        
        for dest_uri in destinations:
            try:
                component = create_component(dest_uri)
                result = component.process(data)
                results.append(result)
            except Exception as e:
                logger.error(f"Multicast destination {dest_uri} failed: {e}")
                results.append({"error": str(e), "destination": dest_uri})
                
        return results


@register("choose")
class ChooseComponent(Component):
    """
    Conditional routing (choice/switch pattern)
    
    URI format:
        choose://condition?field=status&routes={"high":"uri1","low":"uri2"}
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self._conditions: List[tuple] = []  # (condition_fn, component)
        self._otherwise: Optional[Component] = None
        
    def when(self, condition: str, destination: str) -> 'ChooseComponent':
        """
        Add conditional route
        
        Args:
            condition: Condition expression (e.g., "$.priority == 'high'")
            destination: Destination URI
            
        Returns:
            Self for chaining
        """
        condition_fn = self._compile_condition(condition)
        component = create_component(destination)
        self._conditions.append((condition_fn, component))
        return self
        
    def otherwise(self, destination: str) -> 'ChooseComponent':
        """
        Set default route
        
        Args:
            destination: Default destination URI
            
        Returns:
            Self for chaining
        """
        self._otherwise = create_component(destination)
        return self
        
    def process(self, data: Any) -> Any:
        """Route data based on conditions"""
        for condition_fn, component in self._conditions:
            if condition_fn(data):
                return component.process(data)
                
        # No condition matched, use otherwise
        if self._otherwise:
            return self._otherwise.process(data)
            
        # No otherwise, return data unchanged
        return data
        
    def _compile_condition(self, condition: str) -> Callable:
        """
        Compile condition string to callable
        
        Simple implementation for basic conditions
        """
        def evaluate(data: Any) -> bool:
            try:
                # Handle JSONPath-like conditions
                if '==' in condition:
                    parts = condition.split('==')
                    field_path = parts[0].strip().replace('$.', '').replace('$', '')
                    expected_value = parts[1].strip().strip('"').strip("'")
                    
                    # Get field value
                    if isinstance(data, dict):
                        value = data.get(field_path)
                        return str(value) == expected_value
                        
                return False
            except Exception as e:
                logger.error(f"Condition evaluation error: {e}")
                return False
                
        return evaluate


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


# Helper functions

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
