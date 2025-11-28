"""
DOM Analysis - Statistical analysis of DOM structure

No hardcoded rules - uses statistical properties to understand page.
"""

from typing import Dict, Any, List
from collections import defaultdict


async def analyze_structure(page) -> Dict[str, Any]:
    """
    Analyze DOM structure statistically.
    
    Args:
        page: Playwright page
        
    Returns:
        {
            depth_stats: {depth: element_count},
            class_patterns: {class: count},
            feature_locations: {prices: [...], links: [...]}
        }
    """
    result = {
        "depth_stats": {},
        "class_patterns": {},
        "feature_locations": {},
        "optimal_depths": {}
    }
    
    try:
        stats = await page.evaluate("""
        () => {
            const depthMap = {};
            const classCount = {};
            const priceDepths = [];
            const linkDepths = [];
            
            function getDepth(el) {
                let depth = 0;
                let current = el;
                while (current && current !== document.body) {
                    depth++;
                    current = current.parentElement;
                }
                return depth;
            }
            
            // Analyze all elements
            document.querySelectorAll('*').forEach(el => {
                const depth = getDepth(el);
                depthMap[depth] = (depthMap[depth] || 0) + 1;
                
                // Track classes
                if (el.className && typeof el.className === 'string') {
                    const firstClass = el.className.split(' ')[0];
                    if (firstClass && firstClass.length > 2) {
                        classCount[firstClass] = (classCount[firstClass] || 0) + 1;
                    }
                }
                
                // Track prices
                const text = (el.innerText || '').substring(0, 100);
                if (/\\d+[,.]?\\d*\\s*(?:zł|PLN|€|\\$)/.test(text)) {
                    priceDepths.push(depth);
                }
                
                // Track links
                if (el.tagName === 'A' && el.href) {
                    linkDepths.push(depth);
                }
            });
            
            return {
                depthMap,
                classCount,
                priceDepths,
                linkDepths
            };
        }
        """)
        
        result["depth_stats"] = stats.get("depthMap", {})
        result["class_patterns"] = stats.get("classCount", {})
        result["feature_locations"] = {
            "prices": stats.get("priceDepths", []),
            "links": stats.get("linkDepths", [])
        }
        
        # Calculate optimal depths
        result["optimal_depths"] = _calculate_optimal_depths(
            result["depth_stats"],
            result["feature_locations"]
        )
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def _calculate_optimal_depths(depth_stats: Dict, features: Dict) -> Dict[str, Any]:
    """Calculate optimal depth levels from statistics."""
    result = {}
    
    # Find depth with most prices
    price_depths = features.get("prices", [])
    if price_depths:
        depth_counts = defaultdict(int)
        for d in price_depths:
            depth_counts[d] += 1
        result["price_peak_depth"] = max(depth_counts.keys(), key=lambda k: depth_counts[k])
    
    # Find depth with most elements (potential containers)
    if depth_stats:
        result["element_peak_depth"] = max(depth_stats.keys(), key=lambda k: depth_stats.get(k, 0))
    
    return result


async def get_depth_stats(page) -> Dict[int, int]:
    """Get element count per depth level."""
    try:
        return await page.evaluate("""
        () => {
            const depthMap = {};
            
            function getDepth(el) {
                let depth = 0;
                let current = el;
                while (current && current !== document.body) {
                    depth++;
                    current = current.parentElement;
                }
                return depth;
            }
            
            document.querySelectorAll('*').forEach(el => {
                const depth = getDepth(el);
                depthMap[depth] = (depthMap[depth] || 0) + 1;
            });
            
            return depthMap;
        }
        """) or {}
    except Exception:
        return {}


async def find_repeating_patterns(
    page,
    min_count: int = 3
) -> List[Dict[str, Any]]:
    """
    Find repeating class patterns in DOM.
    
    Args:
        page: Playwright page
        min_count: Minimum repetitions to report
        
    Returns:
        [{class_name, count, sample_text}]
    """
    try:
        patterns = await page.evaluate(f"""
        () => {{
            const classCount = {{}};
            const samples = {{}};
            
            document.querySelectorAll('*').forEach(el => {{
                if (!el.className || typeof el.className !== 'string') return;
                const firstClass = el.className.split(' ')[0];
                if (!firstClass || firstClass.length < 3) return;
                
                classCount[firstClass] = (classCount[firstClass] || 0) + 1;
                if (!samples[firstClass]) {{
                    samples[firstClass] = (el.innerText || '').substring(0, 80);
                }}
            }});
            
            return Object.entries(classCount)
                .filter(([_, count]) => count >= {min_count})
                .sort((a, b) => b[1] - a[1])
                .slice(0, 20)
                .map(([cls, count]) => ({{
                    class_name: cls,
                    count: count,
                    sample_text: samples[cls] || ''
                }}));
        }}
        """)
        return patterns or []
    except Exception:
        return []
