"""
Pattern Detector - Find Repeating DOM Patterns

Pure JavaScript analysis for detecting:
- Repeating containers (product grids, article lists)
- Common structural patterns
- Price/name/link co-occurrence
"""

from typing import Dict, List, Any


class PatternDetector:
    """
    Detect repeating patterns in DOM structure.
    
    Uses statistical analysis to find containers that likely hold
    similar items (products, articles, search results).
    """
    
    @staticmethod
    async def find_repeating_containers(
        page, 
        min_count: int = 5,
        require_links: bool = True,
        require_price_signals: bool = True
    ) -> List[Dict]:
        """
        Find containers that repeat with similar structure.
        
        Returns containers sorted by likelihood of being product/item containers.
        """
        return await page.evaluate("""
            (args) => {
                const minCount = args.minCount;
                const requireLinks = args.requireLinks;
                const requirePriceSignals = args.requirePriceSignals;
                
                const pricePattern = /\\d+[,.]\\d{2}\\s*(?:zł|PLN|€|\\$|USD|EUR)/i;
                const priceImagePattern = /cb_|cn_|cena|price/i;
                
                // Group elements by their "signature" (tag + first 2 classes)
                const signatures = new Map();
                
                for (const el of document.querySelectorAll('*')) {
                    if (!el.className || typeof el.className !== 'string') continue;
                    
                    const classes = el.className.split(' ')
                        .filter(c => c.length > 2 && /^[a-zA-Z]/.test(c))
                        .slice(0, 2);
                    if (classes.length === 0) continue;
                    
                    const signature = el.tagName.toLowerCase() + '.' + classes.join('.');
                    
                    if (!signatures.has(signature)) {
                        signatures.set(signature, []);
                    }
                    signatures.get(signature).push(el);
                }
                
                // Analyze each signature group
                const results = [];
                
                for (const [signature, elements] of signatures) {
                    if (elements.length < minCount) continue;
                    
                    // Sample analysis (first 10 elements)
                    const samples = elements.slice(0, 10);
                    let linksCount = 0;
                    let priceSignalsCount = 0;
                    let imagesCount = 0;
                    let totalTextLength = 0;
                    
                    for (const el of samples) {
                        if (el.querySelector('a[href]')) linksCount++;
                        if (el.querySelector('img')) imagesCount++;
                        totalTextLength += (el.textContent || '').length;
                        
                        // Check price signals
                        const text = el.textContent || '';
                        const hasTextPrice = pricePattern.test(text);
                        const hasPriceImage = !!el.querySelector('img[src]') && 
                            Array.from(el.querySelectorAll('img')).some(img => 
                                priceImagePattern.test(img.src || '')
                            );
                        if (hasTextPrice || hasPriceImage) priceSignalsCount++;
                    }
                    
                    const linkRatio = linksCount / samples.length;
                    const priceRatio = priceSignalsCount / samples.length;
                    const imageRatio = imagesCount / samples.length;
                    const avgTextLength = totalTextLength / samples.length;
                    
                    // Filter based on requirements
                    if (requireLinks && linkRatio < 0.5) continue;
                    if (requirePriceSignals && priceRatio < 0.3) continue;
                    
                    // Calculate quality score
                    let score = elements.length;  // Base: count
                    score += linkRatio * 50;      // Links are important
                    score += priceRatio * 100;    // Price signals very important
                    score += imageRatio * 30;     // Images are good
                    
                    // Penalize too short/long text
                    if (avgTextLength < 20) score -= 30;
                    if (avgTextLength > 2000) score -= 50;
                    
                    // Build selector
                    const selector = signature.split('.').slice(0, 2).join('.');
                    
                    results.push({
                        selector: selector,
                        count: elements.length,
                        score: Math.round(score),
                        metrics: {
                            link_ratio: Math.round(linkRatio * 100) / 100,
                            price_ratio: Math.round(priceRatio * 100) / 100,
                            image_ratio: Math.round(imageRatio * 100) / 100,
                            avg_text_length: Math.round(avgTextLength)
                        },
                        sample_text: samples[0]?.textContent?.slice(0, 100) || ''
                    });
                }
                
                return results.sort((a, b) => b.score - a.score).slice(0, 20);
            }
        """, {
            "minCount": min_count,
            "requireLinks": require_links,
            "requirePriceSignals": require_price_signals
        })
    
    @staticmethod
    async def find_list_structures(page) -> List[Dict]:
        """
        Find ul/ol/table structures that might contain items.
        
        Returns list structures with item counts and content hints.
        """
        return await page.evaluate("""
            () => {
                const results = [];
                
                // Check UL/OL lists
                for (const list of document.querySelectorAll('ul, ol')) {
                    const items = list.querySelectorAll(':scope > li');
                    if (items.length < 3) continue;
                    
                    const hasLinks = !!list.querySelector('a[href]');
                    const hasImages = !!list.querySelector('img');
                    const avgItemText = Array.from(items)
                        .reduce((sum, li) => sum + (li.textContent?.length || 0), 0) / items.length;
                    
                    // Build minimal selector
                    const classes = typeof list.className === 'string' 
                        ? list.className.split(' ').filter(c => c.length > 0)[0] 
                        : null;
                    const selector = list.tagName.toLowerCase() + (classes ? '.' + classes : '');
                    
                    results.push({
                        type: 'list',
                        selector: selector,
                        item_count: items.length,
                        has_links: hasLinks,
                        has_images: hasImages,
                        avg_item_text: Math.round(avgItemText)
                    });
                }
                
                // Check tables
                for (const table of document.querySelectorAll('table')) {
                    const rows = table.querySelectorAll('tbody > tr, tr');
                    if (rows.length < 3) continue;
                    
                    const hasLinks = !!table.querySelector('a[href]');
                    const hasImages = !!table.querySelector('img');
                    
                    const classes = typeof table.className === 'string'
                        ? table.className.split(' ').filter(c => c.length > 0)[0]
                        : null;
                    const selector = 'table' + (classes ? '.' + classes : '');
                    
                    results.push({
                        type: 'table',
                        selector: selector,
                        item_count: rows.length,
                        has_links: hasLinks,
                        has_images: hasImages,
                        column_count: rows[0]?.querySelectorAll('td, th').length || 0
                    });
                }
                
                return results.sort((a, b) => b.item_count - a.item_count).slice(0, 10);
            }
        """)
    
    @staticmethod
    async def detect_grid_layout(page) -> Dict[str, Any]:
        """
        Detect CSS grid/flexbox layouts that might be product grids.
        
        Returns grid containers with their properties.
        """
        return await page.evaluate("""
            () => {
                const grids = [];
                
                for (const el of document.querySelectorAll('*')) {
                    const style = window.getComputedStyle(el);
                    const display = style.display;
                    
                    if (display === 'grid' || display === 'flex') {
                        const children = el.children.length;
                        if (children < 4) continue;  // Need multiple items
                        
                        // Check if children have similar structure
                        const childTags = new Set();
                        const childClasses = new Set();
                        for (const child of el.children) {
                            childTags.add(child.tagName);
                            if (child.className && typeof child.className === 'string') {
                                const firstClass = child.className.split(' ')[0];
                                if (firstClass) childClasses.add(firstClass);
                            }
                        }
                        
                        // If children are uniform (same tag and class), likely a grid
                        if (childTags.size === 1 && childClasses.size <= 2) {
                            const classes = typeof el.className === 'string'
                                ? el.className.split(' ').filter(c => c.length > 0)[0]
                                : null;
                            
                            grids.push({
                                selector: el.tagName.toLowerCase() + (classes ? '.' + classes : ''),
                                display: display,
                                children_count: children,
                                child_tag: Array.from(childTags)[0],
                                child_class: Array.from(childClasses)[0] || null,
                                has_images: !!el.querySelector('img'),
                                has_links: !!el.querySelector('a[href]')
                            });
                        }
                    }
                }
                
                return {
                    grids: grids.slice(0, 10),
                    total_found: grids.length
                };
            }
        """)
    
    @staticmethod
    async def find_sibling_groups(page, min_siblings: int = 5) -> List[Dict]:
        """
        Find groups of sibling elements with same structure.
        
        Useful for finding repeated items regardless of container styling.
        """
        return await page.evaluate("""
            (minSiblings) => {
                const groups = [];
                const processed = new Set();
                
                for (const el of document.querySelectorAll('*')) {
                    if (processed.has(el)) continue;
                    
                    const parent = el.parentElement;
                    if (!parent) continue;
                    
                    // Get siblings with same tag
                    const siblings = Array.from(parent.children).filter(child => 
                        child.tagName === el.tagName
                    );
                    
                    if (siblings.length < minSiblings) continue;
                    
                    // Mark as processed
                    siblings.forEach(s => processed.add(s));
                    
                    // Analyze group
                    const classes = typeof el.className === 'string'
                        ? el.className.split(' ').filter(c => c.length > 0)[0]
                        : null;
                    
                    const hasLinks = siblings.some(s => s.querySelector('a[href]'));
                    const hasImages = siblings.some(s => s.querySelector('img'));
                    const avgText = siblings.reduce((sum, s) => 
                        sum + (s.textContent?.length || 0), 0
                    ) / siblings.length;
                    
                    // Build child selector
                    const selector = parent.tagName.toLowerCase() + 
                        (parent.className && typeof parent.className === 'string' 
                            ? '.' + parent.className.split(' ')[0] 
                            : '') +
                        ' > ' + el.tagName.toLowerCase() +
                        (classes ? '.' + classes : '');
                    
                    groups.push({
                        selector: selector,
                        count: siblings.length,
                        has_links: hasLinks,
                        has_images: hasImages,
                        avg_text_length: Math.round(avgText)
                    });
                }
                
                return groups.sort((a, b) => b.count - a.count).slice(0, 15);
            }
        """, min_siblings)
