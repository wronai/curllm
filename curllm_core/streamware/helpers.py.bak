"""
Helper utilities for Streamware
"""

from typing import Any, Dict, List, Callable
import functools
from .flow import flow, Flow
from .registry import list_components, list_schemes
from ..diagnostics import get_logger

logger = get_logger(__name__)


def enable_diagnostics(level: str = "INFO"):
    """
    Enable diagnostics logging
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    import logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.info(f"Diagnostics enabled at {level} level")


def describe_component(scheme: str) -> Dict[str, Any]:
    """
    Get detailed information about a component
    
    Args:
        scheme: Component scheme
        
    Returns:
        Component metadata
    """
    components = list_components()
    
    for comp in components:
        if comp['scheme'] == scheme:
            return comp
            
    return None


def list_available_components() -> List[str]:
    """
    List all available component schemes
    
    Returns:
        List of scheme names
    """
    return list_schemes()


def pipeline(*steps: str) -> Flow:
    """
    Create a pipeline from multiple URI steps
    
    Args:
        *steps: URI strings for each step
        
    Returns:
        Flow instance
        
    Example:
        pipeline(
            "http://api.example.com/data",
            "transform://jsonpath?query=$.items",
            "file://write?path=output.json"
        )
    """
    if not steps:
        raise ValueError("Pipeline requires at least one step")
        
    result = flow(steps[0])
    
    for step in steps[1:]:
        result = result | step
        
    return result


def compose(*functions: Callable) -> Callable:
    """
    Compose multiple functions into a single function
    
    Args:
        *functions: Functions to compose
        
    Returns:
        Composed function
        
    Example:
        f = compose(func1, func2, func3)
        result = f(data)  # Equivalent to func3(func2(func1(data)))
    """
    def composed(data):
        result = data
        for func in functions:
            result = func(result)
        return result
        
    return composed


def retry(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator to retry component operations
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between attempts in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {e}"
                    )
                    
                    if attempt < max_attempts - 1:
                        time.sleep(delay)
                        
            raise last_exception
            
        return wrapper
        
    return decorator


def validate_data(schema: Dict[str, Any]) -> Callable:
    """
    Decorator to validate input/output data against a schema
    
    Args:
        schema: JSON schema for validation
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, data):
            # Simple validation (can be extended with jsonschema library)
            if not isinstance(data, dict):
                logger.warning(f"Expected dict, got {type(data).__name__}")
                
            result = func(self, data)
            
            return result
            
        return wrapper
        
    return decorator


class Metrics:
    """
    Simple metrics collection for pipelines
    """
    
    def __init__(self):
        self._metrics = {}
        
    def track(self, name: str):
        """Context manager for tracking pipeline metrics"""
        import time
        
        class MetricsContext:
            def __init__(ctx_self, metrics_obj, metric_name):
                ctx_self.metrics = metrics_obj
                ctx_self.name = metric_name
                ctx_self.start_time = None
                
            def __enter__(ctx_self):
                ctx_self.start_time = time.time()
                return ctx_self
                
            def __exit__(ctx_self, exc_type, exc_val, exc_tb):
                duration = time.time() - ctx_self.start_time
                
                if ctx_self.name not in ctx_self.metrics._metrics:
                    ctx_self.metrics._metrics[ctx_self.name] = {
                        'processed': 0,
                        'errors': 0,
                        'total_time': 0.0,
                        'avg_time': 0.0
                    }
                    
                stats = ctx_self.metrics._metrics[ctx_self.name]
                stats['processed'] += 1
                stats['total_time'] += duration
                stats['avg_time'] = stats['total_time'] / stats['processed']
                
                if exc_type is not None:
                    stats['errors'] += 1
                    
                return False  # Don't suppress exceptions
                
        return MetricsContext(self, name)
        
    def get_stats(self, name: str) -> Dict[str, Any]:
        """Get metrics for a pipeline"""
        return self._metrics.get(name, {})
        
    def reset(self, name: str = None):
        """Reset metrics"""
        if name:
            self._metrics.pop(name, None)
        else:
            self._metrics.clear()
            
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics"""
        return self._metrics.copy()


# Global metrics instance
metrics = Metrics()


def batch_process(items: List[Any], pipeline_uri: str, batch_size: int = 10) -> List[Any]:
    """
    Process items in batches through a pipeline
    
    Args:
        items: List of items to process
        pipeline_uri: Pipeline URI or Flow
        batch_size: Batch size
        
    Returns:
        List of results
    """
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        try:
            if isinstance(pipeline_uri, str):
                pipe = flow(pipeline_uri)
            else:
                pipe = pipeline_uri
                
            result = pipe.run(batch)
            
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)
                
        except Exception as e:
            logger.error(f"Batch processing error at index {i}: {e}")
            results.append({"error": str(e), "batch_index": i})
            
    return results
