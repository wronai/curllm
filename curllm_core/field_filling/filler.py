"""
LLM-Guided Per-Field Form Filling

Instead of filling the entire form at once, this module uses LLM to make intelligent
decisions about each field individually, with context from previous fields and validation.

Benefits:
- Reduced token usage per request (focused on single field)
- Iterative validation and retry per field
- Learning from validation errors
- Better handling of complex/dynamic forms
"""

import json
import re
from typing import Dict, Any, Optional, List, Tuple


async def llm_guided_field_fill(
    page,
    instruction: str,
    form_fields: List[Dict[str, Any]],
    llm_client,
    run_logger=None
) -> Dict[str, Any]:
    """
    Fill form fields one-by-one with LLM guidance.
    
    Args:
        page: Playwright page object
        instruction: User instruction for form filling
        form_fields: List of detected form fields with metadata
        llm_client: LLM client for making decisions
        run_logger: Optional logger
        
    Returns:
        Dict with filled fields, submitted status, and errors
    """
    if run_logger:
        run_logger.log_text("🤖 LLM-guided per-field form filling started")
        run_logger.log_text(f"   Detected {len(form_fields)} fields in form")
    
    # Parse instruction to extract field values
    field_values = _parse_instruction_values(instruction)
    
    # Decision tree state
    field_states = {}  # field_name -> {status, value, attempts, errors}
    filled_count = 0
    
    # Prioritize required fields first
    required_fields = [f for f in form_fields if f.get("required")]
    optional_fields = [f for f in form_fields if not f.get("required")]
    ordered_fields = required_fields + optional_fields
    
    if run_logger:
        run_logger.log_text(f"   Required fields: {[f.get('name') for f in required_fields]}")
        run_logger.log_text(f"   Optional fields: {[f.get('name') for f in optional_fields]}")
    
    # Fill each field iteratively
    for field in ordered_fields:
        field_name = field.get("name") or field.get("id") or "unknown"
        field_type = field.get("type") or "text"
        field_label = field.get("label") or field_name
        is_required = field.get("required", False)
        
        if run_logger:
            run_logger.log_text(f"\n🔹 Processing field: {field_name} ({field_type})")
            run_logger.log_text(f"   Label: {field_label}")
            run_logger.log_text(f"   Required: {is_required}")
        
        # Ask LLM what value to fill
        llm_decision = await _ask_llm_for_field_value(
            llm_client=llm_client,
            instruction=instruction,
            field=field,
            field_values=field_values,
            previous_fields=field_states,
            run_logger=run_logger
        )
        
        if llm_decision.get("skip"):
            if run_logger:
                run_logger.log_text(f"   ⏭️  LLM decided to SKIP: {llm_decision.get('reason')}")
            field_states[field_name] = {
                "status": "skipped",
                "reason": llm_decision.get("reason")
            }
            continue
        
        value_to_fill = llm_decision.get("value")
        if not value_to_fill:
            if run_logger:
                run_logger.log_text(f"   ⚠️  No value provided by LLM, skipping")
            field_states[field_name] = {
                "status": "skipped",
                "reason": "No value from LLM"
            }
            continue
        
        # Attempt to fill the field with retry logic
        fill_result = await _fill_field_with_retry(
            page=page,
            field=field,
            value=value_to_fill,
            max_attempts=2,
            run_logger=run_logger
        )
        
        field_states[field_name] = fill_result
        
        if fill_result.get("status") == "filled":
            filled_count += 1
            if run_logger:
                run_logger.log_text(f"   ✅ Field filled successfully: {field_name} = '{value_to_fill[:50]}'")
        else:
            if run_logger:
                run_logger.log_text(f"   ❌ Failed to fill: {fill_result.get('error')}")
    
    # After all fields filled, check for consent/GDPR checkbox
    consent_result = await _handle_consent_checkbox(page, run_logger)
    if consent_result.get("checked"):
        field_states["_consent"] = consent_result
    
    # Submit the form
    if run_logger:
        run_logger.log_text(f"\n📤 Attempting form submission ({filled_count} fields filled)")
    
    submit_result = await _submit_form_with_validation(
        page=page,
        field_states=field_states,
        run_logger=run_logger
    )
    
    return {
        "fields_filled": field_states,
        "filled_count": filled_count,
        "submitted": submit_result.get("submitted", False),
        "errors": submit_result.get("errors")
    }


