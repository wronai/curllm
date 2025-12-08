"""
Form Fill module - Deterministic and LLM-driven form filling

Provides two approaches:
1. deterministic_form_fill - Uses heuristics (legacy)
2. llm_form_fill - Uses LLM for intelligent field detection (recommended)
"""

from curllm_core.form_fill.parser import parse_form_pairs
from curllm_core.form_fill.field_filler import robust_fill_field

# Legacy deterministic approach
try:
    from curllm_core.form_fill_legacy import deterministic_form_fill
except ImportError:
    async def deterministic_form_fill(page, form_data: dict, **kwargs):
        """Fill form fields with provided data (legacy)."""
        results = {}
        for field_name, value in form_data.items():
            try:
                filled = await robust_fill_field(page, field_name, value)
                results[field_name] = filled
            except Exception:
                results[field_name] = False
        return results

# NEW: LLM-driven approach (recommended)
try:
    from curllm_core.form_fill_llm import llm_form_fill, smart_form_fill
except ImportError:
    llm_form_fill = None
    smart_form_fill = None

__all__ = [
    'parse_form_pairs',
    'robust_fill_field',
    'deterministic_form_fill',
    # LLM-driven (recommended)
    'llm_form_fill',
    'smart_form_fill',
]
