"""
Screenshot Capture - Atomic screenshot operations

Each function captures screenshots and returns path + metadata.
"""

import os
import time
from typing import Dict, Any, Optional
from urllib.parse import urlparse


def get_screenshot_path(
    url: str = "",
    prefix: str = "screenshot",
    base_dir: str = "screenshots"
) -> str:
    """
    Generate screenshot path based on URL and timestamp.
    
    Args:
        url: Page URL for subdirectory
        prefix: Filename prefix
        base_dir: Base screenshots directory
        
    Returns:
        Full path like: screenshots/example.com/screenshot_12345.png
    """
    # Create subdirectory from domain
    if url:
        parsed = urlparse(url)
        domain = parsed.netloc or "unknown"
        subdir = os.path.join(base_dir, domain)
    else:
        subdir = base_dir
    
    # Ensure directory exists
    os.makedirs(subdir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = int(time.time() * 1000)
    filename = f"{prefix}_{timestamp}.png"
    
    return os.path.join(subdir, filename)


async def capture_page(
    page,
    path: Optional[str] = None,
    full_page: bool = True
) -> Dict[str, Any]:
    """
    Capture full page screenshot.
    
    Args:
        page: Playwright page
        path: Save path (generated if None)
        full_page: Capture full scrollable page
        
    Returns:
        {success: bool, path: str, error: str|None}
    """
    result = {"success": False, "path": None, "error": None}
    
    try:
        if not path:
            path = get_screenshot_path(url=page.url, prefix="page")
        
        await page.screenshot(path=path, full_page=full_page)
        result["success"] = True
        result["path"] = path
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def capture_element(
    page,
    selector: str,
    path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Capture screenshot of specific element.
    
    Args:
        page: Playwright page
        selector: CSS selector for element
        path: Save path (generated if None)
        
    Returns:
        {success: bool, path: str, selector: str, error: str|None}
    """
    result = {"success": False, "path": None, "selector": selector, "error": None}
    
    try:
        if not path:
            path = get_screenshot_path(url=page.url, prefix="element")
        
        # Find element
        element = await page.query_selector(selector)
        
        if element:
            # Scroll to element first
            await page.evaluate(f"""
                const el = document.querySelector('{selector}');
                if (el) el.scrollIntoView({{behavior: 'instant', block: 'center'}});
            """)
            await page.wait_for_timeout(300)
            
            # Capture element
            await element.screenshot(path=path)
            result["success"] = True
            result["path"] = path
        else:
            # Fallback to viewport screenshot
            await page.screenshot(path=path)
            result["success"] = True
            result["path"] = path
            result["fallback"] = "viewport"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def capture_viewport(
    page,
    path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Capture visible viewport screenshot.
    
    Args:
        page: Playwright page
        path: Save path (generated if None)
        
    Returns:
        {success: bool, path: str, error: str|None}
    """
    result = {"success": False, "path": None, "error": None}
    
    try:
        if not path:
            path = get_screenshot_path(url=page.url, prefix="viewport")
        
        await page.screenshot(path=path, full_page=False)
        result["success"] = True
        result["path"] = path
        
    except Exception as e:
        result["error"] = str(e)
    
    return result
