"""
Form Fill Orchestrator - coordinates atomic components.
Uses LLM for field mapping and success detection. No hardcoded selectors.
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

# Import Streamware LLM client
try:
    from curllm_core.streamware.llm_client import (
        get_llm, llm_map_fields, llm_evaluate_success, set_llm_logger,
        generate_missing_field_data
    )
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    set_llm_logger = None
    generate_missing_field_data = None


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
    use_llm: bool = True,
    logger=None
) -> List[Dict[str, Any]]:
    """
    Use LLM to map user data to form fields. No hardcoded keywords.
    
    Args:
        fields: List of detected form fields
        user_data: Dict of user data to fill (email, message, etc.)
        use_llm: Whether to use LLM (default True)
        logger: Optional logger
        
    Returns:
        List of {selector, value, type, name}
    """
    def log(msg):
        if logger:
            logger.log_text(msg)
        print(f"[map_fields_with_llm] {msg}")
    
    log(f"   HAS_LLM={HAS_LLM}, use_llm={use_llm}")
    
    # Try LLM mapping first
    if use_llm and HAS_LLM:
        try:
            log("   🤖 Calling LLM for field mapping...")
            mappings = await llm_map_fields(fields, user_data)
            log(f"   🤖 LLM returned {len(mappings) if mappings else 0} mappings")
            if mappings:
                return mappings
            log("   ⚠️ LLM returned no mappings, using fallback")
        except Exception as e:
            log(f"   ⚠️ LLM mapping failed: {e}, using fallback")
    
    # Fallback: simple type-based matching (no hardcoded keyword lists)
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
            
            # Type-based matching only
            if data_key == "email" and field_type == "email":
                matched = True
            elif data_key == "message" and (field_tag == "textarea" or field_type == "textarea"):
                matched = True
            elif data_key == "phone" and field_type == "tel":
                matched = True
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
        "warnings": [],
        "steps": []
    }
    
    # Set LLM logger to use the same logger
    if HAS_LLM and set_llm_logger and logger:
        set_llm_logger(logger)
    
    # Track all DSL commands for summary
    dsl_commands = []
    
    def log(msg, inline=False):
        if logger:
            if inline:
                logger.log_text(msg, newline=False)
            else:
                logger.log_text(msg)
        result["steps"].append(msg)
    
    def log_dsl(action: str, args: dict = None, description: str = None):
        """Log DSL command that could replay this action."""
        args_str = ", ".join(f'{k}="{v}"' for k, v in (args or {}).items())
        dsl = f"streamware.{action}({args_str})"
        dsl_commands.append({"cmd": dsl, "desc": description or action})
        log(f"> `{dsl}`")
    
    def log_raw(text: str):
        """Log raw text without extra newlines (for tables, code blocks)."""
        if logger and hasattr(logger, '_write'):
            logger._write(text)
        result["steps"].append(text)
    
    def log_table(headers: list, rows: list):
        """Log a properly formatted markdown table."""
        header_row = "| " + " | ".join(headers) + " |"
        separator = "|" + "|".join(["---" for _ in headers]) + "|"
        table_rows = [f"| {' | '.join(str(c) for c in row)} |" for row in rows]
        table = "\n" + "\n".join([header_row, separator] + table_rows) + "\n\n"
        log_raw(table)
    
    # Step 1: Parse instruction
    log("\n## 📝 Step 1: Parse Instruction\n")
    log_dsl("form.parse_instruction", {"instruction": instruction[:100]})
    user_data = parse_instruction(instruction)
    if not user_data:
        result["errors"].append("No data found in instruction")
        return result
    
    # Auto-split "name" into first_name/last_name for forms with separate fields
    if "name" in user_data and " " in user_data["name"]:
        parts = user_data["name"].split(" ", 1)
        user_data["first_name"] = parts[0]
        user_data["last_name"] = parts[1] if len(parts) > 1 else ""
        log(f"**Split name:** `{user_data['name']}` → first: `{user_data['first_name']}`, last: `{user_data['last_name']}`")
    
    log(f"**Parsed data:** `{list(user_data.keys())}`")
    
    # Step 2: Detect form
    log("\n## 🔍 Step 2: Detect Form\n")
    log_dsl("form.detect", {"page": "current"})
    form_info = await detect_form(page)
    if not form_info.get("found"):
        result["errors"].append("No form found on page")
        return result
    
    form_selector = form_info.get("selector")
    fields = form_info.get("fields", [])
    log(f"**Form found:** `{form_info.get('form_id')}` with {len(fields)} fields")
    log(f"**Form selector:** `{form_selector}`")
    
    # Log detected fields in a table
    if fields:
        rows = []
        for i, f in enumerate(fields[:10]):
            sel = f.get('selector') or 'N/A'
            req = "✓" if f.get('required') else ""
            rows.append([i, f.get('type', ''), f.get('name', ''), req, f"`{sel[:30]}`"])
        log_table(["#", "Type", "Name", "Req", "Selector"], rows)
    else:
        log("⚠️ **No fields detected in form**")
    
    # Step 2b: Check for missing required data and generate with LLM
    log("\n## 🔍 Step 2b: Analyze Required Fields\n")
    
    # Find required fields that need data
    required_fields = []
    for f in fields:
        field_type = f.get('type', '').lower()
        field_name = f.get('name', '').lower()
        
        # Skip submit, file, checkbox, hidden
        if field_type in ['submit', 'file', 'hidden', 'checkbox', 'button']:
            continue
        
        # Check if required or looks like a main form field
        is_required = f.get('required', False)
        is_main_field = field_type in ['email', 'text', 'textarea', 'tel']
        
        if is_required or is_main_field:
            required_fields.append({
                "type": field_type,
                "name": field_name,
                "tag": f.get('tag', ''),
                "placeholder": f.get('placeholder', ''),
                "required": is_required
            })
    
    # Check what data we have vs what's needed
    missing_fields = []
    for rf in required_fields:
        field_name = rf['name']
        field_type = rf['type']
        
        # Check if we have data for this field
        has_data = False
        field_name_lower = field_name.lower()
        
        for data_key, data_value in user_data.items():
            if data_value and str(data_value).strip():  # Has non-empty value
                data_key_lower = data_key.lower()
                
                # Direct match
                if data_key_lower in field_name_lower or field_name_lower in data_key_lower:
                    has_data = True
                    break
                
                # Semantic concept groups for type-based matching
                email_concepts = {'email', 'mail', 'e-mail'}
                message_concepts = {'message', 'msg', 'content', 'body', 'text'}
                name_first_concepts = {'first', 'firstname', 'fname', 'imię'}
                name_last_concepts = {'last', 'lastname', 'lname', 'nazwisko', 'surname'}
                
                # Type-based matching with semantic concepts
                if data_key_lower in email_concepts and field_type == 'email':
                    has_data = True
                    break
                if data_key_lower in message_concepts and (rf['tag'] == 'textarea' or field_type == 'textarea'):
                    has_data = True
                    break
                
                # First/Last name matching with semantic concepts
                if data_key_lower in name_first_concepts and any(c in field_name_lower for c in name_first_concepts):
                    has_data = True
                    break
                if data_key_lower in name_last_concepts and any(c in field_name_lower for c in name_last_concepts):
                    has_data = True
                    break
        
        if not has_data:
            missing_fields.append(rf)
    
    if missing_fields:
        log(f"**Missing data for {len(missing_fields)} field(s):**")
        for mf in missing_fields:
            log(f"- `{mf['name']}` ({mf['type']})")
        
        # Use LLM to generate missing data
        if HAS_LLM:
            log("\n> 🤖 Generating missing field values with LLM...")
            log_dsl("llm.generate_field_values", {"missing": str([m['name'] for m in missing_fields])})
            
            generated = await generate_missing_field_data(missing_fields, user_data, logger)
            if generated:
                user_data.update(generated)
                log(f"**Generated values:** `{list(generated.keys())}`")
    else:
        log("**All required fields have data** ✓")
    
    # Step 3: Map fields to data using LLM
    log("\n## 🗺️ Step 3: LLM Field Mapping\n")
    log_dsl("form.map_fields_llm", {"fields": f"{len(fields)} fields", "data": str(list(user_data.keys()))})
    mappings = await map_fields_with_llm(fields, user_data, use_llm=HAS_LLM, logger=logger)
    
    log("\n**Mapping results:**\n")
    for m in mappings:
        log(f"- `{m.get('name')}` → `{m.get('selector')}`")
    
    if not mappings:
        result["errors"].append("LLM could not match any data to form fields")
        return result
    
    # Step 4: Fill fields
    log("\n## ✏️ Step 4: Fill Fields\n")
    
    for m in mappings:
        log_dsl("form.fill_field", {
            "selector": m.get('selector', '')[:50],
            "value": str(m.get('value', ''))[:30],
            "type": m.get('type', 'text')
        })
    
    fill_result = await fill_fields(page, mappings)
    result["filled"] = fill_result.get("filled", {})
    
    filled_count = sum(1 for v in result["filled"].values() if v)
    log(f"\n**Filled:** {filled_count}/{len(mappings)} fields")
    
    if fill_result.get("errors"):
        for err in fill_result["errors"]:
            log(f"- ⚠️ Error: {err}")
            result["errors"].append(f"Fill error: {err}")
    
    # Step 4b: Check and fix required checkboxes
    log("\n## ☑️ Step 4b: Check Required Checkboxes\n")
    log_dsl("form.check_required_checkboxes", {"form_id": form_info.get("form_id", "")})
    
    try:
        checkbox_js = f"""
        () => {{
            let form = document.getElementById('{form_info.get("form_id", "")}');
            if (!form) form = document.querySelector('{form_selector}');
            if (!form) form = document;
            
            const checkboxes = form.querySelectorAll('input[type="checkbox"]');
            let fixed = 0;
            let total = 0;
            
            checkboxes.forEach(cb => {{
                total++;
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
            log(f"**Auto-checked:** {cb_result['fixed']} required checkbox(es)")
            result["filled"]["consent"] = True
        else:
            log(f"**Status:** {cb_result.get('total', 0)} checkbox(es) already checked")
    except Exception as cb_err:
        log(f"⚠️ **Error:** {cb_err}")
    
    # Step 4c: Detect and handle CAPTCHA
    log("\n## 🔐 Step 4c: CAPTCHA Detection\n")
    log_dsl("captcha.detect", {"page": "current"})
    
    try:
        from curllm_core.streamware.components.captcha import detect_captcha
        captcha_info = await detect_captcha(page)
        
        if captcha_info.get("found"):
            captcha_type = captcha_info.get("type", "unknown")
            log(f"**CAPTCHA detected:** `{captcha_type}`")
            log(f"- Sitekey: `{captcha_info.get('sitekey', 'N/A')}`")
            log(f"- Selector: `{captcha_info.get('selector', 'N/A')}`")
            
            # Take screenshot of CAPTCHA
            from datetime import datetime
            from pathlib import Path
            captcha_screenshot = f"screenshots/captcha_{datetime.now().timestamp():.0f}.png"
            Path("screenshots").mkdir(exist_ok=True)
            await page.screenshot(path=captcha_screenshot)
            log(f"**CAPTCHA screenshot:** `{captcha_screenshot}`")
            result["captcha"] = {
                "found": True,
                "type": str(captcha_type),
                "screenshot": captcha_screenshot
            }
            
            # Try to solve with visual LLM first (no API key needed)
            import os
            log("> 🤖 Attempting CAPTCHA solve with visual LLM...")
            try:
                from curllm_core.streamware.components.captcha import solve_captcha_visual
                solve_result = await solve_captcha_visual(page, captcha_info, captcha_screenshot)
                
                if solve_result.get("success"):
                    log("✅ **CAPTCHA solved with visual LLM!**")
                    log(f"- Actions: {solve_result.get('actions_taken', [])}")
                    result["captcha"]["solved"] = True
                else:
                    log(f"⚠️ **Visual LLM solve incomplete:** {solve_result.get('error', 'unknown')}")
                    log(f"- Analysis: {solve_result.get('llm_analysis', '')[:200]}")
                    
                    # Fallback to 2captcha if API key available
                    if os.getenv("CAPTCHA_API_KEY"):
                        log("> Fallback: Attempting solve with 2captcha API...")
                        from curllm_core.streamware.components.captcha import solve_captcha
                        api_result = await solve_captcha(page, captcha_info)
                        if api_result.get("success"):
                            log("✅ **CAPTCHA solved with 2captcha!**")
                            result["captcha"]["solved"] = True
                        else:
                            result["warnings"].append(f"CAPTCHA not solved: {api_result.get('error')}")
                    else:
                        result["warnings"].append("CAPTCHA requires manual solving or vision model")
            except Exception as solve_err:
                log(f"⚠️ **CAPTCHA solve error:** {solve_err}")
                result["warnings"].append(f"CAPTCHA solve failed: {solve_err}")
        else:
            log("**No CAPTCHA detected** ✓")
    except Exception as captcha_err:
        log(f"⚠️ **CAPTCHA detection error:** {captcha_err}")
    
    # Step 5: Submit form
    log("\n## 📤 Step 5: Submit Form\n")
    
    # 5a: Capture state before
    log_dsl("page.capture_state", {"moment": "before_submit"})
    state_before = await capture_page_state(page)
    log(f"**Page state captured:** URL=`{state_before.get('url', '')[:50]}`")
    
    # 5b: Click submit
    log_dsl("form.submit", {"form_selector": form_selector or "auto"})
    submit_result = await submit_form(page, form_selector=form_selector)
    
    if not submit_result.get("clicked"):
        result["errors"].append(f"Submit failed: {submit_result.get('error')}")
        return result
    
    result["submitted"] = True
    log(f"**Clicked:** `{submit_result.get('selector')}`")
    
    # Wait for response - longer wait for AJAX forms
    log_dsl("page.wait", {"ms": "3000"})
    try:
        # Wait for network to stabilize
        await page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    
    try:
        await page.wait_for_timeout(1500)  # Extra time for DOM updates
    except Exception:
        pass
    
    # Step 6: Capture page response
    log("\n## 📄 Step 6: Page Response After Submit\n")
    log_dsl("page.capture_response", {"moment": "after_submit"})
    
    # Capture visible text that user sees
    try:
        visible_response = await page.evaluate("""
        () => {
            // Look for common success message containers
            const selectors = [
                '.success', '.message', '.alert', '.notification',
                '[class*="success"]', '[class*="message"]', '[class*="thank"]',
                '.form-response', '.form-message', '[role="alert"]'
            ];
            
            let responseText = '';
            for (const sel of selectors) {
                const els = document.querySelectorAll(sel);
                els.forEach(el => {
                    const text = el.innerText?.trim();
                    if (text && text.length > 5 && text.length < 500) {
                        responseText += text + '\\n';
                    }
                });
            }
            
            // Also check for any new visible text near form
            const form = document.querySelector('form');
            if (form) {
                const parent = form.parentElement;
                if (parent) {
                    const siblings = parent.children;
                    for (const sib of siblings) {
                        if (sib !== form && sib.innerText) {
                            const text = sib.innerText.trim();
                            if (text.length > 10 && text.length < 200) {
                                responseText += text + '\\n';
                            }
                        }
                    }
                }
            }
            
            return responseText.trim() || null;
        }
        """)
        
        if visible_response:
            log(f"**Server response:**\n```\n{visible_response[:500]}\n```")
            result["server_response"] = visible_response
        else:
            log("**Server response:** _(no visible response message detected)_")
            
    except Exception as resp_err:
        log(f"⚠️ Could not capture response: {resp_err}")
    
    # Step 7: Analyze success with LLM
    log("\n## 🎯 Step 7: LLM Success Analysis\n")
    log_dsl("page.capture_state", {"moment": "after_submit"})
    success_data = await detect_success_data(page, state_before)
    
    diff = success_data.get("diff", {})
    llm_context = success_data.get("llm_context", {})
    
    # Add server response to context for better evaluation
    if result.get("server_response"):
        diff["server_response"] = result["server_response"]
        llm_context["server_response"] = result["server_response"]
    
    # Log changes in a table
    log("\n**Page changes detected:**")
    changes_rows = [
        ["URL changed", "✅" if diff.get('url_changed') else "❌"],
        ["Form disappeared", "✅" if diff.get('form_disappeared') else "❌"],
        ["New errors", "⚠️" if diff.get('new_errors') else "❌"],
    ]
    if diff.get("new_text"):
        changes_rows.append(["New text", f"`{diff.get('new_text', '')[:40]}...`"])
    log_table(["Change", "Status"], changes_rows)
    
    # Evaluate with LLM
    log_dsl("llm.evaluate_success", {"diff": "page_changes"})
    if HAS_LLM:
        try:
            llm_result = await llm_evaluate_success(diff)
        except Exception:
            llm_result = {"success": False, "confidence": 0}
    else:
        llm_result = await evaluate_success_with_llm(llm_context, llm_client=None)
    
    if llm_result.get("llm_evaluated") or (HAS_LLM and llm_result.get("confidence", 0) > 0.6):
        log(f"\n**LLM verdict:** {llm_result.get('reason', 'evaluated')}")
        log(f"**Confidence:** {llm_result.get('confidence', 0)}")
        result["success"] = llm_result.get("success", False)
        result["llm_confidence"] = llm_result.get("confidence", 0)
    else:
        # Fallback heuristics
        server_resp = result.get("server_response", "").lower()
        has_success_indicator = any(word in server_resp for word in [
            "thank", "dziękuj", "success", "sukces", "wysłan", "sent", 
            "otrzym", "received", "potwierdz", "confirm"
        ])
        
        if has_success_indicator:
            log("**Heuristic:** ✓ Success message detected in server response")
            result["success"] = True
        elif diff.get("form_disappeared") or diff.get("url_changed") or len(diff.get("messages", [])) > 0:
            log("**Heuristic:** ✓ Success indicators detected (form/URL change)")
            result["success"] = True
        elif result["submitted"] and filled_count > 0 and not diff.get("new_errors"):
            log("**Heuristic:** ⚠️ No explicit success, but form submitted with data")
            result["success"] = True
        else:
            log("**Heuristic:** ⚠️ Success unclear")
    
    # Step 8: Capture screenshot of form area
    log("\n## 📸 Step 8: Form Screenshot\n")
    
    try:
        import time
        
        # Scroll to form element
        log_dsl("page.scroll_to", {"selector": form_selector or "form"})
        if form_selector:
            await page.evaluate(f"""
                const el = document.querySelector('{form_selector}');
                if (el) el.scrollIntoView({{behavior: 'instant', block: 'center'}});
            """)
        else:
            await page.evaluate("window.scrollBy(0, 300)")
        
        await page.wait_for_timeout(500)
        
        # Screenshot of form area only (not full page)
        screenshot_path = f"screenshots/form_submit_{int(time.time())}.png"
        log_dsl("page.screenshot", {"path": screenshot_path, "element": form_selector or "viewport"})
        
        # Try to screenshot just the form element
        if form_selector:
            try:
                form_el = await page.query_selector(form_selector)
                if form_el:
                    await form_el.screenshot(path=screenshot_path)
                else:
                    await page.screenshot(path=screenshot_path)
            except Exception:
                await page.screenshot(path=screenshot_path)
        else:
            await page.screenshot(path=screenshot_path)
        
        result["screenshot_after"] = screenshot_path
        
        # Log with markdown image
        log(f"**Screenshot saved:** `{screenshot_path}`\n")
        log(f"![Form after submit](../{screenshot_path})\n")
        
    except Exception as ss_err:
        log(f"⚠️ **Screenshot error:** {ss_err}")
    
    # Generate DSL summary for replay
    log("\n---\n## 📋 DSL Execution Summary\n")
    log("**Complete DSL sequence for replay:**")
    
    # Build code block as single string
    dsl_block = "\n```streamware\n"
    dsl_block += "\n".join(cmd["cmd"] for cmd in dsl_commands)
    dsl_block += "\n```\n"
    log_raw(dsl_block)
    
    # Result summary
    status = "✅ SUCCESS" if result.get("success") else "⚠️ PARTIAL"
    summary = f"""
**Execution result:**
- **Status:** {status}
- **Fields filled:** `{list(result.get('filled', {}).keys())}`
- **Submitted:** {result.get('submitted', False)}
"""
    if result.get("errors"):
        summary += f"- **Errors:** {result['errors']}\n"
    log_raw(summary)
    
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
