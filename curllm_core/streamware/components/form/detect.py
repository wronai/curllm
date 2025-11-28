"""
Form Detection - finds forms and fields on page via JS evaluation.
No hardcoded selectors - returns what's actually on page.
"""
from typing import Dict, Any, List, Optional

# JS to detect all forms and their fields
DETECT_FORMS_JS = """
() => {
    const forms = [];
    document.querySelectorAll('form').forEach((form, idx) => {
        const fields = [];
        form.querySelectorAll('input, textarea, select, button').forEach(el => {
            const rect = el.getBoundingClientRect();
            const visible = rect.width > 0 && rect.height > 0 && 
                           getComputedStyle(el).display !== 'none' &&
                           getComputedStyle(el).visibility !== 'hidden';
            if (!visible) return;
            
            fields.push({
                tag: el.tagName.toLowerCase(),
                type: el.type || el.tagName.toLowerCase(),
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                required: el.required || false,
                value: el.value || '',
                selector: el.id ? `#${el.id}` : (el.name ? `[name="${el.name}"]` : null)
            });
        });
        
        if (fields.length > 0) {
            forms.push({
                id: form.id || `form-${idx}`,
                selector: form.id ? `#${form.id}` : `form:nth-of-type(${idx + 1})`,
                action: form.action || '',
                fields: fields,
                score: fields.filter(f => ['email', 'text', 'textarea'].includes(f.type)).length
            });
        }
    });
    return forms.sort((a, b) => b.score - a.score);
}
"""


async def detect_forms(page) -> List[Dict[str, Any]]:
    """Detect all forms on page. Returns list sorted by relevance score."""
    try:
        return await page.evaluate(DETECT_FORMS_JS) or []
    except Exception as e:
        return [{"error": str(e)}]


async def detect_form(page) -> Dict[str, Any]:
    """Detect best form on page."""
    forms = await detect_forms(page)
    if not forms:
        return {"found": False, "form_id": None, "fields": [], "selector": None}
    
    best = forms[0]
    return {
        "found": True,
        "form_id": best.get("id"),
        "selector": best.get("selector"),
        "fields": best.get("fields", []),
        "score": best.get("score", 0)
    }


async def get_field_selectors(page, form_selector: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all field selectors from a form or page."""
    js = f"""
    () => {{
        const container = {f'document.querySelector("{form_selector}")' if form_selector else 'document'};
        if (!container) return [];
        const fields = [];
        container.querySelectorAll('input, textarea, select').forEach(el => {{
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {{
                fields.push({{
                    tag: el.tagName.toLowerCase(),
                    type: el.type || el.tagName.toLowerCase(),
                    name: el.name || '',
                    id: el.id || '',
                    selector: el.id ? '#' + el.id : (el.name ? '[name="' + el.name + '"]' : null),
                    placeholder: el.placeholder || ''
                }});
            }}
        }});
        return fields;
    }}
    """
    try:
        return await page.evaluate(js) or []
    except Exception:
        return []
