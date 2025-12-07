"""
Price Comparator - curllm

Multi-URL price comparison tool using curllm for extraction
and LLM for comparative analysis.
"""

from .app import PriceComparator, ExtractionResult, ComparisonResult

__all__ = ["PriceComparator", "ExtractionResult", "ComparisonResult"]
__version__ = "1.0.0"
