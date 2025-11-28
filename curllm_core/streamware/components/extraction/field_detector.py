"""
Field Detector - LLM-based field detection within containers.

NO REGEX - Uses LLM to identify product fields semantically.
"""
import json
from typing import Dict, Any, List, Optional


async def detect_product_fields(
    page,
    llm,
    container_selector: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Detect product fields (name, price, url, image) within containers using LLM.
    
    Returns:
        {
            "found": bool,
            "fields": {
                "name": {"selector": str, "sample": str},
                "price": {"selector": str, "sample": str},
                "url": {"selector": str, "sample": str},
                "image": {"selector": str, "sample": str}
            },
            "completeness": float
        }
    """
    if run_logger:
        run_logger.log_text(f"🔍 LLM Field Detection in {container_selector}")
    
    # Get structure of first container
    container_structure = await page.evaluate("""
        (selector) => {
            const container = document.querySelector(selector);
            if (!container) return null;
            
            const structure = {
                html: container.innerHTML.substring(0, 1000),
                text: container.textContent?.trim().substring(0, 300) || '',
                links: [],
                images: [],
                textNodes: []
            };
            
            // Get links
            container.querySelectorAll('a').forEach((a, i) => {
                if (i < 5) {
                    structure.links.push({
                        href: a.href,
                        text: a.textContent?.trim().substring(0, 50) || '',
                        classes: a.className
                    });
                }
            });
            
            // Get images
            container.querySelectorAll('img').forEach((img, i) => {
                if (i < 3) {
                    structure.images.push({
                        src: img.src,
                        alt: img.alt,
                        classes: img.className
                    });
                }
            });
            
            // Get distinct text elements
            const textElements = container.querySelectorAll('span, div, p, h1, h2, h3, h4, td');
            textElements.forEach((el, i) => {
                if (i < 10) {
                    const text = el.textContent?.trim();
                    if (text && text.length > 2 && text.length < 200) {
                        structure.textNodes.push({
                            tag: el.tagName.toLowerCase(),
                            text: text.substring(0, 100),
                            classes: el.className
                        });
                    }
                }
            });
            
            return structure;
        }
    """, container_selector)
    
    if not container_structure:
        return {"found": False, "fields": {}, "completeness": 0}
    
    # Ask LLM to identify fields
    prompt = f"""Analyze this product container and identify where each field is located.

Container: {container_selector}

Container content:
Text: {container_structure.get('text', '')[:200]}

Links found:
"""
    for link in container_structure.get('links', [])[:3]:
        prompt += f"  - {link.get('text', '')} -> {link.get('href', '')[:50]}\n"
    
    prompt += "\nImages found:\n"
    for img in container_structure.get('images', [])[:2]:
        prompt += f"  - alt=\"{img.get('alt', '')}\" class=\"{img.get('classes', '')}\"\n"
    
    prompt += "\nText elements:\n"
    for txt in container_structure.get('textNodes', [])[:5]:
        prompt += f"  - <{txt.get('tag')}> {txt.get('text', '')[:60]}\n"
    
    prompt += """
Identify the CSS selectors for:
1. Product NAME (title)
2. Product PRICE (cost)
3. Product URL (link to product page)
4. Product IMAGE (photo)

Output JSON:
{
    "name": {"selector": "CSS selector or null", "sample": "example value"},
    "price": {"selector": "CSS selector or null", "sample": "example value"},
    "url": {"selector": "CSS selector or null", "sample": "example URL"},
    "image": {"selector": "CSS selector or null", "sample": "example src"}
}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        
        if result:
            # Calculate completeness
            found_fields = sum(1 for v in result.values() if v and v.get('selector'))
            completeness = found_fields / 4.0
            
            if run_logger:
                run_logger.log_text(f"✅ Found {found_fields}/4 fields (completeness: {completeness:.0%})")
            
            return {
                "found": found_fields > 0,
                "fields": result,
                "completeness": completeness
            }
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ LLM field detection failed: {e}")
    
    return {"found": False, "fields": {}, "completeness": 0}


async def extract_field_value(
    page,
    llm,
    container_element,
    field_name: str,
    run_logger=None
) -> Optional[str]:
    """
    Extract a single field value from a container using LLM.
    
    This is for cases where selector-based extraction fails.
    LLM analyzes the container text and extracts the requested field.
    """
    # Get container content
    content = await page.evaluate("""
        (el) => {
            return {
                text: el.textContent?.trim().substring(0, 500) || '',
                links: Array.from(el.querySelectorAll('a')).map(a => ({
                    text: a.textContent?.trim(),
                    href: a.href
                })).slice(0, 5)
            };
        }
    """, container_element)
    
    if not content:
        return None
    
    prompt = f"""Extract the {field_name} from this product container.

Container text:
{content.get('text', '')}

Links: {content.get('links', [])}

What is the {field_name}? Just return the value, nothing else.
If you cannot find it, return "NOT_FOUND".

{field_name}:"""

    try:
        response = await _llm_generate(llm, prompt)
        value = response.strip()
        
        if value and value != "NOT_FOUND":
            return value
    except Exception:
        pass
    
    return None


async def detect_price_in_container(
    page,
    llm,
    container_selector: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Detect price format and location in container using LLM.
    
    Handles both text prices and image-based prices.
    """
    # Get container content
    content = await page.evaluate("""
        (selector) => {
            const container = document.querySelector(selector);
            if (!container) return null;
            
            return {
                text: container.textContent?.trim().substring(0, 300) || '',
                priceImages: Array.from(container.querySelectorAll('img')).filter(
                    img => /price|cena|cb_|cn_/i.test(img.src)
                ).map(img => img.src).slice(0, 3),
                hasNumbers: /\\d+[,.]?\\d*/.test(container.textContent || '')
            };
        }
    """, container_selector)
    
    if not content:
        return {"found": False, "format": "unknown"}
    
    prompt = f"""Find the price in this product container.

Container text: {content.get('text', '')}
Price-like images: {content.get('priceImages', [])}
Contains numbers: {content.get('hasNumbers')}

Is there a visible price? What format is it in?

Output JSON:
{{"found": true/false, "format": "text|image", "value": "extracted price or null", "currency": "PLN|EUR|USD|unknown"}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        if result:
            return result
    except Exception:
        pass
    
    return {"found": False, "format": "unknown"}


async def _llm_generate(llm, prompt: str) -> str:
    """Generate text from LLM."""
    if hasattr(llm, 'ainvoke'):
        result = await llm.ainvoke(prompt)
        if isinstance(result, dict):
            return result.get('text', str(result))
        return str(result)
    elif hasattr(llm, 'generate'):
        return await llm.generate(prompt)
    else:
        return str(await llm(prompt))


def _parse_json_response(response: str) -> Optional[Dict]:
    """Parse JSON from LLM response."""
    import re
    match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None
