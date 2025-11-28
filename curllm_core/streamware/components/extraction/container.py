"""
Container Detection - Dynamic container discovery for extraction

DEPRECATED: Use container_finder.py for pure LLM-based detection.
This module is kept for backward compatibility only.

For new code, use:
    from .container_finder import find_product_containers, analyze_container_content
"""
import warnings
from typing import Dict, Any, List, Optional
import json

# Deprecation warning
warnings.warn(
    "container.py is deprecated. Use container_finder.py for pure LLM-based detection.",
    DeprecationWarning,
    stacklevel=2
)


async def detect_containers(
    page,
    entity_type: str = "product",
    min_count: int = 3
) -> Dict[str, Any]:
    """
    Detect repeating containers on page.
    
    Uses statistical analysis to find elements that repeat with similar structure.
    
    Args:
        page: Playwright page
        entity_type: Type hint for LLM (product, article, comment)
        min_count: Minimum elements to consider a container
        
    Returns:
        {
            found: bool,
            containers: [{selector, count, sample_text, has_price, has_link}],
            best: {selector, count, confidence}
        }
    """
    result = {
        "found": False,
        "containers": [],
        "best": None
    }
    
    try:
        # Statistical analysis of repeating elements
        candidates = await page.evaluate(f"""
        () => {{
            const minCount = {min_count};
            const candidates = [];
            const classCount = {{}};
            
            // Count class occurrences
            document.querySelectorAll('*').forEach(el => {{
                if (!el.className || typeof el.className !== 'string') return;
                const firstClass = el.className.split(' ')[0];
                if (firstClass && firstClass.length > 2) {{
                    classCount[firstClass] = (classCount[firstClass] || 0) + 1;
                }}
            }});
            
            // Find classes with significant repetition
            for (const [cls, count] of Object.entries(classCount)) {{
                if (count < minCount) continue;
                
                // Analyze elements with this class
                const elements = document.querySelectorAll('.' + cls);
                let hasPrice = 0, hasLink = 0, hasImage = 0;
                let sampleText = '';
                
                const priceRegex = /\\d+[\\d\\s]*(?:[\\.,]\\d{{2}})?\\s*(?:zł|PLN|€|\\$|USD|EUR)/i;
                
                elements.forEach((el, i) => {{
                    const text = (el.innerText || '').trim();
                    if (i === 0) sampleText = text.substring(0, 100);
                    if (priceRegex.test(text)) hasPrice++;
                    if (el.querySelector('a[href]')) hasLink++;
                    if (el.querySelector('img')) hasImage++;
                }});
                
                // Score candidate
                let score = 0;
                score += count >= 5 ? 30 : count >= 3 ? 15 : 0;
                score += hasPrice > count * 0.5 ? 40 : hasPrice > 0 ? 20 : 0;
                score += hasLink > count * 0.5 ? 20 : hasLink > 0 ? 10 : 0;
                score += hasImage > count * 0.3 ? 15 : hasImage > 0 ? 5 : 0;
                
                if (score > 20) {{
                    candidates.push({{
                        selector: '.' + cls,
                        count: count,
                        sample_text: sampleText,
                        has_price: hasPrice > 0,
                        has_link: hasLink > 0,
                        has_image: hasImage > 0,
                        score: score
                    }});
                }}
            }});
            
            // Sort by score
            candidates.sort((a, b) => b.score - a.score);
            return candidates.slice(0, 10);
        }}
        """)
        
        if candidates:
            result["found"] = True
            result["containers"] = candidates
            result["best"] = candidates[0] if candidates else None
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def detect_container_with_llm(
    page,
    instruction: str,
    dom_sample: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use LLM to find best container selector for instruction.
    
    Args:
        page: Playwright page
        instruction: User's extraction instruction
        dom_sample: Optional DOM sample (generated if None)
        
    Returns:
        {selector: str, reasoning: str, confidence: float}
    """
    result = {"selector": None, "reasoning": "", "confidence": 0}
    
    try:
        from curllm_core.streamware.llm_client import get_llm
        llm = get_llm()
    except ImportError:
        result["error"] = "LLM not available"
        return result
    
    try:
        # Get DOM sample if not provided
        if not dom_sample:
            dom_sample = await page.evaluate("""
            () => {
                const elements = [];
                document.querySelectorAll('*').forEach((el, i) => {
                    if (i > 300) return;
                    if (!el.className && !el.id) return;
                    const text = (el.innerText || '').trim().substring(0, 50);
                    if (text.length < 5) return;
                    elements.push({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        class: (typeof el.className === 'string' ? el.className : '').substring(0, 80),
                        text: text
                    });
                });
                return JSON.stringify(elements.slice(0, 50), null, 2);
            }
            """)
        
        prompt = f"""Analyze DOM and find CSS selector for: {instruction}

DOM sample:
{dom_sample[:3000]}

Return JSON:
{{"selector": "CSS selector", "reasoning": "why this selector", "confidence": 0.0-1.0}}

JSON:"""
        
        response = await llm.generate(prompt)
        
        import re
        match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if match:
            data = json.loads(match.group())
            result["selector"] = data.get("selector")
            result["reasoning"] = data.get("reasoning", "")
            result["confidence"] = float(data.get("confidence", 0))
            
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def extract_from_container(
    page,
    container_selector: str,
    fields: List[str] = None,
    max_items: int = 50
) -> Dict[str, Any]:
    """
    Extract data from detected containers.
    
    Args:
        page: Playwright page
        container_selector: CSS selector for containers
        fields: Fields to extract (auto-detect if None)
        max_items: Maximum items to extract
        
    Returns:
        {items: [...], count: int}
    """
    result = {"items": [], "count": 0}
    
    if not fields:
        fields = ["name", "price", "url", "image"]
    
    try:
        items = await page.evaluate(f"""
        (selector, maxItems) => {{
            const items = [];
            const containers = document.querySelectorAll(selector);
            
            const priceRegex = /(\\d+[\\d\\s]*(?:[\\.,]\\d{{2}})?)\\s*(?:zł|PLN|€|\\$|USD|EUR)/i;
            
            for (let i = 0; i < Math.min(containers.length, maxItems); i++) {{
                const el = containers[i];
                const item = {{}};
                
                // Name: longest text or heading
                const headings = el.querySelectorAll('h1, h2, h3, h4, a');
                let name = '';
                headings.forEach(h => {{
                    const t = (h.innerText || '').trim();
                    if (t.length > name.length && t.length < 200) name = t;
                }});
                if (!name) name = (el.innerText || '').split('\\n')[0].substring(0, 100);
                item.name = name;
                
                // Price
                const text = el.innerText || '';
                const priceMatch = text.match(priceRegex);
                if (priceMatch) {{
                    const priceStr = priceMatch[1].replace(/\\s/g, '').replace(',', '.');
                    item.price = parseFloat(priceStr) || null;
                    item.price_text = priceMatch[0];
                }}
                
                // URL
                const link = el.querySelector('a[href]');
                if (link) item.url = link.href;
                
                // Image
                const img = el.querySelector('img[src]');
                if (img) item.image = img.src;
                
                if (item.name) items.push(item);
            }}
            
            return items;
        }}
        """, container_selector, max_items)
        
        result["items"] = items or []
        result["count"] = len(result["items"])
        
    except Exception as e:
        result["error"] = str(e)
    
    return result
