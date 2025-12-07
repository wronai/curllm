"""
Selector Generator - Build Optimal CSS Selectors

Generate minimal, stable selectors for DOM elements.
No LLM - pure algorithmic selector construction.
"""

from typing import Dict, List, Any, Optional


class SelectorGenerator:
    """
    Generate CSS selectors for elements.
    
    Strategies:
    1. Class-based (most stable)
    2. ID-based (unique but may be dynamic)
    3. Structural (tag + position)
    4. Attribute-based (data-*, aria-*)
    """
    
    @staticmethod
    async def generate_for_element(page, element_description: Dict) -> List[str]:
        """
        Generate multiple selector candidates for a described element.
        
        Args:
            page: Playwright page
            element_description: {tag, classes, text_contains, near_text, etc.}
        
        Returns:
            List of selector strings, ordered by specificity/stability
        """
        return await page.evaluate("""
            (desc) => {
                const selectors = [];
                
                // Find elements matching description
                let candidates = Array.from(document.querySelectorAll(desc.tag || '*'));
                
                // Filter by text content
                if (desc.text_contains) {
                    candidates = candidates.filter(el => 
                        (el.textContent || '').toLowerCase().includes(desc.text_contains.toLowerCase())
                    );
                }
                
                // Filter by class pattern
                if (desc.class_pattern) {
                    const pattern = new RegExp(desc.class_pattern, 'i');
                    candidates = candidates.filter(el => 
                        typeof el.className === 'string' && pattern.test(el.className)
                    );
                }
                
                // Generate selectors for first matching element
                const el = candidates[0];
                if (!el) return [];
                
                // Strategy 1: ID (if present and not dynamic-looking)
                if (el.id && !/^\\d|_\\d{4,}|[a-f0-9]{8,}/.test(el.id)) {
                    selectors.push('#' + el.id);
                }
                
                // Strategy 2: Classes (filter dynamic/utility classes)
                if (el.className && typeof el.className === 'string') {
                    const classes = el.className.split(' ').filter(c => {
                        if (c.length < 2) return false;
                        if (/^\\d|_\\d{4,}|[a-f0-9]{8,}/.test(c)) return false;  // Dynamic
                        if (/^(mt|mb|ml|mr|mx|my|pt|pb|pl|pr|px|py|w-|h-|text-|bg-)/.test(c)) return false;  // Utility
                        return true;
                    });
                    
                    if (classes.length > 0) {
                        selectors.push(el.tagName.toLowerCase() + '.' + classes[0]);
                        if (classes.length > 1) {
                            selectors.push(el.tagName.toLowerCase() + '.' + classes.slice(0, 2).join('.'));
                        }
                    }
                }
                
                // Strategy 3: Data attributes
                for (const attr of el.attributes) {
                    if (attr.name.startsWith('data-') && !attr.name.includes('id')) {
                        selectors.push(`[${attr.name}="${attr.value}"]`);
                    }
                }
                
                // Strategy 4: nth-child (fallback)
                const parent = el.parentElement;
                if (parent) {
                    const siblings = Array.from(parent.children);
                    const index = siblings.indexOf(el);
                    if (index >= 0) {
                        const parentSelector = parent.className && typeof parent.className === 'string'
                            ? parent.tagName.toLowerCase() + '.' + parent.className.split(' ')[0]
                            : parent.tagName.toLowerCase();
                        selectors.push(`${parentSelector} > ${el.tagName.toLowerCase()}:nth-child(${index + 1})`);
                    }
                }
                
                return selectors;
            }
        """, element_description)
    
    @staticmethod
    async def find_stable_selector(page, selector: str) -> Dict[str, Any]:
        """
        Analyze selector stability and suggest improvements.
        
        Returns selector analysis with stability score and alternatives.
        """
        return await page.evaluate("""
            (selector) => {
                try {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length === 0) {
                        return { valid: false, reason: 'No elements match' };
                    }
                    
                    const el = elements[0];
                    
                    // Analyze stability factors
                    const factors = {
                        uses_id: selector.includes('#'),
                        uses_class: selector.includes('.'),
                        uses_nth: selector.includes('nth'),
                        uses_attribute: selector.includes('['),
                        specificity: (selector.match(/\\./g) || []).length + 
                                    (selector.match(/#/g) || []).length * 10 +
                                    (selector.match(/\\[/g) || []).length * 5
                    };
                    
                    // Check for dynamic patterns in selector
                    const dynamicPatterns = /\\d{4,}|[a-f0-9]{8,}|_\\d+/;
                    const hasDynamicParts = dynamicPatterns.test(selector);
                    
                    // Calculate stability score
                    let stability = 100;
                    if (hasDynamicParts) stability -= 50;
                    if (factors.uses_nth) stability -= 20;
                    if (!factors.uses_class && !factors.uses_id) stability -= 30;
                    
                    // Generate alternatives
                    const alternatives = [];
                    if (el.className && typeof el.className === 'string') {
                        const stableClasses = el.className.split(' ')
                            .filter(c => c.length > 2 && !dynamicPatterns.test(c) && /^[a-z]/i.test(c));
                        if (stableClasses.length > 0) {
                            alternatives.push(el.tagName.toLowerCase() + '.' + stableClasses[0]);
                        }
                    }
                    
                    return {
                        valid: true,
                        match_count: elements.length,
                        stability_score: stability,
                        factors: factors,
                        has_dynamic_parts: hasDynamicParts,
                        alternatives: alternatives
                    };
                } catch (e) {
                    return { valid: false, reason: e.message };
                }
            }
        """, selector)
    
    @staticmethod
    async def extract_field_selectors(page, container_selector: str) -> Dict[str, Any]:
        """
        Extract sub-selectors for common fields within a container.
        
        Returns selectors for: name, price, url, image, description
        """
        return await page.evaluate("""
            (containerSelector) => {
                const container = document.querySelector(containerSelector);
                if (!container) return { found: false };
                
                const fields = {};
                const pricePattern = /\\d+[\\s\\d]*[,.]\\d{2}\\s*(?:zł|PLN|€|\\$)/i;
                
                // Find NAME: Longest meaningful text in heading/link
                const nameElements = container.querySelectorAll('h1, h2, h3, h4, a, [class*="name"], [class*="title"]');
                let bestName = { el: null, text: '', score: 0 };
                
                for (const el of nameElements) {
                    const text = (el.textContent || '').trim();
                    if (text.length < 10 || text.length > 200) continue;
                    if (pricePattern.test(text)) continue;  // Skip price text
                    
                    const score = text.length + (el.tagName.match(/^H[1-4]$/) ? 50 : 0);
                    if (score > bestName.score) {
                        bestName = { el, text: text.slice(0, 100), score };
                    }
                }
                
                if (bestName.el) {
                    const cls = typeof bestName.el.className === 'string' 
                        ? bestName.el.className.split(' ').filter(c => c.length > 0)[0]
                        : null;
                    fields.name = {
                        selector: bestName.el.tagName.toLowerCase() + (cls ? '.' + cls : ''),
                        sample: bestName.text
                    };
                }
                
                // Find PRICE: Element with price pattern
                const allElements = container.querySelectorAll('*');
                for (const el of allElements) {
                    const text = (el.textContent || '').trim();
                    if (pricePattern.test(text) && text.length < 50) {
                        const cls = typeof el.className === 'string'
                            ? el.className.split(' ').filter(c => c.length > 0)[0]
                            : null;
                        fields.price = {
                            selector: el.tagName.toLowerCase() + (cls ? '.' + cls : ''),
                            sample: text
                        };
                        break;
                    }
                }
                
                // Find URL: First product-like link
                const links = container.querySelectorAll('a[href]');
                for (const link of links) {
                    if (link.href && link.href.length > 10) {
                        fields.url = {
                            selector: 'a[href]',
                            sample: link.href
                        };
                        break;
                    }
                }
                
                // Find IMAGE: First non-tiny image
                const images = container.querySelectorAll('img[src]');
                for (const img of images) {
                    if (img.width > 30 && img.height > 30) {
                        fields.image = {
                            selector: 'img',
                            sample: img.src.slice(0, 100)
                        };
                        break;
                    }
                }
                
                return {
                    found: Object.keys(fields).length > 0,
                    fields: fields,
                    completeness: Object.keys(fields).length / 4
                };
            }
        """, container_selector)
    
    @staticmethod
    async def test_selector(page, selector: str) -> Dict[str, Any]:
        """
        Test a selector and return match details.
        
        Useful for validating LLM-suggested selectors.
        """
        return await page.evaluate("""
            (selector) => {
                try {
                    const elements = document.querySelectorAll(selector);
                    const count = elements.length;
                    
                    if (count === 0) {
                        return { valid: true, matches: 0 };
                    }
                    
                    // Sample first few elements
                    const samples = Array.from(elements).slice(0, 3).map(el => ({
                        tag: el.tagName.toLowerCase(),
                        text_preview: (el.textContent || '').slice(0, 50),
                        has_link: !!el.querySelector('a[href]'),
                        has_image: !!el.querySelector('img')
                    }));
                    
                    return {
                        valid: true,
                        matches: count,
                        samples: samples
                    };
                } catch (e) {
                    return { valid: false, error: e.message };
                }
            }
        """, selector)
