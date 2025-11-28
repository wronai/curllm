"""
Container Finder - LLM-based product container detection.

NO REGEX - Uses LLM to identify product containers semantically.
"""
import json
from typing import Dict, Any, List, Optional


async def find_product_containers(
    page,
    llm,
    instruction: str = "",
    run_logger=None
) -> Dict[str, Any]:
    """
    Find product containers using LLM analysis.
    
    Returns:
        {
            "found": bool,
            "containers": [{"selector": str, "count": int, "confidence": float}],
            "best": {"selector": str, "reasoning": str}
        }
    """
    if run_logger:
        run_logger.log_text("🔍 LLM Container Detection")
    
    # Get DOM structure summary for LLM
    dom_summary = await page.evaluate("""
        () => {
            const candidates = [];
            
            // Find repeating structures (potential product lists)
            const classCounts = {};
            document.querySelectorAll('*').forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    const firstClass = el.className.split(' ')[0];
                    if (firstClass && firstClass.length > 2) {
                        if (!classCounts[firstClass]) {
                            classCounts[firstClass] = {
                                count: 0,
                                samples: []
                            };
                        }
                        classCounts[firstClass].count++;
                        
                        // Get sample content (first 3)
                        if (classCounts[firstClass].samples.length < 3) {
                            const text = el.textContent?.trim().substring(0, 100) || '';
                            const hasImage = el.querySelector('img') !== null;
                            const hasLink = el.querySelector('a') !== null;
                            
                            classCounts[firstClass].samples.push({
                                text: text,
                                hasImage,
                                hasLink,
                                tag: el.tagName.toLowerCase()
                            });
                        }
                    }
                }
            });
            
            // Filter to classes with 3+ elements (potential lists)
            for (const [className, data] of Object.entries(classCounts)) {
                if (data.count >= 3 && data.count <= 100) {
                    candidates.push({
                        selector: '.' + className,
                        count: data.count,
                        samples: data.samples
                    });
                }
            }
            
            // Sort by count (most frequent first)
            candidates.sort((a, b) => b.count - a.count);
            
            return candidates.slice(0, 15);
        }
    """)
    
    if not dom_summary:
        return {"found": False, "containers": [], "best": None}
    
    # Format for LLM
    candidates_text = ""
    for i, c in enumerate(dom_summary[:10]):
        samples = c.get('samples', [])
        sample_texts = [s.get('text', '')[:50] for s in samples]
        has_images = any(s.get('hasImage') for s in samples)
        has_links = any(s.get('hasLink') for s in samples)
        
        candidates_text += f"""
[{i}] Selector: {c['selector']}
    Count: {c['count']} elements
    Has images: {has_images}, Has links: {has_links}
    Sample content: {sample_texts[:2]}
"""
    
    prompt = f"""Find the CSS selector for product containers on this page.

User instruction: {instruction or 'Find products'}

Candidate containers found:
{candidates_text}

A good product container:
- Contains multiple similar items (products)
- Each item has: name/title, possibly price, possibly image
- NOT navigation menus, NOT headers/footers, NOT cart widgets

Which selector is the BEST product container?

Output JSON:
{{"found": true/false, "best_index": 0-9, "selector": ".class-name", "reasoning": "why this is the product container", "confidence": 0.0-1.0}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        
        if result and result.get('found'):
            best_idx = result.get('best_index', 0)
            if 0 <= best_idx < len(dom_summary):
                best = dom_summary[best_idx]
                best['reasoning'] = result.get('reasoning', '')
                best['confidence'] = result.get('confidence', 0.5)
                
                if run_logger:
                    run_logger.log_text(f"✅ Found container: {best['selector']} ({best['count']} items)")
                
                return {
                    "found": True,
                    "containers": dom_summary,
                    "best": best
                }
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ LLM container detection failed: {e}")
    
    return {"found": False, "containers": dom_summary, "best": None}


async def analyze_container_content(
    page,
    llm,
    container_selector: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Analyze what's inside a container using LLM.
    
    Returns:
        {
            "is_product_container": bool,
            "content_type": "products" | "navigation" | "articles" | "other",
            "has_prices": bool,
            "has_names": bool,
            "reasoning": str
        }
    """
    # Get container content
    content = await page.evaluate(f"""
        (selector) => {{
            const containers = document.querySelectorAll(selector);
            if (containers.length === 0) return null;
            
            const samples = [];
            for (let i = 0; i < Math.min(containers.length, 5); i++) {{
                const el = containers[i];
                samples.push({{
                    text: el.textContent?.trim().substring(0, 200) || '',
                    html: el.innerHTML?.substring(0, 300) || '',
                    hasImg: el.querySelector('img') !== null,
                    hasLink: el.querySelector('a') !== null,
                    linkCount: el.querySelectorAll('a').length
                }});
            }}
            
            return {{
                count: containers.length,
                samples
            }};
        }}
    """, container_selector)
    
    if not content:
        return {"is_product_container": False, "content_type": "unknown"}
    
    prompt = f"""Analyze these container elements. Are they product containers?

Container: {container_selector}
Count: {content.get('count', 0)}

Sample contents:
"""
    
    for i, sample in enumerate(content.get('samples', [])[:3]):
        prompt += f"""
Sample {i+1}:
Text: {sample.get('text', '')[:150]}
Has image: {sample.get('hasImg')}
Link count: {sample.get('linkCount')}
"""
    
    prompt += """
Determine:
1. Is this a PRODUCT container (items for sale)?
2. Or is it: navigation, articles, cart, footer, or other?
3. Does it contain prices?
4. Does it contain product names?

Output JSON:
{"is_product_container": true/false, "content_type": "products|navigation|articles|cart|other", "has_prices": true/false, "has_names": true/false, "reasoning": "brief explanation"}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        if result:
            return result
    except Exception:
        pass
    
    return {"is_product_container": False, "content_type": "unknown"}


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
