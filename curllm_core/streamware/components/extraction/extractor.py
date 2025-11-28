"""
Data Extraction from DOM

DEPRECATED: Use llm_extractor.py for pure LLM-based extraction.
This module is kept for backward compatibility only.

For new code, use:
    from .llm_extractor import LLMIterativeExtractor, llm_extract_products
"""
import warnings
from typing import Dict, Any, Optional, List
import json

try:
    from curllm_core.streamware.llm_client import get_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

# Deprecation warning
warnings.warn(
    "extractor.py is deprecated. Use llm_extractor.py for pure LLM-based extraction.",
    DeprecationWarning,
    stacklevel=2
)


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
    # Use dynamic container detection - no hardcoded selectors
    from .container import detect_containers, extract_from_container
    
    try:
        # Step 1: Detect containers dynamically
        detection = await detect_containers(page, entity_type="product", min_count=3)
        
        if detection.get("found") and detection.get("best"):
            container_selector = detection["best"]["selector"]
            
            # Step 2: Extract from detected containers
            result = await extract_from_container(
                page, 
                container_selector,
                max_items=max_items
            )
            
            return {
                "data": result.get("items", [])[:max_items],
                "count": result.get("count", 0),
                "container": container_selector
            }
        
        # Fallback: Use statistical pattern detection
        products = await page.evaluate("""
        () => {
            const products = [];
            const priceRegex = /(\\d+[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN|€|\\$|USD|EUR)/i;
            
            // Find elements with prices
            document.querySelectorAll('*').forEach(el => {
                const text = (el.innerText || '').substring(0, 500);
                if (!priceRegex.test(text)) return;
                
                const rect = el.getBoundingClientRect();
                if (rect.width < 100 || rect.height < 50) return;
                
                // Get name from heading or link
                const headings = el.querySelectorAll('h1, h2, h3, h4, a');
                let name = '';
                headings.forEach(h => {
                    const t = (h.innerText || '').trim();
                    if (t.length > name.length && t.length < 200) name = t;
                });
                
                const priceMatch = text.match(priceRegex);
                const link = el.querySelector('a[href]');
                
                if (name && priceMatch) {
                    products.push({
                        name: name.substring(0, 100),
                        price: priceMatch[0],
                        url: link ? link.href : ''
                    });
                }
            });
            
            return products.slice(0, 50);
        }
        """)
        
        # Deduplicate
        seen = set()
        unique = []
        for p in (products or []):
            key = (p.get("name", ""), p.get("url", ""))
            if key not in seen and p.get("name"):
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
