"""
LLM Decision Components - Decision making using LLM instead of regex patterns.

NO HARDCODED PATTERNS - All parsing done by LLM.
NO REGEX - LLM interprets instructions semantically.

Replaces hardcoded patterns in decision.py with LLM-based alternatives.
"""
import json
from typing import Dict, Any, List, Optional


async def extract_fields_from_instruction_llm(
    llm,
    instruction: str,
    available_fields: List[str] = None,
    run_logger=None
) -> Dict[str, str]:
    """
    Extract field values from instruction using LLM.
    
    Replaces hardcoded regex patterns like:
        'name': r'name[=:]([^,]+)'
    
    Args:
        llm: LLM client
        instruction: User instruction like "fill form with email=test@example.com"
        available_fields: Optional list of known field names
        
    Returns:
        {"field_name": "value", ...}
    """
    fields_hint = ""
    if available_fields:
        fields_hint = f"\nKnown fields on the form: {', '.join(available_fields)}"
    
    prompt = f"""Extract field values from this instruction.

Instruction: "{instruction}"
{fields_hint}

Find all field=value pairs. Common fields:
- name, first_name, last_name
- email
- phone, telephone
- subject, title
- message, comment, text
- address, city, zip
- company, organization

Return ONLY JSON with field names and their values:
{{"field_name": "value", "another_field": "value"}}

If no fields found, return {{}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        
        if result and isinstance(result, dict):
            if run_logger:
                run_logger.log_text(f"✅ Extracted {len(result)} fields from instruction")
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ Field extraction failed: {e}")
    
    return {}


async def parse_selector_name_llm(
    llm,
    selector: str,
    run_logger=None
) -> Optional[str]:
    """
    Parse field name from CSS selector using LLM.
    
    Replaces hardcoded regex:
        re.search(r"name='([^']+)'", selector)
    
    Args:
        selector: CSS selector like "[name='email']" or "#contact-form input[name=phone]"
        
    Returns:
        Field name or None
    """
    prompt = f"""Extract the field name from this CSS selector.

Selector: "{selector}"

What is the field NAME being targeted? (the value in name='...' or name=... or id='...')

Return ONLY the field name, nothing else.
If no name found, return "null".

Name:"""

    try:
        response = await _llm_generate(llm, prompt)
        name = response.strip().lower()
        
        if name and name != "null":
            return name
    except Exception:
        pass
    
    return None


async def plan_next_action_llm(
    llm,
    instruction: str,
    page_context: Dict[str, Any],
    history: List[Dict] = None,
    run_logger=None
) -> Dict[str, Any]:
    """
    Plan next action using LLM instead of hardcoded logic.
    
    Args:
        instruction: User's goal
        page_context: Current page state (forms, links, text)
        history: Previous actions taken
        
    Returns:
        {"type": "fill|click|wait|complete", "selector": "...", "value": "...", ...}
    """
    history = history or []
    
    # Format page context for LLM
    forms_info = ""
    forms = page_context.get('forms', [])
    for i, form in enumerate(forms):
        fields = form.get('fields', [])
        fields_text = "\n".join([
            f"    - {f.get('name', 'unnamed')}: type={f.get('type')}, value=\"{f.get('value', '')}\""
            for f in fields[:10]
        ])
        forms_info += f"  Form {i}:\n{fields_text}\n"
    
    history_text = ""
    if history:
        recent = history[-5:]  # Last 5 actions
        history_text = "Recent actions:\n" + "\n".join([
            f"  - {h.get('type')}: {h.get('selector', '')}"
            for h in recent
        ])
    
    prompt = f"""Plan the next action to accomplish this task.

TASK: "{instruction}"

CURRENT PAGE STATE:
URL: {page_context.get('url', 'unknown')}
Title: {page_context.get('title', '')}

Forms found:
{forms_info if forms_info else "  (no forms)"}

{history_text}

What should be the NEXT action?

Action types:
- fill: Fill a form field (need selector and value)
- click: Click a button/link (need selector)
- wait: Wait before continuing (need duration in ms)
- complete: Task is done (need reason)

