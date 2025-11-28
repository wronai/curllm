"""
Form Field Filling - fills fields using selectors provided by LLM.
No hardcoded selectors - LLM decides what to fill based on detect results.
"""
from typing import Dict, Any, Optional


async def fill_field(
    page,
    selector: str,
    value: str,
    field_type: str = "text"
) -> Dict[str, Any]:
    """
    Fill a single form field.
    
    Args:
        page: Playwright page
        selector: CSS selector (from LLM based on detect results)
        value: Value to fill
        field_type: Type of field (text, email, textarea, checkbox, etc.)
    
    Returns:
        {success: bool, selector: str, value: str, error: str|None}
    """
    result = {"success": False, "selector": selector, "value": value, "error": None}
    
    if not selector or not value:
        result["error"] = "Missing selector or value"
        return result
    
    try:
        # Handle different field types
        if field_type == "checkbox":
            el = page.locator(selector)
            is_checked = await el.is_checked()
            if value.lower() in ["true", "1", "checked", "yes"] and not is_checked:
                await el.check()
            elif value.lower() in ["false", "0", "unchecked", "no"] and is_checked:
                await el.uncheck()
            result["success"] = True
            
        elif field_type == "select":
            await page.select_option(selector, value)
            result["success"] = True
            
        else:
            # Standard text input / textarea
            await page.fill(selector, value)
            result["success"] = True
            
    except Exception as e:
        result["error"] = str(e)
        # Try JS fallback
        try:
            await page.evaluate(f"""
                (sel, val) => {{
                    const el = document.querySelector(sel);
                    if (el) {{
                        el.value = val;
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                        el.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                }}
            """, selector, value)
            result["success"] = True
            result["error"] = None
            result["fallback"] = True
        except Exception as e2:
            result["error"] = f"Fill failed: {e}, fallback failed: {e2}"
    
    return result


async def fill_fields(
    page,
    field_mappings: list
) -> Dict[str, Any]:
    """
    Fill multiple fields.
    
    Args:
        page: Playwright page
        field_mappings: List of {selector, value, type?}
    
    Returns:
        {filled: {field: bool}, errors: []}
    """
    results = {"filled": {}, "errors": []}
    
    for mapping in field_mappings:
        selector = mapping.get("selector")
        value = mapping.get("value")
        field_type = mapping.get("type", "text")
        
        if not selector:
            continue
            
        res = await fill_field(page, selector, value, field_type)
        
        # Use name or selector as key
        key = mapping.get("name") or selector
        results["filled"][key] = res["success"]
        
        if res.get("error"):
            results["errors"].append({"field": key, "error": res["error"]})
    
    return results
