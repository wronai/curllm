"""
Component registry for dynamic component lookup
"""

from typing import Dict, Type, Callable, List, Optional
from .core import Component
from .uri import StreamwareURI
from .exceptions import RegistryError
from ..diagnostics import get_logger

logger = get_logger(__name__)

# Global component registry
_REGISTRY: Dict[str, Type[Component]] = {}


def register(scheme: str) -> Callable:
    """
    Decorator to register a component for a URI scheme
    
    Usage:
        @register("curllm")
        class CurLLMComponent(Component):
            ...
    
    Args:
        scheme: URI scheme to handle (e.g., "curllm", "http", "file")
        
    Returns:
        Decorator function
    """
    def decorator(component_class: Type[Component]) -> Type[Component]:
        if not issubclass(component_class, Component):
            raise RegistryError(
                f"Component {component_class.__name__} must inherit from Component"
            )
            
        if scheme in _REGISTRY:
            logger.warning(
                f"Overriding existing component for scheme '{scheme}': "
                f"{_REGISTRY[scheme].__name__} -> {component_class.__name__}"
            )
            
        _REGISTRY[scheme] = component_class
        logger.debug(f"Registered component '{component_class.__name__}' for scheme '{scheme}'")
        
        return component_class
        
    return decorator


def get_component(scheme: str) -> Optional[Type[Component]]:
    """
    Get component class for a URI scheme
    
    Args:
        scheme: URI scheme
        
    Returns:
        Component class or None if not found
    """
    return _REGISTRY.get(scheme)


def create_component(uri: str) -> Component:
    """
    Create component instance from URI string
    
    Args:
        uri: URI string (e.g., "curllm://browse?url=...")
        
    Returns:
        Component instance
        
    Raises:
        RegistryError: If no component found for scheme
    """
    streamware_uri = StreamwareURI(uri)
    component_class = get_component(streamware_uri.scheme)
    
    if not component_class:
        raise RegistryError(
            f"No component registered for scheme '{streamware_uri.scheme}'. "
            f"Available schemes: {list_schemes()}"
        )
        
    return component_class(streamware_uri)


def list_components() -> List[Dict[str, str]]:
    """
    List all registered components
    
    Returns:
        List of dicts with component info
    """
    components = []
    for scheme, component_class in _REGISTRY.items():
        components.append({
            "scheme": scheme,
            "class": component_class.__name__,
            "module": component_class.__module__,
            "input_mime": getattr(component_class, "input_mime", "unknown"),
            "output_mime": getattr(component_class, "output_mime", "unknown"),
        })
    return components


def list_schemes() -> List[str]:
    """
    List all registered URI schemes
    
    Returns:
        List of scheme names
    """
    return list(_REGISTRY.keys())


def list_available_components() -> List[str]:
    """
    List all available component schemes (alias for list_schemes)
    
    Returns:
        List of scheme names
    """
    return list_schemes()


def unregister(scheme: str) -> bool:
    """
    Unregister a component
    
    Args:
        scheme: URI scheme to unregister
        
    Returns:
        True if unregistered, False if not found
    """
    if scheme in _REGISTRY:
        del _REGISTRY[scheme]
        logger.debug(f"Unregistered scheme '{scheme}'")
        return True
    return False


def clear_registry():
    """Clear all registered components"""
    _REGISTRY.clear()
    logger.debug("Cleared component registry")
