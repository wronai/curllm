"""
Detection module - Dynamic pattern detection

Classes for detecting dynamic content patterns in DOM,
including field extraction and pattern analysis.
"""

from curllm_core.detection.detector import (
    DOMNode,
    DynamicPatternDetector,
    GenericFieldExtractor,
    dynamic_extract,
)

__all__ = [
    'DOMNode',
    'DynamicPatternDetector',
    'GenericFieldExtractor',
    'dynamic_extract',
]
