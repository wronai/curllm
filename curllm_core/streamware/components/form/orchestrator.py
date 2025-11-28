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
        get_llm, llm_map_fields, llm_evaluate_success, set_llm_logger
    )
    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    set_llm_logger = None


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
        "steps": []
    }
    
    # Set LLM logger to use the same logger
    if HAS_LLM and set_llm_logger and logger:
        set_llm_logger(logger)
    
    def log(msg):
        if logger:
            logger.log_text(msg)
        result["steps"].append(msg)
    
    def log_dsl(action: str, args: dict = None):
        """Log DSL command that could replay this action."""
        args_str = ", ".join(f'{k}="{v}"' for k, v in (args or {}).items())
        dsl = f"streamware.{action}({args_str})"
        log(f"```dsl\n{dsl}\n```")
    
    # Step 1: Parse instruction
    log("\n## 📝 Step 1: Parse Instruction\n")
    log_dsl("form.parse_instruction", {"instruction": instruction[:100]})
    user_data = parse_instruction(instruction)
    if not user_data:
        result["errors"].append("No data found in instruction")
        return result
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
    log("\n| # | Type | Name | Selector |")
    log("|---|------|------|----------|")
    for i, f in enumerate(fields[:10]):  # Max 10 fields
        log(f"| {i} | {f.get('type', '')} | {f.get('name', '')} | `{f.get('selector', '')[:40]}` |")
    
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
    
    # Wait for response
    log_dsl("page.wait", {"ms": "2000"})
    try:
        await page.wait_for_timeout(2000)
    except Exception:
        pass
    
    # Step 6: Analyze success with LLM
    log("\n## 🎯 Step 6: LLM Success Analysis\n")
    log_dsl("page.capture_state", {"moment": "after_submit"})
    success_data = await detect_success_data(page, state_before)
    
    diff = success_data.get("diff", {})
    llm_context = success_data.get("llm_context", {})
    
    # Log changes in a table
    log("\n**Page changes detected:**\n")
    log("| Change | Value |")
    log("|--------|-------|")
    log(f"| URL changed | {diff.get('url_changed', False)} |")
    log(f"| Form disappeared | {diff.get('form_disappeared', False)} |")
    log(f"| New errors | {diff.get('new_errors', False)} |")
    if diff.get("new_text"):
        log(f"| New text | `{diff.get('new_text', '')[:50]}...` |")
    
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
        if diff.get("form_disappeared") or diff.get("url_changed") or len(diff.get("messages", [])) > 0:
            log("**Heuristic:** ✓ Success indicators detected")
            result["success"] = True
        elif result["submitted"] and filled_count > 0 and not diff.get("new_errors"):
            log("**Heuristic:** ⚠️ No explicit success, but form submitted with data")
            result["success"] = True
        else:
            log("**Heuristic:** ⚠️ Success unclear")
    
    # Step 7: Capture screenshot of form area
    log("\n## 📸 Step 7: Form Screenshot\n")
    
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
