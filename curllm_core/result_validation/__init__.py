"""
Result Validation module - Form and action result validation

Classes for validating results of form submissions
and other browser actions.
"""

from curllm_core.result_validation.validator import (
    ValidationLevel,
    ValidationResult,
    ResultValidator,
    validate_form_result,
    validate_strict,
)

__all__ = [
    'ValidationLevel',
    'ValidationResult',
    'ResultValidator',
    'validate_form_result',
    'validate_strict',
]
