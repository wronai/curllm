"""
Form Submit - submits form and detects success via LLM.
No hardcoded selectors or keywords - LLM evaluates page changes.
"""
from typing import Dict, Any, Optional, List


async def get_clickable_buttons(page, form_selector: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all clickable buttons in form/page for LLM to choose from.
    Prioritizes submit buttons, filters out upload/delete buttons.
    
    Returns:
        List of {selector, text, type, classes, is_submit} for LLM to evaluate
    """
    js = f"""
    () => {{
        const container = {f'document.querySelector("{form_selector}")' if form_selector else 'document'};
        if (!container) return [];
        
        const buttons = [];
        container.querySelectorAll('button, input[type="submit"], input[type="button"], [role="button"]').forEach((el, idx) => {{
            const rect = el.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) return;
            
            const text = (el.innerText || el.value || '').trim().toLowerCase();
            const classes = (el.className || '').toLowerCase();
            const elType = (el.type || '').toLowerCase();
            
            // Skip upload/delete/file buttons
            if (classes.includes('upload') || classes.includes('delete') || 
                classes.includes('file') || text.includes('plik') ||
                text.includes('usuń') || text.includes('wybierz plik')) {{
                return;
            }}
            
            // Detect if this is a submit button
            const isSubmit = elType === 'submit' || 
                           classes.includes('submit') || 
                           text.includes('wyślij') || 
                           text.includes('send') ||
                           text.includes('submit') ||
                           text.includes('zapisz');
            
            buttons.push({{
                selector: el.id ? '#' + el.id : (el.name ? '[name="' + el.name + '"]' : `button:nth-of-type(${{idx + 1}})`),
                text: (el.innerText || el.value || '').trim().substring(0, 50),
                type: elType || el.tagName.toLowerCase(),
                classes: el.className || '',
                is_submit: isSubmit
            }});
        }});
        
        // Sort: submit buttons first
        return buttons.sort((a, b) => (b.is_submit ? 1 : 0) - (a.is_submit ? 1 : 0));
    }}
    """
    try:
        return await page.evaluate(js) or []
    except Exception:
        return []


async def capture_page_state(page) -> Dict[str, Any]:
    """
    Capture current page state for comparison.
    
    Returns:
        {url, title, visible_text_preview, form_count, has_errors, new_elements}
    """
    js = """
    () => {
        const forms = document.querySelectorAll('form');
        const visibleForms = Array.from(forms).filter(f => {
            const rect = f.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        });
        
        // Get visible text (first 2000 chars)
        const text = document.body.innerText.substring(0, 2000);
        
        // Check for error elements
        const errorEls = document.querySelectorAll('[class*="error"], [class*="invalid"], .alert-danger');
        
        // Check for new/changed elements (messages, alerts, etc.)
        const messages = [];
        document.querySelectorAll('[class*="message"], [class*="alert"], [class*="notification"], [class*="response"]').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                messages.push({
                    tag: el.tagName.toLowerCase(),
                    classes: el.className,
                    text: el.innerText.substring(0, 200)
                });
            }
        });
        
        return {
            url: window.location.href,
            title: document.title,
            visible_text_preview: text,
            form_count: visibleForms.length,
            total_forms: forms.length,
            has_error_elements: errorEls.length > 0,
            error_count: errorEls.length,
            messages: messages
        };
    }
    """
    try:
        return await page.evaluate(js)
    except Exception as e:
        return {"error": str(e)}


async def compute_page_diff(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute differences between page states.
    
    Returns:
        {url_changed, form_disappeared, new_messages, text_changes}
    """
    diff = {
        "url_changed": before.get("url") != after.get("url"),
        "title_changed": before.get("title") != after.get("title"),
        "form_disappeared": before.get("form_count", 0) > after.get("form_count", 0),
        "form_hidden": before.get("total_forms", 0) == after.get("total_forms", 0) and before.get("form_count", 0) > after.get("form_count", 0),
        "new_errors": after.get("error_count", 0) > before.get("error_count", 0),
        "messages": after.get("messages", []),
        "new_text": ""
    }
    
    # Find new text that appeared
    before_text = before.get("visible_text_preview", "")
    after_text = after.get("visible_text_preview", "")
    
    if after_text != before_text:
        # Simple diff - find text that's new
        new_parts = []
        for line in after_text.split('\n'):
            if line.strip() and line not in before_text:
                new_parts.append(line.strip())
        diff["new_text"] = '\n'.join(new_parts[:10])  # First 10 new lines
    
    return diff


