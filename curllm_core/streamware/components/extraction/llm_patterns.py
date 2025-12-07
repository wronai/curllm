"""
LLM Pattern Generator - Dynamic selectors and patterns from LLM.

NO HARDCODED SELECTORS - LLM generates everything based on DOM context.
NO REGEX IN CODE - LLM provides regex patterns when needed.

This module replaces:
- Hardcoded CSS selectors
- Hardcoded regex patterns
- Fixed price/currency patterns
- Static product link detection
"""
import json
from typing import Dict, Any, List, Optional, Tuple


async def generate_price_pattern(
    page,
    llm,
    run_logger=None
) -> Dict[str, Any]:
    """
    LLM generates regex pattern for prices based on actual page content.
    
    Returns:
        {
            "pattern": "regex pattern",
            "currency": "PLN|EUR|USD",
            "format": "text|image",
            "examples": ["100 zł", "99,99 PLN"]
        }
    """
    # Get price-like content from page
    samples = await page.evaluate("""
        () => {
            const samples = [];
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            let node;
            while ((node = walker.nextNode()) && samples.length < 30) {
                const text = node.textContent.trim();
                // Look for text with digits and potential currency
                if (text.length > 2 && text.length < 50 && /\\d/.test(text)) {
                    samples.push(text);
                }
            }
            
            // Also check for price images
            const priceImgs = document.querySelectorAll('img[src*="price"], img[src*="cena"], img[src*="cb_"], img[src*="cn_"]');
            
            return {
                textSamples: samples.slice(0, 20),
                priceImageCount: priceImgs.length,
                hasPriceImages: priceImgs.length > 0
            };
        }
    """)
    
    prompt = f"""Analyze these text samples from a webpage and generate a regex pattern to match prices.

Text samples containing digits:
{samples.get('textSamples', [])[:15]}

Price images found: {samples.get('priceImageCount', 0)}

Based on these examples, create a regex pattern that will match prices on this page.
Consider:
- Currency format (zł, PLN, €, $, etc.)
- Number format (comma vs dot for decimals)
- Spacing and special characters

Output JSON:
{{
    "pattern": "regex pattern as string",
    "currency": "PLN|EUR|USD|other",
    "format": "text|image|both",
    "examples": ["matched example 1", "matched example 2"],
    "explanation": "why this pattern"
}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        if result:
            if run_logger:
                run_logger.log_text(f"✅ Generated price pattern: {result.get('pattern')}")
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ Price pattern generation failed: {e}")
    
    return {"pattern": None, "currency": "unknown", "format": "unknown"}


async def generate_product_link_pattern(
    page,
    llm,
    run_logger=None
) -> Dict[str, Any]:
    """
    LLM generates regex pattern for product links based on actual URLs.
    
    Returns:
        {
            "pattern": "regex pattern",
            "examples": ["url1", "url2"],
            "selector": "CSS selector for product links"
        }
    """
    # Get links from page
    links = await page.evaluate("""
        () => {
            const links = [];
            for (const a of document.links) {
                if (a.href && a.href.startsWith('http')) {
                    links.push({
                        href: a.href,
                        text: a.textContent?.trim().substring(0, 50) || '',
                        classes: a.className
                    });
                }
            }
            return links.slice(0, 30);
        }
    """)
    
    prompt = f"""Analyze these links from an e-commerce page and identify which are PRODUCT links.

Links found:
"""
    for link in links[:20]:
        prompt += f"  {link.get('href', '')[:80]} - \"{link.get('text', '')[:30]}\"\n"
    
    prompt += """
Product links typically:
- Have product IDs (numbers) in the URL
- Lead to product detail pages
- Have product names in the text

Generate:
1. A regex pattern to match product link URLs
2. A CSS selector to find product link elements

Output JSON:
{
    "pattern": "regex pattern for URLs",
    "selector": "CSS selector",
    "examples": ["example url 1", "example url 2"],
    "explanation": "why these are product links"
}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        if result:
            if run_logger:
                run_logger.log_text(f"✅ Generated product link pattern: {result.get('pattern')}")
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ Product link pattern generation failed: {e}")
    
    return {"pattern": None, "selector": None}


