from typing import Any, Dict, List, Callable
import functools
from ..flow import flow, Flow
from ..registry import list_components, list_schemes
from ...diagnostics import get_logger

from .pipeline import pipeline

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
