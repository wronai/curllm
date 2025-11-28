"""
Data Extraction from DOM

Atomic extraction functions using LLM for pattern detection.
"""
from typing import Dict, Any, Optional, List
import re
import json

try:
    from curllm_core.streamware.llm_client import get_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


async def extract_data(
    page,
    data_type: str,
    selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract data of specified type from page.
    
    Args:
        page: Playwright page
        data_type: What to extract (emails, links, products, phones)
        selector: Optional CSS selector to narrow scope
        
    Returns:
        {data: [...], count: int}
    """
    extractors = {
        "emails": extract_emails,
        "links": extract_links,
        "phones": extract_phones,
        "products": extract_products
    }
    
    extractor = extractors.get(data_type)
    if extractor:
        return await extractor(page, selector)
    
    return {"data": [], "count": 0, "error": f"Unknown data type: {data_type}"}


async def extract_emails(page, selector: Optional[str] = None) -> Dict[str, Any]:
    """Extract email addresses from page."""
    js = f"""
    () => {{
        const container = {f'document.querySelector("{selector}")' if selector else 'document'};
        if (!container) return [];
        
        const emails = new Set();
        
        // From mailto links
        container.querySelectorAll('a[href^="mailto:"]').forEach(a => {{
            const email = a.href.replace('mailto:', '').split('?')[0];
            if (email) emails.add(email);
        }});
        
        // From text content
        const text = container.innerText || '';
        const regex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}/g;
        (text.match(regex) || []).forEach(e => emails.add(e));
        
        return Array.from(emails);
    }}
    """
    try:
        emails = await page.evaluate(js) or []
        return {"data": emails, "count": len(emails)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}


async def extract_links(
    page, 
    selector: Optional[str] = None,
    href_filter: Optional[str] = None
) -> Dict[str, Any]:
    """Extract links from page."""
    js = f"""
    () => {{
        const container = {f'document.querySelector("{selector}")' if selector else 'document'};
        if (!container) return [];
        
        const links = [];
        container.querySelectorAll('a[href]').forEach(a => {{
            const rect = a.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {{
                links.push({{
                    href: a.href,
                    text: (a.innerText || '').trim().substring(0, 100)
                }});
            }}
        }});
        return links.slice(0, 200);
    }}
    """
    try:
        links = await page.evaluate(js) or []
        
        # Filter by href pattern if provided
        if href_filter:
            links = [l for l in links if href_filter.lower() in l.get("href", "").lower()]
        
        return {"data": links, "count": len(links)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}


async def extract_phones(page, selector: Optional[str] = None) -> Dict[str, Any]:
    """Extract phone numbers from page."""
    js = f"""
    () => {{
        const container = {f'document.querySelector("{selector}")' if selector else 'document'};
        if (!container) return [];
        
        const phones = new Set();
        
        // From tel links
        container.querySelectorAll('a[href^="tel:"]').forEach(a => {{
            const phone = a.href.replace('tel:', '');
            if (phone) phones.add(phone);
        }});
        
        // From text using regex patterns
        const text = container.innerText || '';
        const patterns = [
            /\\+?[0-9]{{1,3}}[-. ]?\\(?[0-9]{{2,3}}\\)?[-. ]?[0-9]{{3}}[-. ]?[0-9]{{2,4}}/g,
            /\\+48[-. ]?[0-9]{{3}}[-. ]?[0-9]{{3}}[-. ]?[0-9]{{3}}/g
        ];
        patterns.forEach(regex => {{
            (text.match(regex) || []).forEach(p => phones.add(p.trim()));
        }});
        
        return Array.from(phones);
    }}
    """
    try:
        phones = await page.evaluate(js) or []
        return {"data": phones, "count": len(phones)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}


async def extract_products(
    page, 
    selector: Optional[str] = None,
    max_items: int = 50
) -> Dict[str, Any]:
    """
    Extract product data using LLM for pattern detection.
    """
    # First, get page structure
    js = """
    () => {
        const products = [];
        
        // Find potential product containers
        const containers = document.querySelectorAll(
            '[class*="product"], [class*="item"], [class*="card"], article, .woocommerce-loop-product__link'
        );
        
        containers.forEach((el, i) => {
            if (i >= 100) return;
            
            const rect = el.getBoundingClientRect();
            if (rect.width < 100 || rect.height < 50) return;
            
            // Try to find product info
            const nameEl = el.querySelector('h1, h2, h3, h4, .product-title, .title, [class*="name"]');
            const priceEl = el.querySelector('[class*="price"], .amount');
            const linkEl = el.querySelector('a[href]');
            
            if (nameEl || priceEl) {
                products.push({
                    name: nameEl ? nameEl.innerText.trim().substring(0, 100) : '',
                    price: priceEl ? priceEl.innerText.trim() : '',
                    url: linkEl ? linkEl.href : ''
                });
            }
        });
        
        return products;
    }
    """
    
    try:
        products = await page.evaluate(js) or []
        
        # Filter empty and deduplicate
        seen = set()
        unique = []
        for p in products:
            key = (p.get("name", ""), p.get("url", ""))
            if key not in seen and (p.get("name") or p.get("price")):
                seen.add(key)
                unique.append(p)
        
        return {"data": unique[:max_items], "count": len(unique)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)}


async def extract_with_llm(
    page,
    instruction: str
) -> Dict[str, Any]:
    """
    Use LLM to extract data based on natural language instruction.
    
    Args:
        page: Playwright page
        instruction: What to extract (e.g., "all article titles")
        
    Returns:
        {data: [...], selector: str}
    """
    if not HAS_LLM:
        return {"data": [], "error": "LLM not available"}
    
    # Get page context
    context = await page.evaluate("""
    () => {
        const headings = [];
        document.querySelectorAll('h1, h2, h3').forEach(h => {
            headings.push(h.innerText.substring(0, 100));
        });
        
        const links = [];
        document.querySelectorAll('a[href]').forEach((a, i) => {
            if (i < 20) {
                links.push({text: a.innerText.substring(0, 50), href: a.href});
            }
        });
        
        return {headings, links, url: window.location.href};
    }
    """)
    
    llm = get_llm()
    prompt = f"""Extract from page: {instruction}

Page context:
{json.dumps(context, ensure_ascii=False)}

Return JSON with extracted data:
{{"data": [...], "selector": "CSS selector used"}}

JSON:"""

    response = await llm.generate(prompt)
    
    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    
    return {"data": [], "error": "LLM extraction failed"}
