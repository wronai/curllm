"""
Page Analyzer - LLM-based page type detection.

NO REGEX - Uses LLM to understand page structure semantically.
"""
import json
from typing import Dict, Any, Optional


async def analyze_page_type(
    page,
    llm,
    run_logger=None
) -> Dict[str, Any]:
    """
    Analyze page type using LLM instead of regex patterns.
    
    Returns:
        {
            "page_type": "product_listing" | "single_product" | "category" | "homepage" | "other",
            "has_products": bool,
            "confidence": float,
            "reasoning": str
        }
    """
    if run_logger:
        run_logger.log_text("🔍 LLM Page Analysis")
    
    # Get page summary for LLM
    page_summary = await page.evaluate("""
        () => {
            const title = document.title || '';
            const h1 = document.querySelector('h1')?.textContent?.trim() || '';
            const url = window.location.href;
            const linkCount = document.links.length;
            const imgCount = document.images.length;
            
            // Get sample of visible text (first 500 chars)
            const bodyText = document.body?.innerText?.substring(0, 500) || '';
            
            // Count elements that might be products
            const potentialProducts = document.querySelectorAll('[class*="product"], [class*="item"], [class*="card"]').length;
            
            // Check for price indicators
            const priceElements = document.querySelectorAll('[class*="price"], [class*="cena"]').length;
            
            // Check for add-to-cart elements
            const cartButtons = document.querySelectorAll('[class*="cart"], [class*="koszyk"], button[type="submit"]').length;
            
            return {
                title,
                h1,
                url,
                linkCount,
                imgCount,
                potentialProducts,
                priceElements,
                cartButtons,
                bodyTextSample: bodyText
            };
        }
    """)
    
    # Ask LLM to analyze
    prompt = f"""Analyze this webpage and determine its type.

Page Info:
- Title: {page_summary.get('title', '')}
- H1: {page_summary.get('h1', '')}
- URL: {page_summary.get('url', '')}
- Links: {page_summary.get('linkCount', 0)}
- Images: {page_summary.get('imgCount', 0)}
- Potential products: {page_summary.get('potentialProducts', 0)}
- Price elements: {page_summary.get('priceElements', 0)}
- Cart buttons: {page_summary.get('cartButtons', 0)}

Body text sample:
{page_summary.get('bodyTextSample', '')[:300]}

Determine:
1. Is this a product listing page (multiple products)?
2. Is this a single product page?
3. Is this a category/navigation page?
4. Is this a homepage?
5. Are there products visible that can be extracted?

Output JSON:
{{"page_type": "product_listing|single_product|category|homepage|other", "has_products": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation"}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        
        if result:
            if run_logger:
                run_logger.log_text(f"✅ Page type: {result.get('page_type')} (confidence: {result.get('confidence', 0):.2f})")
            return result
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"⚠️ LLM analysis failed: {e}")
    
    # Fallback
    return {
        "page_type": "unknown",
        "has_products": False,
        "confidence": 0.0,
        "reasoning": "LLM analysis failed"
    }


async def detect_price_format(
    page,
    llm,
    run_logger=None
) -> Dict[str, Any]:
    """
    Detect how prices are displayed on the page using LLM.
    
    Returns:
        {
            "format": "text" | "image" | "mixed",
            "currency": "PLN" | "EUR" | "USD" | etc,
            "sample": str
        }
    """
    # Get price-related elements
    price_info = await page.evaluate("""
        () => {
            const results = {
                textPrices: [],
                imagePrices: [],
                priceLabels: []
            };
            
            // Find text that looks like prices
            const walker = document.createTreeWalker(
                document.body,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            let node;
            let count = 0;
            while ((node = walker.nextNode()) && count < 20) {
                const text = node.textContent.trim();
                if (text.length > 3 && text.length < 30) {
                    // Check if contains currency-like patterns
                    if (/zł|PLN|€|\\$|USD|EUR/i.test(text) || /\\d+[,.]\\d{2}/.test(text)) {
                        results.textPrices.push(text);
                        count++;
                    }
                }
            }
            
            // Find price images
            const priceImgs = document.querySelectorAll('img[src*="price"], img[src*="cena"], img[src*="cb_"], img[src*="cn_"]');
            for (let i = 0; i < Math.min(priceImgs.length, 5); i++) {
                results.imagePrices.push(priceImgs[i].src);
            }
            
            // Find price labels
            const labels = document.querySelectorAll('*');
            for (const el of labels) {
                const text = el.textContent?.trim() || '';
                if (/cena|price/i.test(text) && text.length < 30) {
                    results.priceLabels.push(text);
                    if (results.priceLabels.length >= 5) break;
                }
            }
            
            return results;
        }
    """)
    
    prompt = f"""Analyze how prices are displayed on this page.

Found text prices: {price_info.get('textPrices', [])[:5]}
Found price images: {len(price_info.get('imagePrices', []))} images with price-like URLs
Price labels found: {price_info.get('priceLabels', [])[:5]}

Determine:
1. Are prices shown as TEXT or IMAGES?
2. What currency is used?
3. Give an example of the price format

Output JSON:
{{"format": "text|image|mixed", "currency": "PLN|EUR|USD|other", "sample": "example price"}}

JSON:"""

    try:
        response = await _llm_generate(llm, prompt)
        result = _parse_json_response(response)
        if result:
            return result
    except Exception:
        pass
    
    return {"format": "unknown", "currency": "unknown", "sample": ""}


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
    # Try to find JSON in response
    patterns = [
        r'\{[^{}]*\}',  # Simple JSON
        r'\{.*?\}',     # Greedy
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    
    return None
