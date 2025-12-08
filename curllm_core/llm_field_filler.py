"""DEPRECATED: Use curllm_core.field_filling instead"""
from curllm_core.field_filling.filler import llm_guided_field_fill, _ask_llm_for_field_value, _fill_field_with_retry, _handle_consent_checkbox, _submit_form_with_validation, _parse_instruction_values, _get_canonical_field_name
__all__ = ['llm_guided_field_fill']
