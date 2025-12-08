from typing import Any, Dict, List, Callable
import functools
from ..flow import flow, Flow
from ...diagnostics import get_logger


logger = get_logger(__name__)


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
