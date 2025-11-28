"""
Page Context - Capture page state for LLM decisions

Provides structured context about current page state.
"""

from typing import Dict, Any, Optional


async def capture_context(page) -> Dict[str, Any]:
    """
    Capture full page context.
    
    Args:
        page: Playwright page
        
    Returns:
        {url, title, visible_text, form_count, link_count, ...}
    """
    result = {
        "url": "",
        "title": "",
        "visible_text": "",
        "form_count": 0,
        "link_count": 0,
        "headings": [],
        "meta": {}
    }
    
    try:
        result["url"] = page.url
        result["title"] = await page.title()
        
        context = await page.evaluate("""
        () => {
            const visibleText = document.body.innerText?.substring(0, 2000) || '';
            const forms = document.querySelectorAll('form');
            const links = document.querySelectorAll('a[href]');
            const headings = [];
            
            document.querySelectorAll('h1, h2, h3').forEach(h => {
                const text = h.innerText?.trim();
                if (text && text.length < 200) {
                    headings.push({
                        level: h.tagName,
                        text: text.substring(0, 100)
                    });
                }
            });
            
            const meta = {};
            document.querySelectorAll('meta').forEach(m => {
                const name = m.getAttribute('name') || m.getAttribute('property');
                const content = m.getAttribute('content');
                if (name && content) {
                    meta[name] = content.substring(0, 200);
                }
            });
            
            return {
                visible_text: visibleText,
                form_count: forms.length,
                link_count: links.length,
                headings: headings.slice(0, 10),
                meta: meta
            };
        }
        """)
        
        result.update(context)
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def capture_visible_text(
    page,
    max_length: int = 5000,
    selector: Optional[str] = None
) -> str:
    """
    Capture visible text from page or element.
    
    Args:
        page: Playwright page
        max_length: Maximum text length
        selector: Optional CSS selector
        
    Returns:
        Visible text content
    """
    try:
        if selector:
            text = await page.evaluate(f"""
            () => {{
                const el = document.querySelector('{selector}');
                return el ? el.innerText?.substring(0, {max_length}) || '' : '';
            }}
            """)
        else:
            text = await page.evaluate(f"""
            () => document.body.innerText?.substring(0, {max_length}) || ''
            """)
        return text
    except Exception:
        return ""


async def capture_form_state(
    page,
    form_selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    Capture state of forms on page.
    
    Args:
        page: Playwright page
        form_selector: Optional specific form
        
    Returns:
        {forms: [{fields, values, buttons}]}
    """
    result = {"forms": [], "count": 0}
    
    try:
        forms = await page.evaluate(f"""
        () => {{
            const selector = '{form_selector or "form"}';
            const forms = [];
            
            document.querySelectorAll(selector).forEach((form, i) => {{
                const fields = [];
                const buttons = [];
                
                // Get inputs
                form.querySelectorAll('input, textarea, select').forEach(input => {{
                    fields.push({{
                        type: input.type || input.tagName.toLowerCase(),
                        name: input.name || '',
                        id: input.id || '',
                        value: input.value || '',
                        required: input.required || false,
                        placeholder: input.placeholder || ''
                    }});
                }});
                
                // Get buttons
                form.querySelectorAll('button, input[type="submit"]').forEach(btn => {{
                    buttons.push({{
                        type: btn.type || 'button',
                        text: btn.innerText?.trim() || btn.value || '',
                        id: btn.id || ''
                    }});
                }});
                
                forms.push({{
                    index: i,
                    id: form.id || '',
                    action: form.action || '',
                    method: form.method || 'get',
                    fields: fields,
                    buttons: buttons
                }});
            }});
            
            return forms;
        }}
        """)
        
        result["forms"] = forms or []
        result["count"] = len(result["forms"])
        
    except Exception as e:
        result["error"] = str(e)
    
    return result