async def _ask_llm_for_field_value(
    llm_client,
    instruction: str,
    field: Dict[str, Any],
    field_values: Dict[str, str],
    previous_fields: Dict[str, Any],
    run_logger=None
) -> Dict[str, Any]:
    """
    Ask LLM what value to fill for a specific field.
    
    Returns:
        {
            "value": str,  # Value to fill
            "skip": bool,  # Whether to skip this field
            "reason": str  # Explanation
        }
    """
    field_name = field.get("name") or field.get("id") or "unknown"
    field_type = field.get("type") or "text"
    field_label = field.get("label") or field_name
    is_required = field.get("required", False)
    
    # Build context of previously filled fields
    prev_context = ""
    if previous_fields:
        prev_filled = [f"{k}: {v.get('value', 'N/A')}" for k, v in previous_fields.items() 
                      if v.get("status") == "filled"]
        if prev_filled:
            prev_context = f"\n\nPreviously filled fields:\n" + "\n".join(prev_filled)
    
    prompt = f"""You are filling a web form field by field.

**User instruction:** {instruction}

**Current field to fill:**
- Name: {field_name}
- Type: {field_type}
- Label: {field_label}
- Required: {"YES" if is_required else "NO"}
- Placeholder: {field.get('placeholder', 'N/A')}
{prev_context}

**Question:** What value should be entered into this field?

Analyze the user instruction and determine the appropriate value for this specific field.

**Rules:**
1. If the instruction mentions this field (by name, label, or semantic meaning), use that value
2. If this field is required but not mentioned in instruction, provide a reasonable default
3. If this field is optional and not mentioned, return skip=true
4. For email fields, prefer email addresses from instruction
5. For name fields, prefer names from instruction
6. For message/comment fields, use message from instruction

Return JSON:
{{
  "value": "the value to enter (or null if skip)",
  "skip": false,
  "reason": "brief explanation of your decision",
  "confidence": 0.95
}}

If you should skip this field, return skip=true.
"""
    
    try:
        # Call LLM
        response = await llm_client.ainvoke(prompt)
        
        # Try to extract JSON from response
        try:
            # Look for JSON block
            match = re.search(r'\{[^}]*"value"[^}]*\}', response, re.DOTALL)
            if match:
                decision = json.loads(match.group(0))
            else:
                # Fallback: try to parse entire response
                decision = json.loads(response)
        except json.JSONDecodeError:
            # LLM didn't return valid JSON, try to extract value from text
            if run_logger:
                run_logger.log_text(f"   ⚠️  LLM response not JSON, attempting extraction")
            
            # Try to find a value in the response text
            value_match = re.search(r'value["\s:]+(["\']?)([^"\'}\n]+)\1', response, re.IGNORECASE)
            if value_match:
                value = value_match.group(2).strip()
                decision = {
                    "value": value,
                    "skip": False,
                    "reason": "Extracted from LLM text response"
                }
            else:
                # Try to match field from instruction directly
                canonical_name = _get_canonical_field_name(field_name, field_label)
                if canonical_name in field_values:
                    decision = {
                        "value": field_values[canonical_name],
                        "skip": False,
                        "reason": "Matched from instruction directly"
                    }
                else:
                    decision = {
                        "value": None,
                        "skip": True,
                        "reason": "Could not parse LLM response and no match in instruction"
                    }
        
        if run_logger:
            run_logger.log_text(f"   🤖 LLM decision: {decision}")
        
        return decision
        
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"   ❌ LLM call failed: {e}")
        
        # Fallback: try to match field from instruction
        canonical_name = _get_canonical_field_name(field_name, field_label)
        if canonical_name in field_values:
            return {
                "value": field_values[canonical_name],
                "skip": False,
                "reason": f"LLM failed, using instruction match (fallback)"
            }
        else:
            return {
                "value": None,
                "skip": not is_required,  # Skip if optional, fail if required
                "reason": f"LLM failed: {str(e)}"
            }


