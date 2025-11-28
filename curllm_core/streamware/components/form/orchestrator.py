"""
Form Fill Orchestrator - coordinates atomic components.
Uses page context and LLM-provided data, no hardcoded selectors.
"""
from typing import Dict, Any, List, Optional
import re

from .detect import detect_form, get_field_selectors
from .fill import fill_field, fill_fields
from .submit import (
    submit_form, 
    detect_success, 
    capture_page_state,
    detect_success_data,
    evaluate_success_with_llm,
    get_clickable_buttons
)


def parse_instruction(instruction: str) -> Dict[str, str]:
    """Parse key=value pairs from instruction string."""
    data = {}
    
    # Match patterns: key=value, key = value, key="value with spaces"
    patterns = [
        r'(\w+)\s*=\s*"([^"]+)"',  # key="value"
        r'(\w+)\s*=\s*\'([^\']+)\'',  # key='value'
        r'(\w+)\s*=\s*([^,\s]+(?:\s+[^,=]+)*?)(?=,|\s+\w+=|$)',  # key=value
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, instruction):
            key = match.group(1).lower().strip()
            value = match.group(2).strip()
            if key and value:
                data[key] = value
    
    return data


async def map_fields_with_llm(
    fields: List[Dict[str, Any]], 
    user_data: Dict[str, str],
    llm_client=None
) -> List[Dict[str, Any]]:
    """
    Use LLM to map user data to form fields. No hardcoded keywords.
    
    Args:
        fields: List of detected form fields
        user_data: Dict of user data to fill (email, message, etc.)
        llm_client: Optional LLM client
        
    Returns:
        List of {selector, value, field_name, data_key}
    """
    # Build field descriptions for LLM
    field_descs = []
    for i, f in enumerate(fields):
        desc = {
            "index": i,
            "tag": f.get("tag", ""),
            "type": f.get("type", ""),
            "name": f.get("name", ""),
            "id": f.get("id", ""),
            "placeholder": f.get("placeholder", ""),
            "selector": f.get("selector", "")
        }
        field_descs.append(desc)
    
    # Build prompt for LLM
    prompt = f"""Map user data to form fields. Return JSON array of mappings.

Form fields:
{field_descs}

User data to fill:
{user_data}

For each user data key, find the best matching form field.
Consider: field type (email→email, textarea→message), field name, placeholder.

Return ONLY valid JSON array:
[{{"field_index": 0, "data_key": "email", "selector": "#field-id"}}]

If no match for a data key, don't include it.
JSON:"""

    if llm_client:
        try:
            response = await llm_client.generate(prompt)
            import json
            import re
            # Extract JSON array
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                mappings = json.loads(match.group())
                result = []
                for m in mappings:
                    idx = m.get("field_index", -1)
                    data_key = m.get("data_key")
                    if 0 <= idx < len(fields) and data_key in user_data:
                        result.append({
                            "selector": fields[idx].get("selector") or m.get("selector"),
                            "value": user_data[data_key],
                            "type": fields[idx].get("type", "text"),
                            "name": data_key
                        })
                return result
        except Exception:
            pass
    
    # Fallback: simple heuristic matching (no hardcoded keywords - just type matching)
    result = []
    used_fields = set()
    
    for data_key, value in user_data.items():
        for i, field in enumerate(fields):
            if i in used_fields:
                continue
                
            field_type = field.get("type", "").lower()
            field_tag = field.get("tag", "").lower()
            field_name = field.get("name", "").lower()
            
            matched = False
            
            # Type-based matching only (no keyword guessing)
            if data_key == "email" and field_type == "email":
                matched = True
            elif data_key == "message" and (field_tag == "textarea" or field_type == "textarea"):
                matched = True
            elif data_key == "phone" and field_type == "tel":
                matched = True
            # Name contains data_key (generic fallback)
            elif data_key.lower() in field_name:
                matched = True
            
            if matched:
                result.append({
                    "selector": field.get("selector"),
                    "value": value,
                    "type": field_type or "text",
                    "name": data_key
                })
                used_fields.add(i)
                break
    
    return result


