"""
Form Fill module - Deterministic form filling with robust field detection
"""

from curllm_core.form_fill.parser import parse_form_pairs
from curllm_core.form_fill.field_filler import robust_fill_field

# Import deterministic_form_fill from the parent form_fill.py module
try:
    from curllm_core.form_fill_legacy import deterministic_form_fill
except ImportError:
    # Fallback: create a simple wrapper
    async def deterministic_form_fill(page, form_data: dict, **kwargs):
        """Fill form fields with provided data."""
        results = {}
        for field_name, value in form_data.items():
            try:
                filled = await robust_fill_field(page, field_name, value)
                results[field_name] = filled
            except Exception as e:
                results[field_name] = False
        return results

__all__ = [
    'parse_form_pairs',
    'robust_fill_field',
    'deterministic_form_fill',
]
