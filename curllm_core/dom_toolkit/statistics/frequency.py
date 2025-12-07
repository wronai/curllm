"""
Frequency Analyzer - Count and Analyze Element Patterns

Pure statistical analysis of DOM element frequencies.
No LLM - uses mathematical heuristics.
"""

from typing import Dict, List, Any


class FrequencyAnalyzer:
    """
    Analyze element frequencies and distributions.
    
    Helps identify:
    - Repeated containers (products, articles)
    - Common structural patterns
    - Optimal extraction targets
    """
    
    @staticmethod
    async def count_class_frequencies(page, min_count: int = 3) -> List[Dict]:
        """
        Count how often each CSS class appears.
        
        Returns sorted list of classes by frequency.
        """
        return await page.evaluate("""
            (minCount) => {
                const classCounts = {};
                
                for (const el of document.querySelectorAll('*')) {
                    if (!el.className || typeof el.className !== 'string') continue;
                    
                    for (const cls of el.className.split(' ')) {
                        if (cls.length < 2) continue;
                        if (!/^[a-zA-Z]/.test(cls)) continue;
                        
                        classCounts[cls] = (classCounts[cls] || 0) + 1;
                    }
                }
                
                return Object.entries(classCounts)
                    .filter(([_, count]) => count >= minCount)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 100)
                    .map(([cls, count]) => ({ class: cls, count }));
            }
        """, min_count)
    
    @staticmethod
    async def count_tag_class_combinations(page, min_count: int = 5) -> List[Dict]:
        """
        Count tag+class combinations (e.g., "div.product").
        
        More specific than class-only counting.
        """
        return await page.evaluate("""
            (minCount) => {
                const comboCounts = {};
                
                for (const el of document.querySelectorAll('*')) {
                    if (!el.className || typeof el.className !== 'string') continue;
                    
                    const firstClass = el.className.split(' ')
                        .find(c => c.length > 1 && /^[a-zA-Z]/.test(c));
                    
                    if (!firstClass) continue;
                    
                    const combo = el.tagName.toLowerCase() + '.' + firstClass;
                    comboCounts[combo] = (comboCounts[combo] || 0) + 1;
                }
                
                return Object.entries(comboCounts)
                    .filter(([_, count]) => count >= minCount)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 50)
                    .map(([selector, count]) => ({ selector, count }));
            }
        """, min_count)
    
    @staticmethod
    async def analyze_text_lengths(page, selector: str) -> Dict[str, Any]:
        """
        Analyze text length distribution for elements matching selector.
        
        Useful for identifying content vs. navigation elements.
        """
        return await page.evaluate("""
            (selector) => {
                const elements = document.querySelectorAll(selector);
                if (elements.length === 0) return { found: false };
                
                const lengths = Array.from(elements)
                    .map(el => (el.textContent || '').trim().length);
                
                lengths.sort((a, b) => a - b);
                
                const sum = lengths.reduce((a, b) => a + b, 0);
                const avg = sum / lengths.length;
                
                return {
                    found: true,
                    count: lengths.length,
                    min: lengths[0],
                    max: lengths[lengths.length - 1],
                    avg: Math.round(avg),
                    median: lengths[Math.floor(lengths.length / 2)],
                    std_dev: Math.round(Math.sqrt(
                        lengths.reduce((sum, l) => sum + Math.pow(l - avg, 2), 0) / lengths.length
                    ))
                };
            }
        """, selector)
    
    @staticmethod
    async def find_frequent_siblings(page, min_siblings: int = 5) -> List[Dict]:
        """
        Find parent elements with many similar children.
        
        Good for detecting grids/lists of items.
        """
        return await page.evaluate("""
            (minSiblings) => {
                const results = [];
                const processed = new Set();
                
                for (const parent of document.querySelectorAll('*')) {
                    if (processed.has(parent)) continue;
                    
                    const children = parent.children;
                    if (children.length < minSiblings) continue;
                    
                    // Group children by tag+class signature
                    const signatures = {};
                    for (const child of children) {
                        const cls = typeof child.className === 'string'
                            ? child.className.split(' ')[0] || ''
                            : '';
                        const sig = child.tagName + (cls ? '.' + cls : '');
                        signatures[sig] = (signatures[sig] || 0) + 1;
                    }
                    
                    // Find dominant signature
                    const dominant = Object.entries(signatures)
                        .sort((a, b) => b[1] - a[1])[0];
                    
                    if (dominant && dominant[1] >= minSiblings) {
                        processed.add(parent);
                        
                        const parentCls = typeof parent.className === 'string'
                            ? parent.className.split(' ')[0]
                            : null;
                        
                        results.push({
                            parent_selector: parent.tagName.toLowerCase() + 
                                (parentCls ? '.' + parentCls : ''),
                            child_signature: dominant[0],
                            child_count: dominant[1],
                            total_children: children.length,
                            uniformity: Math.round(dominant[1] / children.length * 100)
                        });
                    }
                }
                
                return results
                    .sort((a, b) => b.child_count - a.child_count)
                    .slice(0, 20);
            }
        """, min_siblings)
    
    @staticmethod
    async def count_links_by_pattern(page) -> Dict[str, Any]:
        """
        Count links grouped by URL pattern.
        
        Identifies product links, category links, etc.
        """
        return await page.evaluate("""
            () => {
                const patterns = {
                    product_numeric: { pattern: /\\/\\d{4,}$/, count: 0 },
                    product_html: { pattern: /_\\d+\\.html$/, count: 0 },
                    product_slug: { pattern: /\\/(product|produkt|item)\\//, count: 0 },
                    category: { pattern: /\\/(category|kategoria|cat)\\//, count: 0 },
                    offers: { pattern: /\\/offers\\/\\d+/, count: 0 },
                    external: { pattern: /^https?:\\/\\/(?!.*${window.location.host})/, count: 0 },
                    anchor: { pattern: /^#/, count: 0 },
                    other: { count: 0 }
                };
                
                for (const link of document.links) {
                    const href = link.href || '';
                    const pathname = link.pathname || '';
                    
                    let matched = false;
                    for (const [name, obj] of Object.entries(patterns)) {
                        if (obj.pattern && obj.pattern.test(pathname || href)) {
                            obj.count++;
                            matched = true;
                            break;
                        }
                    }
                    if (!matched) patterns.other.count++;
                }
                
                return {
                    total_links: document.links.length,
                    by_pattern: Object.fromEntries(
                        Object.entries(patterns).map(([k, v]) => [k, v.count])
                    )
                };
            }
        """)
