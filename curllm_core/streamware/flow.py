"""
Flow builder for composable pipelines
"""

from typing import Any, List, Optional, Iterator, Union
from .core import Component, StreamComponent
from .registry import create_component
from .exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)



class Flow:
    """
    Flow builder for composable component pipelines
    
    Supports both synchronous and streaming execution.
    
    Usage:
        # Synchronous
        result = flow("http://api.example.com/data") | "transform://json" | "file://write"
        result.run()
        
        # Streaming
        for item in flow("kafka://consume?topic=events") | "transform://json":
            process(item)
    """
    
    def __init__(self, components: Optional[List[Union[Component, str]]] = None):
        """
        Initialize flow with optional components
        
        Args:
            components: List of Component instances or URI strings
        """
        self.components: List[Component] = []
        self._input_data: Any = None
        self._diagnostics_enabled = False
        
        if components:
            for comp in components:
                if isinstance(comp, str):
                    self.components.append(create_component(comp))
                else:
                    self.components.append(comp)
                    
    def with_data(self, data: Any) -> 'Flow':
        """
        Set input data for the flow
        
        Args:
            data: Input data
            
        Returns:
            Self for chaining
        """
        self._input_data = data
        return self
        
    def with_diagnostics(self, enabled: bool = True) -> 'Flow':
        """
        Enable diagnostics for the flow
        
        Args:
            enabled: Enable diagnostics
            
        Returns:
            Self for chaining
        """
        self._diagnostics_enabled = enabled
        return self
        
    def __or__(self, other: Union[Component, str, 'Flow']) -> 'Flow':
        """
        Pipe operator for chaining components
        
        Args:
            other: Component, URI string, or another Flow
            
        Returns:
            New Flow with added component
        """
        new_flow = Flow(self.components.copy())
        new_flow._input_data = self._input_data
        new_flow._diagnostics_enabled = self._diagnostics_enabled
        
        if isinstance(other, str):
            new_flow.components.append(create_component(other))
        elif isinstance(other, Flow):
            new_flow.components.extend(other.components)
        else:
            new_flow.components.append(other)
            
        return new_flow
        
    def run(self, input_data: Any = None) -> Any:
        """
        Execute flow synchronously
        
        Args:
            input_data: Optional input data (overrides with_data)
            
        Returns:
            Final output data
            
        Raises:
            ComponentError: If any component fails
        """
        data = input_data if input_data is not None else self._input_data
        
        if self._diagnostics_enabled:
            logger.info(f"Starting flow with {len(self.components)} components")
            
        for i, component in enumerate(self.components):
            try:
                if self._diagnostics_enabled:
                    logger.debug(
                        f"[{i+1}/{len(self.components)}] Processing: "
                        f"{component.__class__.__name__} ({component.uri.scheme})"
                    )
                    
                data = component.process(data)
                
                if self._diagnostics_enabled:
                    logger.debug(f"[{i+1}/{len(self.components)}] Output type: {type(data).__name__}")
                    
            except Exception as e:
                logger.error(
                    f"Error in component {component.__class__.__name__} "
                    f"at position {i+1}: {e}"
                )
                raise ComponentError(
                    f"Flow execution failed at component {i+1} "
                    f"({component.__class__.__name__}): {e}"
                ) from e
                
        if self._diagnostics_enabled:
            logger.info("Flow completed successfully")
            
        return data
        
    def stream(self, input_stream: Optional[Iterator] = None) -> Iterator:
        """
        Execute flow as stream
        
        Args:
            input_stream: Optional input iterator
            
        Yields:
            Processed data items
            
        Raises:
            ComponentError: If any component fails
        """
        if not self.components:
            return iter(())
            
        current_stream = input_stream
        
        for i, component in enumerate(self.components):
            try:
                current_stream = self._apply_component_stream(component, current_stream)
            except Exception as e:
                logger.error(f"Error in streaming component {i+1}: {e}")
                raise ComponentError(
                    f"Stream execution failed at component {i+1}: {e}"
                ) from e
                
        # Yield from final stream
        if current_stream:
            yield from current_stream
        
    def _apply_component_stream(
        self, component: Component, current_stream: Optional[Iterator]
    ) -> Iterator:
        if isinstance(component, StreamComponent):
            return component.stream(current_stream)
        return self._wrap_non_stream_component(component, current_stream)

    @staticmethod
    def _wrap_non_stream_component(
        component: Component, stream: Optional[Iterator]
    ) -> Iterator:
        if stream:
            for item in stream:
                yield component.process(item)
        else:
            yield component.process(None)
            
    async def run_async(self, input_data: Any = None) -> Any:
        """
        Execute flow asynchronously
        
        Args:
            input_data: Optional input data
            
        Returns:
            Final output data
        """
        data = input_data if input_data is not None else self._input_data
        
        for i, component in enumerate(self.components):
            try:
                data = await component.process_async(data)
            except Exception as e:
                raise ComponentError(
                    f"Async flow execution failed at component {i+1}: {e}"
                ) from e
                
        return data
        
    def add(self, component: Union[Component, str]) -> 'Flow':
        """
        Add component to flow
        
        Args:
            component: Component instance or URI string
            
        Returns:
            Self for chaining
        """
        if isinstance(component, str):
            self.components.append(create_component(component))
        else:
            self.components.append(component)
        return self
        
    def __len__(self) -> int:
        """Get number of components in flow"""
        return len(self.components)
        
    def __repr__(self) -> str:
        component_names = [c.__class__.__name__ for c in self.components]
        return f"Flow({' | '.join(component_names)})"


def flow(uri: Union[str, Component]) -> Flow:
    """
    Create a new flow starting with a component
    
    Args:
        uri: Component URI string or Component instance
        
    Returns:
        Flow instance
        
    Example:
        flow("http://api.example.com/data") | "transform://json" | "file://write"
    """
    if isinstance(uri, str):
        return Flow([create_component(uri)])
    return Flow([uri])
