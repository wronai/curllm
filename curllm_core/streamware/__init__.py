"""
Streamware - Component-based architecture for CurLLM

Inspired by Apache Camel, provides URI-based routing and composable pipelines.
"""

from .core import Component, StreamComponent, TransformComponent
from .uri import StreamwareURI
from .exceptions import (
    ComponentError, 
    ConnectionError, 
    ValidationError,
    URIError,
    RegistryError
)
from .registry import register, get_component, list_components, create_component
from .flow import flow, Flow
from .patterns import split, join, multicast, choose
from .helpers import (
    enable_diagnostics,
    pipeline,
    metrics,
    batch_process,
    describe_component,
    list_available_components
)
from .yaml_runner import YAMLFlowRunner, run_yaml_flow, validate_yaml_flow

# Auto-register built-in components
from .components import curllm, web, file, transform

__all__ = [
    # Core classes
    "Component",
    "StreamComponent",
    "TransformComponent",
    "StreamwareURI",
    
    # Exceptions
    "ComponentError",
    "ConnectionError",
    "ValidationError",
    "URIError",
    "RegistryError",
    
    # Registry
    "register",
    "get_component",
    "list_components",
    "create_component",
    
    # Flow builders
    "flow",
    "Flow",
    
    # Patterns
    "split",
    "join",
    "multicast",
    "choose",
    
    # Helpers
    "enable_diagnostics",
    "pipeline",
    "metrics",
    "batch_process",
    "describe_component",
    "list_available_components",
    
    # YAML Runner
    "YAMLFlowRunner",
    "run_yaml_flow",
    "validate_yaml_flow",
]