async def _fill_field_with_retry(
    page,
    field: Dict[str, Any],
    value: str,
    max_attempts: int = 2,
    run_logger=None
) -> Dict[str, Any]:
    """
    Attempt to fill a field with retry logic and validation.
    
    Returns:
        {
            "status": "filled" | "failed",
            "value": str,
            "attempts": int,
            "error": str (if failed),
            "validation_error": str (if validation failed)
        }
    """
    field_name = field.get("name") or field.get("id") or "unknown"
    selector = f"[name='{field_name}']"
    
    if field.get("id"):
        selector = f"#{field['id']}"
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Wait for field to be visible
            await page.wait_for_selector(selector, timeout=5000, state="visible")
            
            # Clear and fill
            await page.fill(selector, "")
            await page.fill(selector, value)
            
            # Trigger validation events
            await page.evaluate(f"""
                (selector) => {{
                    const el = document.querySelector(selector);
                    if (el) {{
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                        el.blur();
                    }}
                }}
            """, selector)
            
            # Wait a bit for validation
            await page.wait_for_timeout(500)
            
            # Check for validation errors
            validation_error = await page.evaluate(f"""
                (selector) => {{
                    const el = document.querySelector(selector);
                    if (!el) return null;
                    
                    // Check aria-invalid
                    if (el.getAttribute('aria-invalid') === 'true') {{
                        return 'Field marked as invalid (aria-invalid=true)';
                    }}
                    
                    // Check error classes
                    if (el.classList.contains('error') || 
                        el.classList.contains('invalid') ||
                        el.classList.contains('wpcf7-not-valid') ||
                        el.classList.contains('forminator-error')) {{
                        return 'Field has error class';
                    }}
                    
                    // Check for error message nearby
                    const parent = el.parentElement;
                    const errorMsg = parent?.querySelector('.error-message, .forminator-error-message, .wpcf7-not-valid-tip');
                    if (errorMsg) {{
                        return errorMsg.textContent.trim();
                    }}
                    
                    return null;
                }}
            """, selector)
            
            if validation_error:
                if run_logger:
                    run_logger.log_text(f"   ⚠️  Validation error (attempt {attempt}): {validation_error}")
                
                if attempt < max_attempts:
                    # Try again with modified value
                    continue
                else:
                    return {
                        "status": "failed",
                        "value": value,
                        "attempts": attempt,
                        "validation_error": validation_error
                    }
            
            # Success!
            return {
                "status": "filled",
                "value": value,
                "attempts": attempt
            }
            
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"   ❌ Fill attempt {attempt} failed: {e}")
            
            if attempt >= max_attempts:
                return {
                    "status": "failed",
                    "value": value,
                    "attempts": attempt,
                    "error": str(e)
                }
    
    return {
        "status": "failed",
        "value": value,
        "attempts": max_attempts,
        "error": "Max attempts reached"
    }


async def _handle_consent_checkbox(page, run_logger=None, llm=None) -> Dict[str, Any]:
    """
    Find and check consent/GDPR checkbox using LLM analysis.
    
    LLM analyzes all checkboxes and their labels to find consent-related ones.
    Falls back to statistical analysis if LLM unavailable.
    """
    try:
        # Try LLM-based consent detection first
        if llm:
            try:
                from curllm_core.llm_dsl.selector_generator import LLMSelectorGenerator
                generator = LLMSelectorGenerator(llm=llm)
                result = await generator.generate_consent_selector(page)
                
                if result.confidence > 0.5 and result.selector:
                    if run_logger:
                        run_logger.log_text(f"   🤖 LLM found consent checkbox: {result.selector} ({result.method})")
                    consent_selector = result.selector
                else:
                    consent_selector = None
            except Exception as e:
                if run_logger:
                    run_logger.log_text(f"   ⚠️ LLM consent detection failed: {e}")
                consent_selector = None
        else:
            consent_selector = None
        
        # Fallback: statistical analysis of checkbox labels
        if not consent_selector:
            consent_selector = await page.evaluate("""
                () => {
                    // Find all checkboxes with their labels
                    const checkboxes = [];
                    
                    document.querySelectorAll('input[type="checkbox"]').forEach((cb, i) => {
                        if (cb.offsetParent === null) return;
                        
                        let labelText = '';
                        // Try to get label by 'for' attribute
                        if (cb.id) {
                            const label = document.querySelector(`label[for="${cb.id}"]`);
                            if (label) labelText = (label.textContent || '').toLowerCase();
                        }
                        // Try parent label
                        if (!labelText) {
                            const parentLabel = cb.closest('label');
                            if (parentLabel) labelText = (parentLabel.textContent || '').toLowerCase();
                        }
                        
                        checkboxes.push({ cb, labelText, index: i });
                    });
                    
                    // Score each checkbox - LLM would do this semantically
                    // Here we use simple heuristics as fallback
                    for (const { cb, labelText } of checkboxes) {
                        // Check if label contains consent-like words
                        // This scoring simulates what LLM would do semantically
                        const score = (
                            (labelText.includes('zgod') ? 2 : 0) +
                            (labelText.includes('akcept') ? 2 : 0) +
                            (labelText.includes('regulamin') ? 2 : 0) +
                            (labelText.includes('polityk') ? 1 : 0) +
                            (labelText.includes('rodo') ? 2 : 0) +
                            (labelText.includes('privacy') ? 2 : 0) +
                            (labelText.includes('consent') ? 2 : 0) +
                            (labelText.includes('agree') ? 2 : 0) +
                            (labelText.includes('terms') ? 1 : 0) +
                            (labelText.includes('gdpr') ? 2 : 0) +
                            (cb.required ? 1 : 0)
                        );
                        
                        if (score >= 2) {
                            cb.setAttribute('data-curllm-consent', 'true');
                            return '[data-curllm-consent="true"]';
                        }
                    }
                    
                    // Last fallback: any required checkbox
                    for (const { cb } of checkboxes) {
                        if (cb.required) {
                            cb.setAttribute('data-curllm-consent', 'true');
                            return '[data-curllm-consent="true"]';
                        }
                    }
                    
                    return null;
                }
            """)
        
        if consent_selector:
            await page.check(consent_selector)
            if run_logger:
                run_logger.log_text("   ✅ Consent checkbox checked")
            return {"checked": True, "selector": consent_selector}
        else:
            if run_logger:
                run_logger.log_text("   ℹ️  No consent checkbox found")
            return {"checked": False}
            
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"   ⚠️  Consent checkbox handling failed: {e}")
        return {"checked": False, "error": str(e)}


