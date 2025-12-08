from typing import Any, List, Callable, Optional, Iterator
import json
from ..core import Component, StreamComponent
from ..uri import StreamwareURI
from ..registry import register, create_component
from ..exceptions import ComponentError
from ...diagnostics import get_logger

logger = get_logger(__name__)


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

