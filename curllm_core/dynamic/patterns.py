"""
Dynamic Pattern Detection - Detect patterns without hardcoded regexes

Uses statistics and LLM to find patterns dynamically.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectedPattern:
    """A detected pattern on the page"""
    pattern_type: str
    selector: Optional[str]
    sample_values: List[str]
    confidence: float
    count: int


async def detect_price_pattern(page, llm=None) -> Optional[DetectedPattern]:
    """
    Detect price pattern on page dynamically.
    
    Instead of hardcoded regex like r'\\d+[,.]\\d{2}\\s*zł',
    uses statistics to find price-like patterns.
    
    Args:
        page: Playwright page
        llm: Optional LLM
        
    Returns:
        Detected price pattern
    """
    # Get all text nodes with potential prices
    candidates = await page.evaluate("""() => {
        const candidates = [];
        
        // Common currency indicators
        const currencies = ['zł', 'PLN', '€', 'EUR', '$', 'USD', '£', 'GBP'];
        
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        while (walker.nextNode()) {
            const text = walker.currentNode.textContent.trim();
            
            // Check if contains number and potentially currency
            if (/\\d/.test(text) && text.length < 50) {
                const hasCurrency = currencies.some(c => text.includes(c));
                const hasPrice = /\\d+[.,]\\d{2}/.test(text);
                
                if (hasCurrency || hasPrice) {
                    const parent = walker.currentNode.parentElement;
                    candidates.push({
                        text: text,
                        tagName: parent?.tagName?.toLowerCase(),
                        className: parent?.className,
                    });
                }
            }
        }
        
        return candidates.slice(0, 100);
    }""")
    
    if not candidates:
        return None
    
    # Analyze patterns statistically
    prices = []
    for c in candidates:
        # Extract price-like values
        matches = re.findall(r'(\d+[\s\u00a0]*\d*[,.\s]\d{2})', c['text'])
        prices.extend(matches)
    
    if len(prices) >= 3:
        return DetectedPattern(
            pattern_type='price',
            selector=None,  # No hardcoded selector
            sample_values=prices[:5],
            confidence=min(len(prices) / 10, 0.9),
            count=len(prices),
        )
    
    return None


async def detect_product_container(page, llm=None) -> Optional[DetectedPattern]:
    """
    Detect product container pattern dynamically.
    
    Uses DOM statistics to find repeating product-like structures.
    
    Args:
        page: Playwright page
        llm: Optional LLM
        
    Returns:
        Detected container pattern
    """
    from curllm_core.detection import DynamicPatternDetector
    
    # Use existing dynamic detector
    detector = DynamicPatternDetector()
    
    # Get page DOM
    html = await page.content()
    
    # Find repeating patterns
    result = await detector.find_repeating_containers(html)
    
    if result and result.get('count', 0) >= 3:
        return DetectedPattern(
            pattern_type='product_container',
            selector=result.get('selector'),
            sample_values=[],
            confidence=result.get('confidence', 0.7),
            count=result.get('count', 0),
        )
    
    return None


async def detect_list_pattern(page, content_type: str = None, llm=None) -> Optional[DetectedPattern]:
    """
    Detect list/repeating pattern on page.
    
    Args:
        page: Playwright page
        content_type: Hint about content (e.g., "products", "articles")
        llm: Optional LLM
        
    Returns:
        Detected list pattern
    """
    # Analyze DOM for repeating structures
    patterns = await page.evaluate("""() => {
        const patterns = {};
        
        // Find elements with multiple similar children
        const containers = document.querySelectorAll('ul, ol, div, section, article');
        
        for (const container of containers) {
            const children = Array.from(container.children);
            if (children.length < 3) continue;
            
            // Check if children are similar
            const tags = children.map(c => c.tagName);
            const uniqueTags = [...new Set(tags)];
            
            if (uniqueTags.length === 1) {
                // All children have same tag
                const key = `${container.tagName}>${uniqueTags[0]}`;
                patterns[key] = (patterns[key] || 0) + children.length;
            }
        }
        
        return patterns;
    }""")
    
    # Find most common pattern
    if patterns:
        best_pattern = max(patterns.items(), key=lambda x: x[1])
        if best_pattern[1] >= 3:
            return DetectedPattern(
                pattern_type='list',
                selector=best_pattern[0],
                sample_values=[],
                confidence=min(best_pattern[1] / 20, 0.9),
                count=best_pattern[1],
            )
    
    return None


async def detect_pagination(page, llm=None) -> Optional[DetectedPattern]:
    """
    Detect pagination pattern on page.
    
    Args:
        page: Playwright page
        llm: Optional LLM
        
    Returns:
        Detected pagination pattern
    """
    pagination = await page.evaluate("""() => {
        // Look for pagination indicators
        const keywords = ['page', 'strona', 'next', 'następna', 'prev', 'poprzednia', '»', '«'];
        
        const elements = document.querySelectorAll('nav, .pagination, [class*="pager"], [role="navigation"]');
        
        for (const el of elements) {
            const text = el.textContent.toLowerCase();
            const hasKeyword = keywords.some(kw => text.includes(kw));
            const hasNumbers = /\\d+.*\\d+/.test(text);
            
            if (hasKeyword || hasNumbers) {
                // Found pagination
                const links = el.querySelectorAll('a');
                return {
                    found: true,
                    linkCount: links.length,
                    text: text.substring(0, 100),
                };
            }
        }
        
        // Check for numbered links
        const numberedLinks = document.querySelectorAll('a');
        let count = 0;
        for (const link of numberedLinks) {
            if (/^\\d+$/.test(link.textContent.trim())) {
                count++;
            }
        }
        
        if (count >= 3) {
            return {
                found: true,
                linkCount: count,
                text: 'numbered links',
            };
        }
        
        return { found: false };
    }""")
    
    if pagination and pagination.get('found'):
        return DetectedPattern(
            pattern_type='pagination',
            selector=None,
            sample_values=[],
            confidence=0.8,
            count=pagination.get('linkCount', 0),
        )
    
    return None
