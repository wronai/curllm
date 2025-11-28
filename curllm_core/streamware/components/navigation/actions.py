"""
Navigation Actions - Atomic browser interaction operations

Each function is a single atomic action that can be composed.
No hardcoded selectors - all selectors come from LLM or caller.
"""

import random
from typing import Any, Dict, Optional


async def click(
    page,
    selector: str,
    timeout_ms: int = 8000,
    smart_scroll: bool = True
) -> Dict[str, Any]:
    """
    Click on element by selector.
    
    Args:
        page: Playwright page
        selector: CSS selector (from LLM detection)
        timeout_ms: Click timeout
        smart_scroll: Auto-scroll to reveal element
        
    Returns:
        {success: bool, selector: str, error: str|None}
    """
    result = {"success": False, "selector": selector, "error": None}
    
    if not selector:
        result["error"] = "No selector provided"
        return result
    
    try:
        # Optional pre-scroll to reveal element
        if smart_scroll:
            await auto_scroll(page, steps=2, delay_ms=300)
        
        loc = page.locator(str(selector))
        
        # Check if element exists
        if await loc.count() == 0:
            if smart_scroll:
                # Try deeper scroll for lazy-loaded elements
                await auto_scroll(page, steps=4, delay_ms=500)
        
        # Wait for visibility and click
        await loc.first.wait_for(state="visible", timeout=timeout_ms)
        await loc.first.click(timeout=timeout_ms)
        result["success"] = True
        
    except Exception as e:
        # Fallback: direct DOM click
        try:
            await page.evaluate(
                "(s) => { const el=document.querySelector(s); if(el) el.click(); }",
                selector,
            )
            result["success"] = True
        except Exception as e2:
            result["error"] = f"Click failed: {e}, fallback: {e2}"
    
    return result


async def fill_field(
    page,
    selector: str,
    value: str,
    timeout_ms: int = 8000,
    trigger_events: bool = True
) -> Dict[str, Any]:
    """
    Fill input field with value.
    
    Args:
        page: Playwright page
        selector: CSS selector (from LLM detection)
        value: Value to fill
        timeout_ms: Wait timeout
        trigger_events: Dispatch input/blur events
        
    Returns:
        {success: bool, selector: str, value: str, error: str|None}
    """
    result = {"success": False, "selector": selector, "value": value, "error": None}
    
    if not selector:
        result["error"] = "No selector provided"
        return result
    
    try:
        # Wait for element
        await page.locator(str(selector)).first.wait_for(state="visible", timeout=timeout_ms)
        
        # Fill value
        await page.fill(str(selector), str(value))
        
        # Trigger validation events
        if trigger_events:
            await page.evaluate(
                """(s) => { 
                    const el = document.querySelector(s); 
                    if (!el) return;
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                    el.blur();
                }""",
                selector,
            )
        
        # Human-like delay
        await page.wait_for_timeout(150 + int(random.random() * 350))
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def scroll_page(
    page,
    direction: str = "down",
    amount: Optional[int] = None
) -> Dict[str, Any]:
    """
    Scroll page in direction.
    
    Args:
        page: Playwright page
        direction: "up" or "down"
        amount: Pixels to scroll (random if None)
        
    Returns:
        {success: bool, scrolled: int}
    """
    result = {"success": False, "scrolled": 0}
    
    try:
        dy = amount if amount else (300 + int(random.random() * 700))
        if direction == "up":
            dy = -dy
        
        try:
            await page.mouse.wheel(0, dy)
        except Exception:
            await page.evaluate(f"window.scrollBy(0, {dy})")
        
        await page.wait_for_timeout(500 + int(random.random() * 800))
        result["success"] = True
        result["scrolled"] = dy
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def wait(page, ms: int = 1000) -> Dict[str, Any]:
    """
    Wait for specified time.
    
    Args:
        page: Playwright page
        ms: Milliseconds to wait
        
    Returns:
        {success: bool, waited: int}
    """
    result = {"success": False, "waited": ms}
    
    try:
        # Add some randomness for human-like behavior
        actual_wait = ms + int(random.random() * (ms * 0.3))
        await page.wait_for_timeout(actual_wait)
        result["success"] = True
        result["waited"] = actual_wait
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def auto_scroll(
    page,
    steps: int = 3,
    delay_ms: int = 500
) -> Dict[str, Any]:
    """
    Auto-scroll page to load lazy content.
    
    Args:
        page: Playwright page
        steps: Number of scroll steps
        delay_ms: Delay between steps
        
    Returns:
        {success: bool, steps: int}
    """
    result = {"success": False, "steps_completed": 0}
    
    try:
        for i in range(steps):
            await page.evaluate("window.scrollBy(0, window.innerHeight);")
            await page.wait_for_timeout(delay_ms)
            result["steps_completed"] = i + 1
        
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def execute_action(
    page,
    action: Dict,
    runtime: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Execute action from LLM decision.
    
    Args:
        page: Playwright page
        action: {type, selector?, value?, ...}
        runtime: Runtime config
        
    Returns:
        Action result
    """
    runtime = runtime or {}
    action_type = action.get("type")
    
    if action_type == "click":
        return await click(
            page,
            selector=action.get("selector"),
            timeout_ms=int(action.get("timeoutMs") or runtime.get("action_timeout_ms") or 8000),
            smart_scroll=runtime.get("smart_click", True)
        )
    
    elif action_type == "fill":
        return await fill_field(
            page,
            selector=action.get("selector"),
            value=action.get("value", ""),
            timeout_ms=int(action.get("timeoutMs") or runtime.get("action_timeout_ms") or 8000)
        )
    
    elif action_type == "scroll":
        return await scroll_page(page)
    
    elif action_type == "wait":
        return await wait(page, ms=800 + int(random.random() * 1200))
    
    else:
        return {"success": False, "error": f"Unknown action type: {action_type}"}