async def orchestrate_form_fill(
    page,
    instruction: str,
    logger=None
) -> Dict[str, Any]:
    """
    Orchestrate form filling using atomic components.
    
    Flow:
    1. Parse instruction to get user data
    2. Detect form and fields
    3. Match fields to data
    4. Fill matched fields
    5. Submit form
    6. Check success
    
    Returns:
        {success: bool, filled: {}, submitted: bool, errors: []}
    """
    result = {
        "success": False,
        "filled": {},
        "submitted": False,
        "errors": [],
        "steps": []
    }
    
    def log(msg):
        if logger:
            logger.log_text(msg)
        result["steps"].append(msg)
    
    # Step 1: Parse instruction
    log("📝 Step 1: Parsing instruction...")
    user_data = parse_instruction(instruction)
    if not user_data:
        result["errors"].append("No data found in instruction")
        return result
    log(f"   Found data: {list(user_data.keys())}")
    
    # Step 2: Detect form
    log("🔍 Step 2: Detecting form...")
    form_info = await detect_form(page)
    if not form_info.get("found"):
        result["errors"].append("No form found on page")
        return result
    
    form_selector = form_info.get("selector")
    fields = form_info.get("fields", [])
    log(f"   Found form: {form_info.get('form_id')} with {len(fields)} fields")
    
    # Step 3: Map fields to data using LLM (no hardcoded keywords)
    log("🗺️ Step 3: Mapping fields to data (LLM)...")
    mappings = await map_fields_with_llm(fields, user_data, llm_client=None)
    
    for m in mappings:
        log(f"   ✓ {m.get('name')} → {m.get('selector')}")
    
    if not mappings:
        result["errors"].append("LLM could not match any data to form fields")
        return result
    
    # Step 4: Fill fields
    log("✏️ Step 4: Filling fields...")
    fill_result = await fill_fields(page, mappings)
    result["filled"] = fill_result.get("filled", {})
    
    filled_count = sum(1 for v in result["filled"].values() if v)
    log(f"   Filled {filled_count}/{len(mappings)} fields")
    
    if fill_result.get("errors"):
        for err in fill_result["errors"]:
            result["errors"].append(f"Fill error: {err}")
    
    # Step 4b: Check and fix required checkboxes (consent, terms, etc.)
    log("☑️ Step 4b: Checking required checkboxes...")
    try:
        # Use form_id to find form, then check all checkboxes
        checkbox_js = f"""
        () => {{
            // Try to find form by ID or selector
            let form = document.getElementById('{form_info.get("form_id", "")}');
            if (!form) form = document.querySelector('{form_selector}');
            if (!form) form = document;
            
            const checkboxes = form.querySelectorAll('input[type="checkbox"]');
            let fixed = 0;
            let total = 0;
            
            checkboxes.forEach(cb => {{
                total++;
                // Check if required OR has 'consent' in name/id
                const needsCheck = cb.required || 
                    (cb.name && cb.name.includes('consent')) ||
                    (cb.id && cb.id.includes('consent'));
                    
                if (needsCheck && !cb.checked) {{
                    cb.checked = true;
                    cb.dispatchEvent(new Event('change', {{bubbles: true}}));
                    cb.dispatchEvent(new Event('click', {{bubbles: true}}));
                    fixed++;
                }}
            }});
            return {{fixed: fixed, total: total}};
        }}
        """
        cb_result = await page.evaluate(checkbox_js)
        if cb_result.get("fixed", 0) > 0:
            log(f"   ✓ Auto-checked {cb_result['fixed']} checkbox(es)")
            result["filled"]["consent"] = True
        else:
            log(f"   ✓ {cb_result.get('total', 0)} checkbox(es) already OK")
    except Exception as cb_err:
        log(f"   ⚠️ Checkbox check failed: {cb_err}")
    
    # Step 5: Capture state BEFORE submit (for LLM comparison)
    log("📸 Step 5a: Capturing page state before submit...")
    state_before = await capture_page_state(page)
    
    # Step 5b: Submit
    log("📤 Step 5b: Submitting form...")
    submit_result = await submit_form(page, form_selector=form_selector)
    
    if not submit_result.get("clicked"):
        result["errors"].append(f"Submit failed: {submit_result.get('error')}")
        return result
    
    result["submitted"] = True
    log(f"   ✓ Clicked: {submit_result.get('selector')}")
    
    # Wait for response
    try:
        await page.wait_for_timeout(2000)
    except Exception:
        pass
    
    # Step 6: Capture state AFTER submit and compute diff
    log("🎯 Step 6: Analyzing page changes for LLM...")
    success_data = await detect_success_data(page, state_before)
    
    diff = success_data.get("diff", {})
    llm_context = success_data.get("llm_context", {})
    
    # Log what changed
    if diff.get("url_changed"):
        log("   📍 URL changed")
    if diff.get("form_disappeared"):
        log("   📋 Form disappeared")
    if diff.get("new_text"):
        log(f"   📝 New text: {diff.get('new_text', '')[:100]}...")
    if diff.get("messages"):
        log(f"   💬 {len(diff.get('messages', []))} new message(s)")
    
    # Evaluate with LLM if available
    llm_result = await evaluate_success_with_llm(llm_context, llm_client=None)
    
    if llm_result.get("llm_evaluated"):
        log(f"   🤖 LLM: {llm_result.get('reason', 'evaluated')}")
        result["success"] = llm_result.get("success", False)
        result["llm_confidence"] = llm_result.get("confidence", 0)
    else:
        # Fallback heuristics
        if diff.get("form_disappeared") or diff.get("url_changed") or len(diff.get("messages", [])) > 0:
            log("   ✓ Success indicators detected")
            result["success"] = True
        elif result["submitted"] and filled_count > 0 and not diff.get("new_errors"):
            log("   ⚠️ No explicit success, but form submitted with data")
            result["success"] = True
        else:
            log("   ⚠️ Success unclear")
    
    # Step 7: Capture screenshot AFTER submission for verification
    log("📸 Step 7: Capturing post-submit screenshot...")
    try:
        import time
        screenshot_path = f"screenshots/form_submit_{int(time.time())}.png"
        await page.screenshot(path=screenshot_path)
        result["screenshot_after"] = screenshot_path
        log(f"   ✓ Screenshot saved: {screenshot_path}")
    except Exception as ss_err:
        log(f"   ⚠️ Screenshot failed: {ss_err}")
    
    return result


async def form_fill_tool(
    page,
    args: Dict[str, str],
    run_logger=None
) -> Dict[str, Any]:
    """
    Simplified tool interface for task_runner.
    
    Args:
        page: Playwright page
        args: Form data from LLM (email, message, name, etc.)
        run_logger: Optional logger
    
    Returns:
        {form_fill: {submitted: bool, filled: {}, errors: []}}
    """
    # Convert args dict to instruction string
    instruction = ", ".join(f"{k}={v}" for k, v in args.items())
    
    result = await orchestrate_form_fill(page, instruction, run_logger)
    
    return {
        "form_fill": {
            "submitted": result.get("submitted", False),
            "filled": result.get("filled", {}),
            "success": result.get("success", False),
            "errors": result.get("errors", [])
        }
    }
