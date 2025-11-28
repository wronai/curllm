"""
LLM-based Selector Discovery

No hardcoded selectors - LLM analyzes DOM to find elements.
"""
from typing import Dict, Any, Optional, List
import json
import re

try:
    from curllm_core.streamware.llm_client import get_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


async def find_selector_llm(
    page,
    description: str,
    context: Optional[str] = None
) -> Optional[str]:
    """
    Use LLM to find CSS selector for an element.
    
    Args:
        page: Playwright page
        description: What to find (e.g., "submit button", "email input")
        context: Optional DOM context to narrow search
        
    Returns:
        CSS selector or None
    """
    if not HAS_LLM:
        return None
    
    # Get DOM context if not provided
    if not context:
        context = await page.evaluate("""
        () => {
            const body = document.body;
            if (!body) return '';
            
            // Get relevant elements
            const elements = [];
            body.querySelectorAll('input, button, a, select, textarea, [role="button"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    elements.push({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        class: el.className || '',
                        type: el.type || '',
                        name: el.name || '',
                        text: (el.innerText || el.value || '').substring(0, 50),
                        placeholder: el.placeholder || ''
                    });
                }
            });
            return JSON.stringify(elements.slice(0, 50));
        }
        """)
    
    llm = get_llm()
    prompt = f"""Find CSS selector for: {description}

Elements on page:
{context}

Output ONLY the CSS selector. Examples:
- #my-button
- .submit-btn
- button[type="submit"]
- input[name="email"]

Selector:"""

    response = await llm.generate(prompt)
    
    # Clean and validate selector
    selector = response.strip().split('\n')[0].strip()
    
    if selector and (
        selector.startswith('#') or 
        selector.startswith('.') or 
        selector.startswith('[') or 
        re.match(r'^[a-z]', selector)
    ):
        # Verify selector exists
        try:
            exists = await page.evaluate(f"document.querySelector('{selector}') !== null")
            if exists:
                return selector
        except Exception:
            pass
    
    return None


async def find_all_selectors(
    page,
    element_type: str
) -> List[Dict[str, Any]]:
    """
    Find all selectors for a type of element.
    
    Args:
        page: Playwright page
        element_type: Type of elements (emails, links, products, buttons)
        
    Returns:
        List of {selector, text, ...}
    """
    js_by_type = {
        "emails": """
        () => {
            const results = [];
            document.querySelectorAll('a[href^="mailto:"], input[type="email"]').forEach(el => {
                results.push({
                    selector: el.id ? '#' + el.id : (el.href ? 'a[href="' + el.href + '"]' : null),
                    value: el.href ? el.href.replace('mailto:', '') : el.value,
                    tag: el.tagName.toLowerCase()
                });
            });
            // Also find email patterns in text
            const text = document.body.innerText;
            const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
            const matches = text.match(emailRegex) || [];
            matches.forEach(email => {
                if (!results.some(r => r.value === email)) {
                    results.push({selector: null, value: email, tag: 'text'});
                }
            });
            return results;
        }
        """,
        "links": """
        () => {
            const results = [];
            document.querySelectorAll('a[href]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    results.push({
                        selector: el.id ? '#' + el.id : null,
                        href: el.href,
                        text: el.innerText.substring(0, 100)
                    });
                }
            });
            return results.slice(0, 100);
        }
        """,
        "buttons": """
        () => {
            const results = [];
            document.querySelectorAll('button, input[type="submit"], [role="button"]').forEach((el, i) => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    results.push({
                        selector: el.id ? '#' + el.id : 'button:nth-of-type(' + (i+1) + ')',
                        text: (el.innerText || el.value || '').substring(0, 50),
                        type: el.type || ''
                    });
                }
            });
            return results;
        }
        """
    }
    
    js = js_by_type.get(element_type)
    if not js:
        return []
    
    try:
        return await page.evaluate(js) or []
    except Exception:
        return []