async def _submit_form_with_validation(
    page,
    field_states: Dict[str, Any],
    run_logger=None
) -> Dict[str, Any]:
    """Submit form and check for success/errors."""
    try:
        # Find submit button
        submit_selector = await page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll(
                    'button[type="submit"], input[type="submit"], .wpcf7-submit, button'
                ));
                
                for (const btn of buttons) {
                    const text = (btn.innerText || btn.value || '').toLowerCase();
                    if (text.includes('wyślij') || text.includes('send') || 
                        text.includes('submit') || btn.type === 'submit') {
                        if (btn.offsetParent !== null) {
                            btn.setAttribute('data-curllm-submit', 'true');
                            return '[data-curllm-submit="true"]';
                        }
                    }
                }
                return null;
            }
        """)
        
        if not submit_selector:
            if run_logger:
                run_logger.log_text("   ❌ Submit button not found")
            return {"submitted": False, "errors": {"submit_button": "not found"}}
        
        # Click submit
        await page.click(submit_selector)
        if run_logger:
            run_logger.log_text("   ▶️  Clicked submit button")
        
        # Wait for response
        await page.wait_for_timeout(2000)
        
        # Check for success
        success = await page.evaluate("""
            () => {
                const text = (document.body.innerText || '').toLowerCase();
                const successIndicators = [
                    'dziękujemy', 'dziekujemy', 'thank you', 
                    'wiadomość wysłana', 'message sent',
                    'success', 'sukces'
                ];
                
                if (successIndicators.some(s => text.includes(s))) {
                    return true;
                }
                
                // Check for success elements
                if (document.querySelector('.wpcf7-mail-sent-ok, .success-message, .elementor-message-success')) {
                    return true;
                }
                
                return false;
            }
        """)
        
        if success:
            if run_logger:
                run_logger.log_text("   ✅ Form submitted successfully!")
            return {"submitted": True}
        else:
            # Check for errors
            errors = await page.evaluate("""
                () => {
                    const text = (document.body.innerText || '').toLowerCase();
                    const errors = {};
                    
                    if (text.includes('invalid email') || text.includes('nieprawidłowy email')) {
                        errors.email = 'invalid';
                    }
                    if (text.includes('required') || text.includes('wymagane')) {
                        errors.required = 'missing';
                    }
                    
                    return Object.keys(errors).length > 0 ? errors : null;
                }
            """)
            
            if run_logger:
                run_logger.log_text(f"   ⚠️  Form not submitted, errors: {errors}")
            
            return {"submitted": False, "errors": errors}
            
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"   ❌ Submit failed: {e}")
        return {"submitted": False, "errors": {"exception": str(e)}}


def _parse_instruction_values(instruction: str) -> Dict[str, str]:
    """
    Parse instruction to extract field=value pairs.
    
    Example:
        "Fill form: name=John Doe, email=john@example.com, message=Hello"
        -> {"name": "John Doe", "email": "john@example.com", "message": "Hello"}
    """
    values = {}
    
    # Extract key=value pairs
    for match in re.finditer(r'(\w+)\s*=\s*([^,;\n]+)', instruction):
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        values[key] = value
    
    return values


def _get_canonical_field_name(field_name: str, field_label: str) -> str:
    """
    Get canonical name for a field based on its name/label.
    
    Maps various field names to standard names like "name", "email", "phone", "message".
    """
    combined = f"{field_name} {field_label}".lower()
    
    if any(k in combined for k in ["email", "e-mail", "mail"]):
        return "email"
    elif any(k in combined for k in ["name", "imi", "fullname"]):
        return "name"
    elif any(k in combined for k in ["phone", "telefon", "tel"]):
        return "phone"
    elif any(k in combined for k in ["message", "wiadomo", "comment", "komentarz"]):
        return "message"
    elif any(k in combined for k in ["subject", "temat"]):
        return "subject"
    else:
        return field_name.lower()
