"""
DOM Structure Analyzer - Pure JavaScript Analysis

Provides atomic queries for DOM structure without LLM.
Each method returns a focused, small result set.
"""

from typing import Dict, List, Any, Optional


class DOMStructureAnalyzer:
    """
    Atomic DOM structure analysis.
    
    All methods are async and run JavaScript in the browser.
    Returns minimal, focused data - no large DOM dumps.
    """
    
    # =========================================================================
    # ATOMIC QUERIES - Each returns focused data
    # =========================================================================
    
    @staticmethod
    async def get_depth_distribution(page) -> Dict[str, Any]:
        """
        Get element count at each DOM depth level.
        
        Use case: Find optimal depth for container detection.
        Returns: {depth: count} mapping + statistics
        """
        return await page.evaluate("""
            () => {
                const depthCounts = {};
                const walk = (node, depth) => {
                    if (node.nodeType !== Node.ELEMENT_NODE) return;
                    depthCounts[depth] = (depthCounts[depth] || 0) + 1;
                    for (const child of node.children) {
                        walk(child, depth + 1);
                    }
                };
                walk(document.body, 0);
                
                const depths = Object.keys(depthCounts).map(Number).sort((a,b) => a-b);
                const counts = depths.map(d => depthCounts[d]);
                const maxCount = Math.max(...counts);
                const peakDepth = depths[counts.indexOf(maxCount)];
                
                return {
                    distribution: depthCounts,
                    peak_depth: peakDepth,
                    max_count: maxCount,
                    total_elements: counts.reduce((a,b) => a+b, 0)
                };
            }
        """)
    
    @staticmethod
    async def get_repeating_structures(page, min_count: int = 5) -> List[Dict]:
        """
        Find DOM structures that repeat (potential lists/grids).
        
        Use case: Identify product containers, article lists, etc.
        Returns: List of repeating class patterns with counts
        """
        return await page.evaluate("""
            (minCount) => {
                const classPatterns = {};
                
                for (const el of document.querySelectorAll('*')) {
                    if (!el.className || typeof el.className !== 'string') continue;
                    
                    const classes = el.className.split(' ').filter(c => 
                        c.length > 0 && /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(c)
                    );
                    if (classes.length === 0) continue;
                    
                    // Use tag + first class as pattern key
                    const pattern = el.tagName.toLowerCase() + '.' + classes[0];
                    
                    if (!classPatterns[pattern]) {
                        classPatterns[pattern] = {
                            selector: pattern,
                            count: 0,
                            sample_classes: classes.slice(0, 3),
                            has_links: false,
                            has_images: false,
                            avg_text_length: 0,
                            depths: []
                        };
                    }
                    
                    const p = classPatterns[pattern];
                    p.count++;
                    p.has_links = p.has_links || !!el.querySelector('a[href]');
                    p.has_images = p.has_images || !!el.querySelector('img');
                    p.avg_text_length = (p.avg_text_length * (p.count - 1) + (el.textContent?.length || 0)) / p.count;
                    
                    // Track depth distribution
                    let depth = 0, current = el;
                    while (current && current !== document.body) {
                        depth++; current = current.parentElement;
                    }
                    if (!p.depths.includes(depth)) p.depths.push(depth);
                }
                
                return Object.values(classPatterns)
                    .filter(p => p.count >= minCount)
                    .sort((a, b) => b.count - a.count)
                    .slice(0, 50);
            }
        """, min_count)
    
    @staticmethod
    async def get_elements_at_depth(page, depth: int, limit: int = 100) -> List[Dict]:
        """
        Get elements at specific DOM depth.
        
        Use case: Analyze containers at optimal depth.
        Returns: List of element info (tag, classes, children count)
        """
        return await page.evaluate("""
            (args) => {
                const targetDepth = args.depth;
                const limit = args.limit;
                const results = [];
                
                const walk = (node, currentDepth) => {
                    if (node.nodeType !== Node.ELEMENT_NODE) return;
                    if (results.length >= limit) return;
                    
                    if (currentDepth === targetDepth) {
                        const classes = typeof node.className === 'string' 
                            ? node.className.split(' ').filter(c => c.length > 0).slice(0, 3)
                            : [];
                        results.push({
                            tag: node.tagName.toLowerCase(),
                            classes: classes,
                            children_count: node.children.length,
                            text_length: (node.textContent || '').length,
                            has_link: !!node.querySelector('a[href]'),
                            has_image: !!node.querySelector('img')
                        });
                    } else if (currentDepth < targetDepth) {
                        for (const child of node.children) {
                            walk(child, currentDepth + 1);
                        }
                    }
                };
                
                walk(document.body, 0);
                return results;
            }
        """, {"depth": depth, "limit": limit})
    
    @staticmethod
    async def get_parent_chain(page, selector: str, max_depth: int = 5) -> List[Dict]:
        """
        Get parent chain for elements matching selector.
        
        Use case: Understand container hierarchy.
        Returns: Parent elements from selector up to max_depth
        """
        return await page.evaluate("""
            (args) => {
                const el = document.querySelector(args.selector);
                if (!el) return [];
                
                const chain = [];
                let current = el;
                let depth = 0;
                
                while (current && current !== document.body && depth < args.maxDepth) {
                    const classes = typeof current.className === 'string'
                        ? current.className.split(' ').filter(c => c.length > 0).slice(0, 3)
                        : [];
                    chain.push({
                        tag: current.tagName.toLowerCase(),
                        classes: classes,
                        children_count: current.children.length,
                        siblings_count: current.parentElement?.children.length || 0
                    });
                    current = current.parentElement;
                    depth++;
                }
                
                return chain;
            }
        """, {"selector": selector, "maxDepth": max_depth})
    
    @staticmethod
    async def count_elements_by_tag(page) -> Dict[str, int]:
        """
        Count elements by HTML tag.
        
        Use case: Quick page structure overview.
        Returns: {tag: count} mapping
        """
        return await page.evaluate("""
            () => {
                const counts = {};
                for (const el of document.querySelectorAll('*')) {
                    const tag = el.tagName.toLowerCase();
                    counts[tag] = (counts[tag] || 0) + 1;
                }
                return counts;
            }
        """)
    
    # =========================================================================
    # HELPER: Get minimal page snapshot (for orchestrator context)
    # =========================================================================
    
    @staticmethod
    async def get_page_summary(page) -> Dict[str, Any]:
        """
        Get minimal page summary for LLM orchestration.
        
        Use case: Give LLM just enough context to decide extraction strategy.
        Returns: Focused summary (< 500 chars) - NOT full DOM
        """
        return await page.evaluate("""
            () => {
                const title = document.title || '';
                const h1 = document.querySelector('h1')?.textContent?.trim() || '';
                const h2s = Array.from(document.querySelectorAll('h2'))
                    .slice(0, 3)
                    .map(h => h.textContent?.trim())
                    .filter(t => t && t.length < 100);
                
                // Count key indicators
                const links = document.links.length;
                const images = document.images.length;
                const forms = document.forms.length;
                const tables = document.querySelectorAll('table').length;
                const lists = document.querySelectorAll('ul, ol').length;
                
                // Detect page type indicators
                const hasCart = !!/koszyk|cart|checkout/i.test(document.body.textContent || '');
                const hasProducts = !!/produkt|product|cena|price|zł|PLN/i.test(document.body.textContent || '');
                const hasLogin = !!/login|zaloguj|sign.?in/i.test(document.body.textContent || '');
                
                return {
                    title: title.slice(0, 100),
                    h1: h1.slice(0, 100),
                    h2s: h2s,
                    counts: { links, images, forms, tables, lists },
                    indicators: { hasCart, hasProducts, hasLogin },
                    url: window.location.href
                };
            }
        """)
