"""
Core component base classes
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Iterator, Dict
from .uri import StreamwareURI
from .exceptions import ComponentError


class Component(ABC):
    """
    Base class for Streamware components
    
    Components process data based on URI parameters.
    They should be stateless and reusable.
    """
    
    # MIME types (can be overridden by subclasses)
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        """
        Initialize component with URI
        
        Args:
            uri: StreamwareURI object with routing info
        """
        self.uri = uri
        
    @abstractmethod
    def process(self, data: Any) -> Any:
        """
        Process input data and return output
        
        Args:
            data: Input data to process
            
        Returns:
            Processed output data
            
        Raises:
            ComponentError: If processing fails
        """
        pass
        
    async def process_async(self, data: Any) -> Any:
        """
        Async version of process (optional)
        
        Default implementation calls synchronous process()
        Override for true async processing
        """
        return self.process(data)
        
    def validate_input(self, data: Any) -> bool:
        """
        Validate input data (optional)
        
        Returns:
            True if valid, False otherwise
        """
        return True
        
    def validate_output(self, data: Any) -> bool:
        """
        Validate output data (optional)
        
        Returns:
            True if valid, False otherwise
        """
        return True
        
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get component metadata
        
        Returns:
            Dictionary with component info
        """
        return {
            "name": self.__class__.__name__,
            "scheme": self.uri.scheme,
            "operation": self.uri.operation,
            "input_mime": self.input_mime,
            "output_mime": self.output_mime,
        }
        
    def __or__(self, other):
        """
        Pipe operator support for chaining components
        
        Example:
            component1 | component2
        """
        from .flow import Flow
        if isinstance(other, str):
            # Create component from URI string
            from .registry import create_component
            other = create_component(other)
        return Flow([self, other])


class StreamComponent(Component):
    """
    Base class for streaming components
    
    Streaming components process data in chunks/batches
    using Python generators for memory efficiency.
    """
    
    @abstractmethod
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """
        Process stream of data
        
        Args:
            input_stream: Input iterator/generator
            
        Yields:
            Processed data chunks
            
        Raises:
            ComponentError: If streaming fails
        """
        pass
        
    def process(self, data: Any) -> Any:
        """
        Process single item by wrapping in stream
        
        Default implementation for compatibility
        """
        result = list(self.stream(iter([data])))
        return result[0] if result else None


class TransformComponent(Component):
    """
    Base class for transformation components
    
    Simpler interface for pure data transformations
    """
    
    @abstractmethod
    def transform(self, data: Any) -> Any:
        """Transform data"""
        pass
        
    def process(self, data: Any) -> Any:
        """Process by calling transform"""
        return self.transform(data)
