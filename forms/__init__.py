"""
Bulk Form Filler - curllm

Multi-URL form filling tool using curllm for automation
and LLM for intelligent field mapping.
"""

from .app import BulkFormFiller, FormResult, BulkFormResult

__all__ = ["BulkFormFiller", "FormResult", "BulkFormResult"]
__version__ = "1.0.0"