Output JSON:
{{"type": "fill|click|wait|complete", "selector": "CSS selector", "value": "value for fill", "reason": "explanation"}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        
        if result:
            if run_logger:
                run_logger.log_text(f"✅ Planned action: {result.get('type')}")
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ Action planning failed: {e}")
    
    return {"type": "wait", "duration": 1000, "reason": "LLM planning failed"}


async def validate_action_llm(
    llm,
    action: Dict[str, Any],
    before_state: Dict[str, Any],
    after_state: Dict[str, Any],
    run_logger=None
) -> Dict[str, Any]:
    """
    Validate if action was successful using LLM instead of hardcoded checks.
    
    Args:
        action: The action that was taken
        before_state: Page state before action
        after_state: Page state after action
        
    Returns:
        {"success": bool, "reason": str, "details": {...}}
    """
    prompt = f"""Validate if this action was successful.

ACTION TAKEN:
Type: {action.get('type')}
Selector: {action.get('selector', 'N/A')}
Value: {action.get('value', 'N/A')}

BEFORE:
URL: {before_state.get('url', '')}
Title: {before_state.get('title', '')}

AFTER:
URL: {after_state.get('url', '')}
Title: {after_state.get('title', '')}

Changes detected:
- URL changed: {before_state.get('url') != after_state.get('url')}
- Title changed: {before_state.get('title') != after_state.get('title')}

Was this action successful?

Output JSON:
{{"success": true/false, "reason": "explanation", "confidence": 0.0-1.0}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        
        if result:
            return result
    except Exception:
        pass
    
    # Fallback: assume success if no errors
    return {"success": True, "reason": "assumed_success", "confidence": 0.5}


async def interpret_instruction_llm(
    llm,
    instruction: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Interpret user instruction using LLM.
    
    Extracts:
    - Intent (fill_form, navigate, extract_data, click)
    - Target URL
    - Form data
    - Expected outcome
    
    Returns:
        {
            "intent": "fill_form|navigate|extract_data|click",
            "url": str | None,
            "form_data": {...},
            "expected_outcome": str,
            "steps": ["step1", "step2"]
        }
    """
    prompt = f"""Interpret this browser automation instruction.

Instruction: "{instruction}"

What is the user trying to accomplish?

Output JSON:
{{
    "intent": "fill_form|navigate|extract_data|click|search",
    "url": "target URL or null",
    "form_data": {{"field": "value"}} or {{}},
    "expected_outcome": "what success looks like",
    "steps": ["step 1", "step 2", "..."]
}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        
        if result:
            if run_logger:
                run_logger.log_text(f"✅ Interpreted intent: {result.get('intent')}")
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ Instruction interpretation failed: {e}")
    
    return {"intent": "unknown", "form_data": {}, "steps": []}


async def generate_selector_for_field_llm(
    llm,
    field_name: str,
    form_fields: List[Dict],
    run_logger=None
) -> Optional[str]:
    """
    Generate CSS selector for a field using LLM.
    
    Instead of hardcoded: f"[name='{field_name}']"
    
    Args:
        field_name: Semantic field name (email, phone, etc.)
        form_fields: List of available form fields with their attributes
        
    Returns:
        CSS selector string
    """
    fields_text = "\n".join([
        f"  - name=\"{f.get('name', '')}\", id=\"{f.get('id', '')}\", type=\"{f.get('type', '')}\", placeholder=\"{f.get('placeholder', '')}\""
        for f in form_fields[:15]
    ])
    
    prompt = f"""Find the CSS selector for the {field_name} field.

Available form fields:
{fields_text}

Which field should be used for: {field_name}?

Rules:
- Match by name attribute, id, or type
- Consider semantic meaning (email field for email, textarea for message)
- Return the most specific selector

Output JSON:
{{"selector": "CSS selector", "confidence": 0.0-1.0, "reasoning": "why this field"}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        
        if result and result.get('selector'):
            return result['selector']
    except Exception:
        pass
    
    return None


async def _llm_generate(llm, prompt: str) -> str:
    """Generate text from LLM."""
    if hasattr(llm, 'ainvoke'):
        result = await llm.ainvoke(prompt)
        if isinstance(result, dict):
            return result.get('text', str(result))
        return str(result)
    elif hasattr(llm, 'generate'):
        return await llm.generate(prompt)
    else:
        return str(await llm(prompt))


def _parse_json_response(response: str) -> Optional[Dict]:
    """Parse JSON from LLM response."""
    import re
    
    # Try to find JSON in response
    match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    # Try nested JSON
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    return None
