import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions
from curllm_core.llm_dsl.atoms import AtomResult

from .field_mapping import FieldMapping
from .form_fill_result import FormFillResult
from ._extract_values_with_llm import _extract_values_with_llm
from ._trigger_field_events import _trigger_field_events

async def llm_form_fill(
    instruction: str,
    page,
    llm,
    run_logger=None,
) -> FormFillResult:
    """
    Fill form using LLM-driven field detection.
    
    NO HARDCODED KEYWORDS - LLM understands context.
    
    Args:
        instruction: User instruction with values (e.g., "email=test@example.com")
        page: Playwright page
        llm: LLM instance for intelligent detection
        run_logger: Optional logger
        
    Returns:
        FormFillResult with filled fields and status
    """
    errors = []
    filled_fields = []
    
    # Initialize LLM-DSL
    executor = DSLExecutor(page=page, llm=llm)
    atoms = AtomicFunctions(page=page, llm=llm)
    
    # Step 1: Parse user values from instruction using LLM
    user_values = await _extract_values_with_llm(instruction, llm)
    
    if run_logger:
        run_logger.log_text(f"📝 Extracted {len(user_values)} values from instruction")
    
    # Step 2: Analyze page to find form fields
    page_analysis = await atoms.analyze_page_structure()
    
    if not page_analysis.success or not page_analysis.data.get('stats', {}).get('forms', 0):
        errors.append("No forms found on page")
        return FormFillResult(success=False, filled_fields=[], submitted=False, errors=errors)
    
    # Step 3: For each user value, find matching field using LLM
    for key, value in user_values.items():
        if run_logger:
            run_logger.log_text(f"   🔍 Finding field for: {key}")
        
        # LLM finds the appropriate field based on purpose description
        result = await atoms.find_input_by_context(
            f"input field for {key} - looking for field where user would enter their {key}"
        )
        
        if result.success and result.data:
            selector = result.data.get('selector')
            
            # Fill the field
            try:
                await page.fill(selector, value)
                await _trigger_field_events(page, selector)
                
                filled_fields.append(FieldMapping(
                    user_key=key,
                    user_value=value,
                    field_selector=selector,
                    field_purpose=key,
                    confidence=result.confidence,
                ))
                
                if run_logger:
                    run_logger.log_text(f"   ✅ Filled {key}: {selector}")
                    
            except Exception as e:
                errors.append(f"Failed to fill {key}: {e}")
                if run_logger:
                    run_logger.log_text(f"   ❌ Failed to fill {key}: {e}")
        else:
            errors.append(f"Could not find field for: {key}")
            if run_logger:
                run_logger.log_text(f"   ⚠️ No field found for: {key}")
    
    # Step 4: Find and click submit button using LLM
    submitted = False
    if filled_fields:
        submit_result = await atoms.find_clickable_by_intent(
            "submit the form / send the message / confirm"
        )
        
        if submit_result.success and submit_result.data:
            submit_selector = submit_result.data.get('selector')
            try:
                await page.click(submit_selector)
                submitted = True
                if run_logger:
                    run_logger.log_text(f"   📤 Clicked submit: {submit_selector}")
            except Exception as e:
                errors.append(f"Failed to submit: {e}")
    
    # Step 5: Detect result message using LLM
    message = None
    if submitted:
        await page.wait_for_timeout(2000)  # Wait for response
        
        msg_result = await atoms.detect_message_type()
        if msg_result.success and msg_result.data:
            message = msg_result.data.get('text')
            msg_type = msg_result.data.get('type')
            
            if run_logger:
                run_logger.log_text(f"   📬 {msg_type}: {message}")
    
    success = len(filled_fields) > 0 and len(errors) == 0
    
    return FormFillResult(
        success=success,
        filled_fields=filled_fields,
        submitted=submitted,
        message=message,
        errors=errors if errors else None,
    )