async def generate_container_selector(
    page,
    llm,
    content_type: str = "products",
    run_logger=None
) -> Dict[str, Any]:
    """
    LLM generates CSS selector for containers based on DOM analysis.
    
    Args:
        content_type: "products" | "articles" | "items" | "cards"
    
    Returns:
        {
            "selector": "CSS selector",
            "count": int,
            "confidence": float,
            "alternatives": ["selector1", "selector2"]
        }
    """
    # Get DOM structure
    structure = await page.evaluate("""
        () => {
            const classCounts = {};
            
            document.querySelectorAll('*').forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    const classes = el.className.split(' ').filter(c => c.length > 2);
                    for (const cls of classes) {
                        if (!classCounts[cls]) {
                            classCounts[cls] = { count: 0, samples: [] };
                        }
                        classCounts[cls].count++;
                        
                        if (classCounts[cls].samples.length < 2) {
                            classCounts[cls].samples.push({
                                tag: el.tagName.toLowerCase(),
                                text: el.textContent?.trim().substring(0, 80) || '',
                                hasImage: el.querySelector('img') !== null,
                                hasLink: el.querySelector('a') !== null
                            });
                        }
                    }
                }
            });
            
            // Get classes with 3+ elements (potential containers)
            const candidates = [];
            for (const [cls, data] of Object.entries(classCounts)) {
                if (data.count >= 3 && data.count <= 100) {
                    candidates.push({
                        class: cls,
                        count: data.count,
                        samples: data.samples
                    });
                }
            }
            
            return candidates.sort((a, b) => b.count - a.count).slice(0, 15);
        }
    """)
    
    prompt = f"""Find the CSS selector for {content_type} containers on this page.

DOM classes with multiple elements:
"""
    for item in structure[:12]:
        samples = item.get('samples', [])
        sample_info = ""
        if samples:
            s = samples[0]
            sample_info = f"tag={s.get('tag')}, img={s.get('hasImage')}, link={s.get('hasLink')}, text=\"{s.get('text', '')[:40]}\""
        prompt += f"  .{item['class']} ({item['count']}x) - {sample_info}\n"
    
    prompt += f"""
I need the selector for {content_type}. A good {content_type} container:
- Contains multiple similar items
- Each item has content (text, maybe images)
- NOT navigation, NOT footer, NOT header

Output JSON:
{{
    "selector": ".best-class-name",
    "count": number_of_elements,
    "confidence": 0.0-1.0,
    "alternatives": [".alt1", ".alt2"],
    "reasoning": "why this selector"
}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        if result:
            if run_logger:
                run_logger.log_text(f"✅ Generated container selector: {result.get('selector')}")
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ Container selector generation failed: {e}")
    
    return {"selector": None, "count": 0, "confidence": 0}


async def generate_field_selector(
    page,
    llm,
    container_selector: str,
    field_name: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    LLM generates CSS selector for a specific field within a container.
    
    Args:
        container_selector: Parent container selector
        field_name: "name" | "price" | "url" | "image" | "description"
    
    Returns:
        {
            "selector": "CSS selector relative to container",
            "sample_value": "example value",
            "confidence": float
        }
    """
    # Get container content
    content = await page.evaluate("""
        (selector) => {
            const container = document.querySelector(selector);
            if (!container) return null;
            
            const elements = [];
            
            // Get all text-containing elements
            container.querySelectorAll('*').forEach(el => {
                const text = el.textContent?.trim();
                if (text && text.length > 0 && text.length < 200) {
                    elements.push({
                        tag: el.tagName.toLowerCase(),
                        classes: el.className || '',
                        text: text.substring(0, 100),
                        isLink: el.tagName === 'A',
                        href: el.href || null,
                        isImage: el.tagName === 'IMG',
                        src: el.src || null
                    });
                }
            });
            
            return elements.slice(0, 20);
        }
    """, container_selector)
    
    if not content:
        return {"selector": None, "confidence": 0}
    
    prompt = f"""Find the CSS selector for the {field_name} field within this container.

Container: {container_selector}

Elements inside container:
"""
    for el in content[:15]:
        if el.get('isImage'):
            prompt += f"  <img class=\"{el.get('classes', '')}\" src=\"{el.get('src', '')[:50]}\">\n"
        elif el.get('isLink'):
            prompt += f"  <a class=\"{el.get('classes', '')}\" href=\"{el.get('href', '')[:50]}\">{el.get('text', '')[:40]}</a>\n"
        else:
            prompt += f"  <{el.get('tag')} class=\"{el.get('classes', '')}\">{el.get('text', '')[:50]}</{el.get('tag')}>\n"
    
    prompt += f"""
I need the selector for: {field_name}

Field hints:
- name/title: Usually prominent text, often in a link or heading
- price: Contains numbers and currency (zł, PLN, €, $)
- url: Link to product page
- image: Product photo
- description: Longer text describing the item

Output JSON:
{{
    "selector": "CSS selector (relative to container)",
    "sample_value": "example value found",
    "confidence": 0.0-1.0,
    "reasoning": "why this element is the {field_name}"
}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        if result:
            if run_logger:
                run_logger.log_text(f"✅ Generated {field_name} selector: {result.get('selector')}")
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ {field_name} selector generation failed: {e}")
    
    return {"selector": None, "confidence": 0}


async def generate_extraction_strategy(
    page,
    llm,
    instruction: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    LLM generates complete extraction strategy based on page and instruction.
    
    Uses LLM heuristics discovery for dynamic pattern detection.
    
    Returns:
        {
            "container_selector": str,
            "fields": {
                "name": {"selector": str, "type": "text"},
                "price": {"selector": str, "type": "text|image"},
                "url": {"selector": str, "type": "attribute:href"}
            },
            "filters": {
                "price_max": float | None,
                "price_pattern": str
            }
        }
    """
    # Discover dynamic heuristics first
    discovered_patterns = {}
    try:
        from curllm_core.llm_heuristics import LLMHeuristicsDiscovery
        discovery = LLMHeuristicsDiscovery(page, llm, run_logger)
        discovered_patterns = await discovery.build_dynamic_selectors()
        if run_logger:
            run_logger.log_text(f"🔍 Discovered URL patterns: {discovered_patterns.get('discovered_patterns', {}).get('links', [])[:3]}")
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ Heuristics discovery skipped: {e}")
    
    # Get page overview
    overview = await page.evaluate("""
        () => {
            return {
                title: document.title,
                url: window.location.href,
                h1: document.querySelector('h1')?.textContent?.trim() || '',
                linkCount: document.links.length,
                imgCount: document.images.length,
                bodyText: document.body?.innerText?.substring(0, 500) || ''
            };
        }
    """)
    
    # Get potential containers
    containers = await page.evaluate("""
        () => {
            const candidates = [];
            const seen = new Set();
            
            document.querySelectorAll('*').forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    const cls = el.className.split(' ')[0];
                    if (cls && !seen.has(cls)) {
                        seen.add(cls);
                        const count = document.querySelectorAll('.' + cls).length;
                        if (count >= 3 && count <= 50) {
                            const sample = el.textContent?.trim().substring(0, 100) || '';
                            candidates.push({ selector: '.' + cls, count, sample });
                        }
                    }
                }
            });
            
            return candidates.sort((a, b) => b.count - a.count).slice(0, 10);
        }
    """)
    
    # Include discovered patterns in prompt
    patterns_info = ""
    if discovered_patterns:
        dp = discovered_patterns.get('discovered_patterns', {})
        if dp.get('links'):
            patterns_info += f"\nDISCOVERED URL PATTERNS: {dp['links'][:4]}"
        if dp.get('price_classes'):
            patterns_info += f"\nDISCOVERED PRICE CLASSES: {dp['price_classes'][:3]}"
    
    prompt = f"""Create a complete extraction strategy for this page.

USER INSTRUCTION: "{instruction}"

PAGE INFO:
- Title: {overview.get('title', '')}
- URL: {overview.get('url', '')}
- H1: {overview.get('h1', '')}
{patterns_info}

POTENTIAL CONTAINERS:
"""
    for c in containers[:8]:
        prompt += f"  {c['selector']} ({c['count']}x): \"{c['sample'][:60]}\"\n"
    
    prompt += """
Create a strategy to extract products. Include:
1. Container selector (which elements hold products)
2. Field selectors (name, price, url, image - relative to container)
3. Any filters based on the instruction

Output JSON:
{
    "container_selector": ".product-item",
    "fields": {
        "name": {"selector": "a.title, h2, .name", "type": "text"},
        "price": {"selector": ".price, span[class*=price]", "type": "text"},
        "url": {"selector": "a", "type": "attribute:href"},
        "image": {"selector": "img", "type": "attribute:src"}
    },
    "filters": {
        "price_max": number_or_null,
        "price_min": number_or_null
    },
    "confidence": 0.0-1.0,
    "reasoning": "explanation"
}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        if result:
            if run_logger:
                run_logger.log_text(f"✅ Generated extraction strategy")
                run_logger.log_code("json", json.dumps(result, indent=2))
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ Strategy generation failed: {e}")
    
    return {"container_selector": None, "fields": {}, "confidence": 0}


async def validate_selector(
    page,
    llm,
    selector: str,
    expected_type: str = "products",
    run_logger=None
) -> Dict[str, Any]:
    """
    LLM validates if a selector actually matches the expected content type.
    
    Returns:
        {
            "is_valid": bool,
            "matches_count": int,
            "actual_type": str,
            "reasoning": str
        }
    """
    # Get what the selector matches
    matches = await page.evaluate("""
        (selector) => {
            const elements = document.querySelectorAll(selector);
            if (elements.length === 0) return { count: 0, samples: [] };
            
            const samples = [];
            for (let i = 0; i < Math.min(elements.length, 3); i++) {
                const el = elements[i];
                samples.push({
                    text: el.textContent?.trim().substring(0, 150) || '',
                    hasImage: el.querySelector('img') !== null,
                    hasLink: el.querySelector('a') !== null
                });
            }
            
            return { count: elements.length, samples };
        }
    """, selector)
    
    prompt = f"""Validate if this CSS selector matches {expected_type}.

Selector: {selector}
Matches: {matches.get('count', 0)} elements

Sample content:
"""
    for i, sample in enumerate(matches.get('samples', [])):
        prompt += f"""
Sample {i+1}:
  Text: "{sample.get('text', '')[:100]}"
  Has image: {sample.get('hasImage')}
  Has link: {sample.get('hasLink')}
"""
    
    prompt += f"""
Does this selector match {expected_type}?
Consider:
- Do the matched elements contain actual {expected_type}?
- Or is it navigation/menu/footer/other?

Output JSON:
{{"is_valid": true/false, "actual_type": "products|navigation|articles|other", "reasoning": "explanation"}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        if result:
            result["matches_count"] = matches.get("count", 0)
            return result
    except Exception:
        pass
    
    return {"is_valid": False, "matches_count": matches.get("count", 0)}


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
    # Try multiple patterns
    patterns = [
        r'\{[^{}]*\}',
        r'\{.*?\}'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    
    return None
