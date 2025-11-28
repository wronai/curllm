"""
DOM Query - Atomic DOM query operations

Simple, composable queries without hardcoded selectors.
"""

from typing import Dict, Any, List, Optional


async def query_elements(
    page,
    selector: str,
    max_count: int = 100
) -> List[Dict[str, Any]]:
    """
    Query elements by selector.
    
    Args:
        page: Playwright page
        selector: CSS selector
        max_count: Maximum elements to return
        
    Returns:
        [{tag, id, class, text, href, ...}]
    """
    try:
        elements = await page.evaluate(f"""
        (selector, max) => {{
            const results = [];
            const els = document.querySelectorAll(selector);
            
            for (let i = 0; i < Math.min(els.length, max); i++) {{
                const el = els[i];
                results.push({{
                    tag: el.tagName.toLowerCase(),
                    id: el.id || '',
                    class: (typeof el.className === 'string' ? el.className : '').substring(0, 100),
                    text: (el.innerText || '').substring(0, 200),
                    href: el.href || '',
                    src: el.src || ''
                }});
            }}
            
            return results;
        }}
        """, selector, max_count)
        return elements or []
    except Exception:
        return []


async def query_text(
    page,
    selector: str
) -> List[str]:
    """
    Query text content of elements.
    
    Args:
        page: Playwright page
        selector: CSS selector
        
    Returns:
        List of text contents
    """
    try:
        texts = await page.evaluate(f"""
        (selector) => {{
            const texts = [];
            document.querySelectorAll(selector).forEach(el => {{
                const text = (el.innerText || '').trim();
                if (text) texts.push(text);
            }});
            return texts;
        }}
        """, selector)
        return texts or []
    except Exception:
        return []


async def query_attributes(
    page,
    selector: str,
    attribute: str
) -> List[str]:
    """
    Query specific attribute from elements.
    
    Args:
        page: Playwright page
        selector: CSS selector
        attribute: Attribute name (href, src, data-*, etc.)
        
    Returns:
        List of attribute values
    """
    try:
        values = await page.evaluate(f"""
        (selector, attr) => {{
            const values = [];
            document.querySelectorAll(selector).forEach(el => {{
                const val = el.getAttribute(attr);
                if (val) values.push(val);
            }});
            return values;
        }}
        """, selector, attribute)
        return values or []
    except Exception:
        return []


async def query_count(page, selector: str) -> int:
    """Count elements matching selector."""
    try:
        return await page.evaluate(f"""
        (selector) => document.querySelectorAll(selector).length
        """, selector) or 0
    except Exception:
        return 0


async def query_exists(page, selector: str) -> bool:
    """Check if element exists."""
    try:
        return await page.evaluate(f"""
        (selector) => document.querySelector(selector) !== null
        """, selector)
    except Exception:
        return False


async def query_visible(page, selector: str) -> bool:
    """Check if element is visible."""
    try:
        return await page.evaluate(f"""
        (selector) => {{
            const el = document.querySelector(selector);
            if (!el) return false;
            const rect = el.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
        }}
        """, selector)
    except Exception:
        return False
