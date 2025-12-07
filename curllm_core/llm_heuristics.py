"""
LLM-Assisted Heuristics Discovery

Dynamically discovers URL patterns, element patterns, and other heuristics
by analyzing the page structure with LLM assistance.
"""

import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class DiscoveredHeuristics:
    """Container for discovered heuristics"""
    product_link_patterns: List[str] = field(default_factory=list)
    price_patterns: List[str] = field(default_factory=list)
    container_patterns: List[str] = field(default_factory=list)
    image_patterns: List[str] = field(default_factory=list)
    confidence: float = 0.0
    source: str = "default"


# Default fallback patterns (used when LLM unavailable)
DEFAULT_PRODUCT_LINK_PATTERNS = [
    'a[href*="product"]',
    'a[href*="produkt"]', 
    'a[href*="item"]',
    'a[href*="/p/"]',
    'a[href*=".html"]',
    'a[href*="/i/"]',
    'a[href*="towar"]',
]

DEFAULT_PRICE_IMAGE_PATTERNS = [
    'img[src*="cb_"]',
    'img[src*="cena"]',
    'img[src*="price"]',
]


class LLMHeuristicsDiscovery:
    """
    Discovers site-specific heuristics using LLM analysis of page structure
    """
    
    def __init__(self, page, llm=None, run_logger=None):
        self.page = page
        self.llm = llm
        self.run_logger = run_logger
        self._cache: Dict[str, DiscoveredHeuristics] = {}
    
    def _log(self, title: str, data: Any):
        """Log discovery progress"""
        if self.run_logger:
            if isinstance(data, dict):
                self.run_logger.log_json(f"🔍 Heuristics: {title}", data)
            else:
                self.run_logger.log_text(f"🔍 Heuristics: {title} - {data}")
    
    async def discover_product_link_patterns(self) -> List[str]:
        """
        Analyze page URLs and ask LLM which patterns indicate product links
        """
        # Step 1: Extract unique URL patterns from page
        url_analysis = await self.page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href]'));
                const patterns = {};
                const samples = {};
                
                for (const link of links.slice(0, 200)) {
                    const href = link.href || '';
                    const text = (link.innerText || '').trim().substring(0, 50);
                    
                    // Skip empty, hash, or javascript links
                    if (!href || href.startsWith('#') || href.startsWith('javascript:')) continue;
                    
                    // Extract path patterns
                    try {
                        const url = new URL(href);
                        const path = url.pathname;
                        
                        // Find pattern markers in URL
                        const markers = [];
                        
                        // Check for common product indicators
                        if (/\/p\//.test(path)) markers.push('/p/');
                        if (/\/product/.test(path)) markers.push('/product');
                        if (/\/produkt/.test(path)) markers.push('/produkt');
                        if (/\/item/.test(path)) markers.push('/item');
                        if (/\/towar/.test(path)) markers.push('/towar');
                        if (/\/i\//.test(path)) markers.push('/i/');
                        if (/\\.html$/.test(path)) markers.push('.html');
                        if (/\\.htm$/.test(path)) markers.push('.htm');
                        if (/\/\\d{4,}/.test(path)) markers.push('/ID (numeric)');
                        if (/_\\d{4,}/.test(path)) markers.push('_ID (numeric)');
                        
                        // Also check query params
                        if (url.searchParams.has('product')) markers.push('?product=');
                        if (url.searchParams.has('id')) markers.push('?id=');
                        if (url.searchParams.has('pid')) markers.push('?pid=');
                        
                        for (const marker of markers) {
                            patterns[marker] = (patterns[marker] || 0) + 1;
                            if (!samples[marker]) {
                                samples[marker] = { href: href.substring(0, 100), text };
                            }
                        }
                    } catch (e) {}
                }
                
                // Return sorted by frequency
                return Object.entries(patterns)
                    .map(([pattern, count]) => ({ 
                        pattern, 
                        count, 
                        sample: samples[pattern] 
                    }))
                    .sort((a, b) => b.count - a.count)
                    .slice(0, 10);
            }
        """)
        
        if not url_analysis:
            self._log("No URL patterns found, using defaults", {})
            return DEFAULT_PRODUCT_LINK_PATTERNS
        
        self._log("URL patterns discovered", {
            "patterns": [p["pattern"] for p in url_analysis[:5]],
            "counts": {p["pattern"]: p["count"] for p in url_analysis[:5]}
        })
        
        # Step 2: Ask LLM to identify product link patterns
        if self.llm:
            try:
                patterns_text = "\n".join([
                    f"- {p['pattern']}: {p['count']} links, sample: {p['sample']['text'][:30]}..."
                    for p in url_analysis[:8]
                ])
                
                prompt = f"""Analyze these URL patterns found on an e-commerce page.
Which patterns indicate PRODUCT links (not categories, navigation, etc)?

Patterns found:
{patterns_text}

Return JSON: {{"product_patterns": ["pattern1", "pattern2"], "reasoning": "why"}}

Rules:
- Include patterns that likely lead to product detail pages
- Patterns with numeric IDs often indicate products
- .html/.htm extensions often indicate product pages
- /p/, /product/, /item/ are common product URL patterns"""

                response = await self.llm.ainvoke(prompt)
                content = response.content if hasattr(response, 'content') else str(response)
                
                # Parse JSON from response
                json_match = re.search(r'\{[^{}]*"product_patterns"[^{}]*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    llm_patterns = result.get("product_patterns", [])
                    
                    if llm_patterns:
                        # Convert LLM patterns to CSS selectors
                        css_selectors = []
                        for p in llm_patterns:
                            if p == '.html':
                                css_selectors.append('a[href$=".html"]')
                            elif p == '.htm':
                                css_selectors.append('a[href$=".htm"]')
                            elif p.startswith('/') or p.startswith('?'):
                                css_selectors.append(f'a[href*="{p}"]')
                            elif 'ID' in p or 'numeric' in p.lower():
                                # Can't do regex in CSS, skip these
                                pass
                            else:
                                css_selectors.append(f'a[href*="{p}"]')
                        
                        self._log("LLM identified product patterns", {
                            "patterns": css_selectors,
                            "reasoning": result.get("reasoning", "")
                        })
                        
                        if css_selectors:
                            return css_selectors
                            
            except Exception as e:
                self._log("LLM pattern analysis failed", str(e))
        
        # Fallback: Use discovered patterns with high frequency
        fallback_selectors = []
        for p in url_analysis[:5]:
            pattern = p["pattern"]
            if pattern == '.html':
                fallback_selectors.append('a[href$=".html"]')
            elif pattern.startswith('/') or pattern.startswith('?'):
                fallback_selectors.append(f'a[href*="{pattern}"]')
        
        return fallback_selectors if fallback_selectors else DEFAULT_PRODUCT_LINK_PATTERNS
    
    async def discover_price_patterns(self) -> Dict[str, Any]:
        """
        Analyze page to find price display patterns (text and images)
        """
        price_analysis = await self.page.evaluate("""
            () => {
                const results = {
                    text_patterns: [],
                    image_patterns: [],
                    container_classes: []
                };
                
                // Find text-based prices
                const priceRegex = /\\d+[\\d\\s]*[,.]?\\d*\\s*(?:zł|PLN|€|\\$|USD|EUR|грн|руб)/gi;
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                
                const priceElements = new Set();
                let node;
                while (node = walker.nextNode()) {
                    if (priceRegex.test(node.textContent)) {
                        const parent = node.parentElement;
                        if (parent) {
                            const cls = parent.className?.split(' ')[0];
                            if (cls && /price|cena|cost|kwota/i.test(cls)) {
                                priceElements.add(cls);
                            }
                        }
                    }
                }
                
                results.container_classes = Array.from(priceElements).slice(0, 5);
                
                // Find price images (common in Polish e-commerce)
                const images = document.querySelectorAll('img');
                const priceImagePatterns = new Set();
                
                for (const img of images) {
                    const src = img.src || '';
                    // Common price image patterns
                    if (/cb_|cena|price|_c\\d|_p\\d/i.test(src)) {
                        // Extract pattern
                        const match = src.match(/(cb_|cena|price|_c\\d|_p\\d)/i);
                        if (match) priceImagePatterns.add(match[1].toLowerCase());
                    }
                }
                
                results.image_patterns = Array.from(priceImagePatterns);
                
                return results;
            }
        """)
        
        self._log("Price patterns discovered", price_analysis)
        return price_analysis
    
    async def build_dynamic_selectors(self, instruction: str = "") -> Dict[str, str]:
        """
        Build optimized selectors based on page analysis and instruction
        
        Returns dict with:
        - product_link_selector: CSS selector for product links
        - price_selector: CSS selector for price elements
        - price_image_selector: CSS selector for price images
        """
        # Discover patterns
        link_patterns = await self.discover_product_link_patterns()
        price_info = await self.discover_price_patterns()
        
        # Build combined selector for product links
        if link_patterns:
            product_link_selector = ", ".join(link_patterns[:4])
        else:
            product_link_selector = ", ".join(DEFAULT_PRODUCT_LINK_PATTERNS[:4])
        
        # Build price image selector
        if price_info.get("image_patterns"):
            price_image_parts = [f'img[src*="{p}"]' for p in price_info["image_patterns"]]
            price_image_selector = ", ".join(price_image_parts)
        else:
            price_image_selector = ", ".join(DEFAULT_PRICE_IMAGE_PATTERNS)
        
        # Build price container selector
        if price_info.get("container_classes"):
            price_selector = ", ".join([f'.{c}' for c in price_info["container_classes"]])
        else:
            price_selector = '[class*="price"], [class*="cena"], [class*="cost"]'
        
        result = {
            "product_link_selector": product_link_selector,
            "price_selector": price_selector,
            "price_image_selector": price_image_selector,
            "discovered_patterns": {
                "links": link_patterns,
                "price_images": price_info.get("image_patterns", []),
                "price_classes": price_info.get("container_classes", [])
            }
        }
        
        self._log("Dynamic selectors built", result)
        return result


async def get_dynamic_heuristics(page, llm=None, run_logger=None) -> Dict[str, str]:
    """
    Convenience function to get dynamic heuristics for a page
    
    Usage:
        heuristics = await get_dynamic_heuristics(page, llm, logger)
        product_links = page.query_selector_all(heuristics["product_link_selector"])
    """
    discovery = LLMHeuristicsDiscovery(page, llm, run_logger)
    return await discovery.build_dynamic_selectors()


def build_product_link_js_check(patterns: List[str]) -> str:
    """
    Build JavaScript code for checking product links dynamically
    
    Returns JS code that can be used in page.evaluate()
    """
    if not patterns:
        patterns = DEFAULT_PRODUCT_LINK_PATTERNS
    
    # Convert CSS selectors to JS checks
    js_checks = []
    for p in patterns:
        # Extract the pattern from selector like a[href*="product"]
        match = re.search(r'\[href\*="([^"]+)"\]', p)
        if match:
            js_checks.append(f'href.includes("{match.group(1)}")')
        match = re.search(r'\[href\$="([^"]+)"\]', p)
        if match:
            js_checks.append(f'href.endsWith("{match.group(1)}")')
    
    if not js_checks:
        js_checks = ['href.includes("product")', 'href.includes(".html")']
    
    return " || ".join(js_checks)
