"""
Function Registry

Manages discovery, registration, and execution of atomic functions.

Usage:
    from functions.registry import register_function, get_function
    
    @register_function(name="my_func", category="extractors")
    def my_func(x):
        return x * 2
    
    func = get_function("extractors.my_func")
    result = func(5)  # Returns 10
"""

import json
import logging
import importlib
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class FunctionInfo:
    """Metadata about a registered function."""
    
    name: str
    category: str
    func: Callable
    description: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)
    parameters: List[Dict[str, str]] = field(default_factory=list)
    return_type: str = "Any"
    source_file: str = ""
    is_async: bool = False
    tags: List[str] = field(default_factory=list)
    
    @property
    def full_name(self) -> str:
        return f"{self.category}.{self.name}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "full_name": self.full_name,
            "description": self.description,
            "examples": self.examples,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "is_async": self.is_async,
            "tags": self.tags,
        }
    
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class FunctionRegistry:
    """Registry for atomic functions."""
    
    _instance: Optional["FunctionRegistry"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._functions: Dict[str, FunctionInfo] = {}
            cls._instance._categories: Dict[str, List[str]] = {}
        return cls._instance
    
    def register(
        self,
        func: Callable,
        name: str,
        category: str,
        description: str = "",
        examples: List[Dict] = None,
        tags: List[str] = None,
    ) -> FunctionInfo:
        """
        Register a function.
        
        Args:
            func: The function to register
            name: Function name
            category: Category (extractors, validators, etc.)
            description: Human-readable description
            examples: List of {input, output} examples
            tags: Optional tags for filtering
            
        Returns:
            FunctionInfo object
        """
        # Extract parameter info from signature
        sig = inspect.signature(func)
        parameters = []
        for param_name, param in sig.parameters.items():
            param_info = {"name": param_name}
            if param.annotation != inspect.Parameter.empty:
                param_info["type"] = str(param.annotation.__name__ 
                    if hasattr(param.annotation, '__name__') 
                    else str(param.annotation))
            if param.default != inspect.Parameter.empty:
                param_info["default"] = str(param.default)
            parameters.append(param_info)
        
        # Get return type
        return_type = "Any"
        if sig.return_annotation != inspect.Signature.empty:
            return_type = str(sig.return_annotation.__name__ 
                if hasattr(sig.return_annotation, '__name__') 
                else str(sig.return_annotation))
        
        # Get source file
        source_file = ""
        try:
            source_file = inspect.getfile(func)
        except Exception:
            pass
        
        info = FunctionInfo(
            name=name,
            category=category,
            func=func,
            description=description or func.__doc__ or "",
            examples=examples or [],
            parameters=parameters,
            return_type=return_type,
            source_file=source_file,
            is_async=inspect.iscoroutinefunction(func),
            tags=tags or [],
        )
        
        full_name = f"{category}.{name}"
        self._functions[full_name] = info
        
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)
        
        logger.debug(f"Registered function: {full_name}")
        return info
    
    def get(self, full_name: str) -> Optional[FunctionInfo]:
        """Get a function by full name (category.name)."""
        return self._functions.get(full_name)
    
    def list(self, category: str = None) -> List[FunctionInfo]:
        """List all functions, optionally filtered by category."""
        if category:
            names = self._categories.get(category, [])
            return [self._functions[f"{category}.{n}"] for n in names]
        return list(self._functions.values())
    
    def list_by_tag(self, tag: str) -> List[FunctionInfo]:
        """List functions with a specific tag."""
        return [f for f in self._functions.values() if tag in f.tags]
    
    def categories(self) -> List[str]:
        """List all categories."""
        return list(self._categories.keys())
    
    def search(self, query: str) -> List[FunctionInfo]:
        """Search functions by name or description."""
        query_lower = query.lower()
        results = []
        for func in self._functions.values():
            if (query_lower in func.name.lower() or 
                query_lower in func.description.lower() or
                any(query_lower in tag.lower() for tag in func.tags)):
                results.append(func)
        return results
    
    def export_catalog(self, filepath: str):
        """Export function catalog to JSON."""
        catalog = {
            "categories": self._categories,
            "functions": {
                name: info.to_dict() 
                for name, info in self._functions.items()
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        logger.info(f"Exported {len(self._functions)} functions to {filepath}")


# Global registry instance
_registry = FunctionRegistry()


def register_function(
    name: str = None,
    category: str = "general",
    description: str = "",
    examples: List[Dict] = None,
    tags: List[str] = None,
):
    """
    Decorator to register a function.
    
    Args:
        name: Function name (defaults to function.__name__)
        category: Category for grouping
        description: Human-readable description
        examples: List of {input, output} examples
        tags: Optional tags
    
    Example:
        @register_function(category="extractors", tags=["price"])
        def extract_price(text: str) -> float:
            ...
    """
    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__
        _registry.register(
            func=func,
            name=func_name,
            category=category,
            description=description,
            examples=examples,
            tags=tags,
        )
        return func
    return decorator


def get_function(full_name: str) -> Optional[FunctionInfo]:
    """
    Get a function by full name.
    
    Args:
        full_name: Full function name (category.name)
        
    Returns:
        FunctionInfo or None
    """
    return _registry.get(full_name)


def list_functions(category: str = None) -> List[FunctionInfo]:
    """
    List available functions.
    
    Args:
        category: Optional category filter
        
    Returns:
        List of FunctionInfo objects
    """
    return _registry.list(category)


def get_registry() -> FunctionRegistry:
    """Get the global function registry."""
    return _registry
