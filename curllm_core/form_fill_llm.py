"""
LLM-Driven Form Fill - No hardcoded keywords or selectors

Uses LLM to:
1. Understand field purposes from context
2. Match user values to fields
3. Detect success/error messages

This replaces the keyword-based approach in form_fill.py
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from curllm_core.llm_dsl import DSLExecutor, AtomicFunctions
from curllm_core.llm_dsl.atoms import AtomResult

logger = logging.getLogger(__name__)


@dataclass
class FieldMapping:
    """Mapping of user value to form field"""
    user_key: str       # What user called it (e.g., "email")
    user_value: str     # Value to fill
    field_selector: str # Found selector
    field_purpose: str  # LLM-detected purpose
    confidence: float


@dataclass 
class FormFillResult:
    """Result of form filling"""
    success: bool
    filled_fields: List[FieldMapping]
    submitted: bool
    message: Optional[str] = None
    errors: List[str] = None


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


async def _extract_values_with_llm(instruction: str, llm) -> Dict[str, str]:
    """
    Extract key-value pairs from instruction using LLM.
    
    NO HARDCODED PARSING - LLM understands the instruction.
    """
    prompt = f"""Extract key-value pairs from this form filling instruction.

Instruction: "{instruction}"

Return JSON with field names as keys and values to fill:
{{"field_name": "value", ...}}

Examples:
- "email=test@example.com, name=John" → {{"email": "test@example.com", "name": "John"}}
- "wypełnij formularz: imię Jan, telefon 123456" → {{"name": "Jan", "phone": "123456"}}

Return ONLY the JSON, no explanation."""

    try:
        response = await llm.agenerate([prompt])
        answer = response.generations[0][0].text.strip()
        
        # Clean markdown
        import re
        if '```' in answer:
            answer = re.sub(r'```\w*\n?', '', answer)
        
        import json
        return json.loads(answer)
    except Exception as e:
        logger.error(f"LLM value extraction failed: {e}")
        # Fallback: simple regex parsing
        return _simple_parse(instruction)


def _simple_parse(instruction: str) -> Dict[str, str]:
    """Simple fallback parser (no hardcoded field names)"""
    import re
    pairs = {}
    # Match any key=value pattern
    for match in re.finditer(r'(\w+)\s*[=:]\s*([^,;\n]+)', instruction):
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        if key and value:
            pairs[key] = value
    return pairs


async def _trigger_field_events(page, selector: str):
    """Trigger input events after filling field"""
    await page.evaluate("""(sel) => {
        const el = document.querySelector(sel);
        if (el) {
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            el.dispatchEvent(new Event('blur', {bubbles: true}));
        }
    }""", selector)


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

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
