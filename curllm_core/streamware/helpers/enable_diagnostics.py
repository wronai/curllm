from typing import Any, Dict, List, Callable
import functools
from ..flow import flow, Flow
from ..registry import list_components, list_schemes
from ...diagnostics import get_logger

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
