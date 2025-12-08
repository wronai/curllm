import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions
from curllm_core.llm_dsl.atoms import AtomResult

from .field_mapping import FieldMapping
from .form_fill_result import FormFillResult
from ._trigger_field_events import _trigger_field_events

async def smart_form_fill(
    page,
    values: Dict[str, str],
    llm,
    submit: bool = True,
    run_logger=None,
) -> FormFillResult:
    """
    Smart form filling with explicit values dict.
    
    Args:
        page: Playwright page
        values: Dict of field purposes to values (e.g., {"email": "test@test.com"})
        llm: LLM instance
        submit: Whether to submit form after filling
        run_logger: Optional logger
        
    Returns:
        FormFillResult
    """
    atoms = AtomicFunctions(page=page, llm=llm)
    filled_fields = []
    errors = []
    
    for purpose, value in values.items():
        # LLM finds field by understanding purpose
        result = await atoms.find_input_by_context(
            f"form field for entering {purpose}"
        )
        
        if result.success and result.data:
            selector = result.data.get('selector')
            try:
                await page.fill(selector, value)
                await _trigger_field_events(page, selector)
                
                filled_fields.append(FieldMapping(
                    user_key=purpose,
                    user_value=value,
                    field_selector=selector,
                    field_purpose=purpose,
                    confidence=result.confidence,
                ))
            except Exception as e:
                errors.append(f"Failed to fill {purpose}: {e}")
        else:
            errors.append(f"No field found for: {purpose}")
    
    submitted = False
    if submit and filled_fields:
        submit_result = await atoms.find_clickable_by_intent("submit form")
        if submit_result.success:
            try:
                await page.click(submit_result.data.get('selector'))
                submitted = True
            except Exception as e:
                errors.append(f"Submit failed: {e}")
    
    return FormFillResult(
        success=len(filled_fields) > 0,
        filled_fields=filled_fields,
        submitted=submitted,
        errors=errors if errors else None,
    )