async def submit_form(
    page,
    submit_selector: Optional[str] = None,
    form_selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submit form by clicking submit button.
    
    Args:
        page: Playwright page
        submit_selector: CSS selector for submit button (from LLM detection)
        form_selector: Form selector to find buttons in
    
    Returns:
        {clicked: bool, selector: str, buttons: [], error: str|None}
    """
    result = {"clicked": False, "selector": None, "buttons": [], "error": None}
    
    # Get available buttons for LLM if no selector provided
    if not submit_selector:
        buttons = await get_clickable_buttons(page, form_selector)
        result["buttons"] = buttons
        
        if not buttons:
            result["error"] = "No buttons found - LLM should analyze page"
            return result
        
        # Use first button as fallback (LLM should provide better choice)
        submit_selector = buttons[0].get("selector")
    
    result["selector"] = submit_selector
    
    try:
        await page.click(submit_selector)
        result["clicked"] = True
    except Exception as e:
        result["error"] = str(e)
        
        # Try JS click
        try:
            await page.evaluate(f"""
                () => {{
                    const el = document.querySelector("{submit_selector}");
                    if (el) {{ el.click(); return true; }}
                    return false;
                }}
            """)
            result["clicked"] = True
            result["error"] = None
        except Exception:
            pass
    
    return result


async def detect_success_data(page, state_before: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Collect data for LLM to evaluate success. No hardcoded keywords.
    
    Args:
        page: Playwright page
        state_before: Page state captured before submission
    
    Returns:
        {state_after, diff, llm_prompt} - data for LLM evaluation
    """
    state_after = await capture_page_state(page)
    
    if state_before:
        diff = await compute_page_diff(state_before, state_after)
    else:
        diff = {"no_before_state": True}
    
    # Build prompt for LLM to evaluate
    llm_context = {
        "url_changed": diff.get("url_changed", False),
        "form_disappeared": diff.get("form_disappeared", False),
        "new_errors": diff.get("new_errors", False),
        "new_text": diff.get("new_text", ""),
        "messages": diff.get("messages", []),
        "current_url": state_after.get("url", "")
    }
    
    return {
        "state_after": state_after,
        "diff": diff,
        "llm_context": llm_context,
        "needs_llm_evaluation": True
    }


async def evaluate_success_with_llm(
    llm_context: Dict[str, Any],
    llm_client=None
) -> Dict[str, Any]:
    """
    Use LLM to evaluate if form submission was successful.
    
    Args:
        llm_context: Context from detect_success_data
        llm_client: LLM client for evaluation
    
    Returns:
        {success: bool, confidence: float, reason: str}
    """
    if not llm_client:
        # Fallback: simple heuristics if no LLM available
        success = (
            llm_context.get("form_disappeared", False) or
            llm_context.get("url_changed", False)
        ) and not llm_context.get("new_errors", False)
        
        return {
            "success": success,
            "confidence": 0.5,
            "reason": "No LLM available, using heuristics",
            "fallback": True
        }
    
    # Build prompt for LLM
    prompt = f"""Evaluate if a form submission was successful based on page changes:

URL changed: {llm_context.get('url_changed', False)}
Form disappeared: {llm_context.get('form_disappeared', False)}
New error elements: {llm_context.get('new_errors', False)}
Current URL: {llm_context.get('current_url', '')}

New text on page:
{llm_context.get('new_text', 'No new text')}

New messages/alerts:
{llm_context.get('messages', [])}

Was the form submission successful? Respond with JSON:
{{"success": true/false, "confidence": 0.0-1.0, "reason": "explanation"}}
"""
    
    try:
        response = await llm_client.generate(prompt)
        # Parse LLM response
        import json
        import re
        
        # Extract JSON from response
        json_match = re.search(r'\{[^}]+\}', response)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "success": result.get("success", False),
                "confidence": result.get("confidence", 0.7),
                "reason": result.get("reason", "LLM evaluation"),
                "llm_evaluated": True
            }
    except Exception as e:
        pass
    
    # Fallback if LLM fails
    return {
        "success": llm_context.get("form_disappeared", False),
        "confidence": 0.5,
        "reason": "LLM evaluation failed, using heuristics",
        "fallback": True
    }


# Legacy function for backward compatibility
async def detect_success(page, state_before: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Detect success - returns data for LLM evaluation.
    For backward compatibility, also returns simple heuristic result.
    """
    data = await detect_success_data(page, state_before)
    
    # Simple heuristics as fallback
    diff = data.get("diff", {})
    success = (
        diff.get("form_disappeared", False) or
        diff.get("url_changed", False) or
        len(diff.get("messages", [])) > 0
    ) and not diff.get("new_errors", False)
    
    return {
        "success": success,
        "diff": diff,
        "llm_context": data.get("llm_context"),
        "needs_llm_evaluation": True
    }
