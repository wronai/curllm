"""
Dynamic Pattern Detection System

Generic, adaptive container detection bez hard-coded selectors.
Analizuje strukturę DOM i wykrywa wzorce dynamicznie.

Approach:
1. Find elements with signals (prices, links, images)
2. Analyze their parent structures
3. Cluster similar structures
4. Pick most frequent pattern
5. Extract generically
"""

import json
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import Counter


@dataclass
class DOMNode:
    """Representation of a DOM node structure"""
    tag: str
    classes: List[str]
    has_price: bool
    has_link: bool
    has_image: bool
    text_length: int
    depth: int
    selector: str
    
    def signature(self) -> str:
        """Unique signature for clustering"""
        return f"{self.tag}|{','.join(sorted(self.classes)[:3])}|{self.has_price}|{self.has_link}|{self.has_image}"
    
    def structural_signature(self) -> str:
        """Structural signature (ignoring specific class names)"""
        return f"{self.tag}|{len(self.classes)}|{self.has_price}|{self.has_link}|{self.has_image}"


class DynamicPatternDetector:
    """
    Dynamically detects repeating patterns in DOM structure
    
    No hard-coded selectors - learns from page structure!
    Uses LLM to discover optimal heuristics for each site.
    """
    
    def __init__(self, page, run_logger=None, llm=None):
        self.page = page
        self.run_logger = run_logger
        self.llm = llm
        self._dynamic_selectors = None
    
    def _log(self, message: str, data: Any = None):
        """Log detection steps"""
        if self.run_logger:
            self.run_logger.log_text(f"🔍 Dynamic Detector: {message}")
            if data:
                self.run_logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False)[:500])
    
    async def detect_product_containers(self) -> Optional[Dict[str, Any]]:
        """
        Main detection pipeline - fully dynamic!
        
        Returns:
            {
                'selector': '.detected-class',
                'count': 32,
                'confidence': 0.95,
                'method': 'clustering',
                'structure': {...}
            }
        """
        self._log("Starting dynamic pattern detection")
        
        # Step 1: Find signal elements (prices, product links)
        signals = await self._find_signal_elements()
        
        if not signals or len(signals) < 5:
            self._log("Not enough signal elements", {"count": len(signals) if signals else 0})
            return None
        
        self._log(f"Found {len(signals)} signal elements")
        
        # Step 2: Extract parent structures
        structures = await self._extract_parent_structures(signals)
        
        if not structures:
            self._log("No parent structures found")
            return None
        
        self._log(f"Analyzed {len(structures)} parent structures")
        
        # Step 3: Cluster similar structures
        clusters = self._cluster_structures(structures)
        
        if not clusters:
            self._log("No clusters formed")
            return None
        
        self._log(f"Formed {len(clusters)} clusters")
        
        # Step 4: Pick best cluster
        best = self._pick_best_cluster(clusters)
        
        if not best:
            self._log("No suitable cluster found")
            return None
        
        self._log("Best pattern detected", {
            "selector": best['selector'],
            "count": best['count'],
            "confidence": best['confidence']
        })
        
        return best
    
    async def _get_dynamic_link_selector(self) -> Optional[str]:
        """
        Get dynamic product link selector using LLM heuristics discovery
        
        Falls back to common patterns if LLM unavailable
        """
        # Return cached if available
        if self._dynamic_selectors:
            return self._dynamic_selectors.get("product_link_selector")
        
        # Try LLM-based discovery
        if self.llm:
            try:
                from .llm_heuristics import LLMHeuristicsDiscovery
                discovery = LLMHeuristicsDiscovery(self.page, self.llm, self.run_logger)
                self._dynamic_selectors = await discovery.build_dynamic_selectors()
                
                selector = self._dynamic_selectors.get("product_link_selector")
                if selector:
                    self._log("Using LLM-discovered link selector", {"selector": selector})
                    return selector
            except Exception as e:
                self._log("LLM heuristics discovery failed", str(e))
        
        # Fallback to common patterns
        fallback = 'a[href*="product"], a[href*="item"], a[href*="/p/"], a[href*="/produkt"], a[href$=".html"]'
        self._log("Using fallback link selector", {"selector": fallback})
        return fallback
    
    async def _find_signal_elements(self) -> List[Dict]:
        """
        Find elements that signal product presence
        
        Signals:
        - Price patterns (123.99 zł)
        - Product-like links
        - Images with alt text
        """
        # Get dynamic selectors if LLM available
        link_selector = await self._get_dynamic_link_selector()
        
        return await self.page.evaluate("""
            (linkSelector) => {
                const signals = [];
                
                // Price regex - supports multiple currencies
                const priceRegex = /\\d+[\\s,.]?\\d*[\\s,.]?\\d{2}\\s*(?:zł|PLN|€|\\$|USD|EUR|грн|руб)/i;
                
                // Find all elements
                const allElements = Array.from(document.querySelectorAll('*'));
                
                // Track processed to avoid duplicates
                const processed = new Set();
                
                for (const el of allElements) {
                    if (processed.has(el)) continue;
                    
                    const text = el.innerText || '';
                    const hasPrice = priceRegex.test(text);
                    
                    // Skip if text too long (likely not a product)
                    if (text.length > 1000) continue;
                    
                    // Check for signals - use DYNAMIC selector from LLM
                    const hasLink = linkSelector ? 
                        !!el.querySelector(linkSelector) :
                        !!el.querySelector('a[href]');
                    const hasImage = !!el.querySelector('img');
                    
                    // Must have at least price OR (link + image)
                    if (hasPrice || (hasLink && hasImage)) {
                        signals.push({
                            element: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : ''),
                            hasPrice: hasPrice,
                            hasLink: hasLink,
                            hasImage: hasImage,
                            textLength: text.length,
                            // Store path for parent analysis
                            path: el
                        });
                        
                        processed.add(el);
                    }
                }
                
                return signals.slice(0, 100); // Limit to first 100
            }
        """, link_selector)
    
    async def _extract_parent_structures(self, signals: List[Dict]) -> List[DOMNode]:
        """
        Extract parent structures for clustering
        
        For each signal, check parents 1-4 levels up
        """
        return await self.page.evaluate("""
            (signals) => {
                const structures = [];
                
                signals.forEach((signal, idx) => {
                    // Get the actual element (path is a reference)
                    const el = document.querySelectorAll('*')[idx];
                    if (!el) return;
                    
                    // Check parents 1-4 levels up
                    let parent = el;
                    for (let depth = 0; depth < 4 && parent; depth++) {
                        parent = parent.parentElement;
                        if (!parent) break;
                        
                        // Get classes (handle SVG elements where className is SVGAnimatedString)
                        const classNameStr = typeof parent.className === 'string' 
                            ? parent.className 
                            : (parent.className && parent.className.baseVal ? parent.className.baseVal : '');
                        const classes = classNameStr ? 
                            classNameStr.split(' ')
                                .filter(c => c.length > 0)
                                .filter(c => /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(c))
                            : 
                            [];
                        
                        // Build selector
                        let selector = parent.tagName.toLowerCase();
                        if (classes.length > 0) {
                            selector += '.' + classes[0];
                        }
                        
                        // Count elements with same selector
                        const sameElements = document.querySelectorAll(selector);
                        
                        // Only consider if there are multiple similar elements
                        if (sameElements.length >= 5) {
                            // Check structure
                            const hasPrice = /\\d+[\\s,.]?\\d*[\\s,.]?\\d{2}\\s*(?:zł|PLN|€|\\$)/i.test(parent.innerText || '');
                            const hasLink = !!parent.querySelector('a[href]');
                            const hasImage = !!parent.querySelector('img');
                            
                            structures.push({
                                tag: parent.tagName.toLowerCase(),
                                classes: classes,
                                has_price: hasPrice,
                                has_link: hasLink,
                                has_image: hasImage,
                                text_length: (parent.innerText || '').length,
                                depth: depth,
                                selector: selector,
                                count: sameElements.length
                            });
                        }
                    }
                });
                
                return structures;
            }
        """, signals)
    
    def _cluster_structures(self, structures: List[Dict]) -> List[Dict]:
        """
        Cluster structures by similarity
        
        Uses structural signature to group similar patterns
        """
        # Count by structural signature
        signature_counts = Counter()
        signature_examples = {}
        
        for struct in structures:
            # Create signature
            sig = f"{struct['tag']}|{len(struct.get('classes', []))}|{struct.get('has_price')}|{struct.get('has_link')}|{struct.get('has_image')}"
            
            signature_counts[sig] += 1
            
            if sig not in signature_examples:
                signature_examples[sig] = struct
        
        # Create clusters from frequent signatures
        clusters = []
        for sig, count in signature_counts.most_common():
            if count >= 5:  # Minimum cluster size
                example = signature_examples[sig]
                clusters.append({
                    'signature': sig,
                    'count': count,
                    'example': example,
                    'selector': example.get('selector', ''),
                    'structure': example
                })
        
        return clusters
    
    def _pick_best_cluster(self, clusters: List[Dict]) -> Optional[Dict]:
        """
        Pick best cluster based on heuristics
        
        Scoring:
        - Specificity (has class names - IMPORTANT!)
        - Size (more is better)
        - Has price + link (required)
        - Has image (bonus)
        - Text length (not too short, not too long)
        """
        scored_clusters = []
        
        for cluster in clusters:
            struct = cluster['structure']
            selector = cluster['selector']
            count = cluster['count']  # Extract count FIRST!
            score = 0
            
            # CRITICAL: Filter out overly generic selectors
            tag = struct.get('tag', '')
            classes = struct.get('classes', [])
            
            # Skip if no classes and generic tag
            if len(classes) == 0 and tag in ['div', 'span', 'article', 'section', 'li']:
                self._log(f"Skipping too generic: {selector}", {"reason": "no_classes"})
                continue
            
            # CRITICAL: Skip if count too low for product listings
            if count < 5:
                self._log(f"Skipping low count: {selector}", {"count": count, "threshold": 5})
                continue
            
            # CRITICAL: Must have price! (Product containers should contain prices)
            if not struct.get('has_price'):
                self._log(f"Skipping no price: {selector}", {"reason": "likely_navigation_or_layout"})
                continue
            
            # Specificity score (CRITICAL)
            if len(classes) > 0:
                score += 30  # Has at least one class
                if len(classes) >= 2:
                    score += 5  # Multiple classes even better
            else:
                score -= 20  # Penalty for no classes
            
            # Size score (reduced weight)
            score += min(count / 50.0, 1.0) * 25  # Max 25 points
            
            # Structure score (PRICE IS NOW REQUIRED - see above filter)
            score += 25  # Has price (guaranteed by filter)
            if struct.get('has_link'):
                score += 15  # Important
            if struct.get('has_image'):
                score += 10  # More important now
            
            # Text length score (sweet spot: 50-500 chars)
            text_len = struct.get('text_length', 0)
            if 50 <= text_len <= 500:
                score += 5
            
            # Bonus for high count + specificity + complete structure
            if count >= 10 and len(classes) > 0:
                score += 10
            
            # Big bonus for complete product-like structure
            if struct.get('has_price') and struct.get('has_link') and struct.get('has_image'):
                score += 15  # Perfect product structure!
            
            scored_clusters.append({
                'cluster': cluster,
                'score': score,
                'count': count,
                'specificity': len(classes)
            })
        
        if not scored_clusters:
            self._log("No suitable clusters after filtering")
            return None
        
        # Sort by score
        scored_clusters.sort(key=lambda x: x['score'], reverse=True)
        best = scored_clusters[0]
        
        # Require minimum score
        if best['score'] < 40:
            self._log(f"Best score too low: {best['score']}", {"threshold": 40})
            return None
        
        # Calculate confidence
        confidence = min(best['score'] / 100.0, 1.0)
        
        self._log("Selected best pattern", {
            "selector": best['cluster']['selector'],
            "score": best['score'],
            "count": best['count'],
            "specificity": best['specificity']
        })
        
        return {
            'selector': best['cluster']['selector'],
            'count': best['cluster']['count'],
            'confidence': confidence,
            'method': 'dynamic_clustering',
            'structure': best['cluster']['structure'],
            'score': best['score']
        }


class GenericFieldExtractor:
    """
    Generic field extraction - no hard-coded selectors!
    
    Dynamically finds where name, price, url are in a container
    """
    
    def __init__(self, page, run_logger=None):
        self.page = page
        self.run_logger = run_logger
    
    def _log(self, message: str, data: Any = None):
        if self.run_logger:
            self.run_logger.log_text(f"🔧 Generic Extractor: {message}")
            if data:
                self.run_logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False)[:300])
    
    async def detect_fields(self, container_selector: str) -> Optional[Dict[str, Any]]:
        """
        Dynamically detect where fields are in container
        
        Args:
            container_selector: The detected container selector
            
        Returns:
            {
                'name': {'selector': '...', 'strategy': '...'},
                'price': {'selector': '...', 'strategy': '...'},
                'url': {'selector': '...', 'strategy': '...'}
            }
        """
        self._log(f"Detecting fields in {container_selector}")
        
        # Validate container exists
        container_exists = await self.page.evaluate(f"""
            () => {{
                const containers = document.querySelectorAll('{container_selector}');
                return containers.length > 0;
            }}
        """)
        
        if not container_exists:
            self._log(f"Container {container_selector} not found on page")
            return None
        
        result = await self.page.evaluate("""
            (containerSel) => {
                const container = document.querySelector(containerSel);
                if (!container) {
                    return {error: 'container_not_found'};
                }
                
                const fields = {};
                
                // === PRICE DETECTION ===
                // Find element with price pattern
                const priceRegex = /\\d+[\\s,.]?\\d*[\\s,.]?\\d{2}\\s*(?:zł|PLN|€|\\$)/i;
                const allInContainer = Array.from(container.querySelectorAll('*'));
                
                let priceEl = null;
                for (const el of allInContainer) {
                    const text = el.innerText || '';
                    // Check direct text (not inherited)
                    const ownText = text.replace(
                        Array.from(el.children).map(c => c.innerText || '').join(''),
                        ''
                    );
                    
                    if (priceRegex.test(ownText) && ownText.length < 50) {
                        priceEl = el;
                        break;
                    }
                }
                
                if (priceEl) {
                    const classes = (typeof priceEl.className === 'string' ? priceEl.className : (priceEl.className?.baseVal || '')).split(' ').filter(c => c);
                    fields.price = {
                        selector: priceEl.tagName.toLowerCase() + 
                                 (classes[0] ? '.' + classes[0] : ''),
                        strategy: 'text_with_regex'
                    };
                }
                
                // === URL DETECTION ===
                // Find most prominent link
                const links = Array.from(container.querySelectorAll('a[href]'))
                    .filter(a => {
                        const href = a.href || '';
                        // Filter out navigation/footer links
                        return !href.includes('#') && 
                               !href.includes('javascript:') &&
                               href.length > 10;
                    });
                
                if (links.length > 0) {
                    // Pick first or longest text
                    const mainLink = links.reduce((best, link) => {
                        const text = link.innerText || '';
                        const bestText = best.innerText || '';
                        return text.length > bestText.length ? link : best;
                    });
                    
                    const classes = (typeof mainLink.className === 'string' ? mainLink.className : (mainLink.className?.baseVal || '')).split(' ').filter(c => c);
                    fields.url = {
                        selector: 'a' + (classes[0] ? '.' + classes[0] : '[href]'),
                        strategy: 'href_attribute'
                    };
                }
                
                // === NAME DETECTION ===
                // Find heading or prominent text (but not price)
                const headings = Array.from(container.querySelectorAll('h1, h2, h3, h4, h5, h6, strong, b'));
                let nameEl = null;
                
                for (const h of headings) {
                    const text = h.innerText || '';
                    // Should be substantial but not too long
                    // Should NOT be the price
                    if (text.length > 10 && 
                        text.length < 200 && 
                        !priceRegex.test(text)) {
                        nameEl = h;
                        break;
                    }
                }
                
                // Fallback: longest text element (not price, not link text)
                if (!nameEl) {
                    let maxLen = 0;
                    for (const el of allInContainer) {
                        const text = el.innerText || '';
                        const ownText = text.replace(
                            Array.from(el.children).map(c => c.innerText || '').join(''),
                            ''
                        ).trim();
                        
                        if (ownText.length > maxLen && 
                            ownText.length > 10 &&
                            ownText.length < 200 &&
                            !priceRegex.test(ownText)) {
                            maxLen = ownText.length;
                            nameEl = el;
                        }
                    }
                }
                
                if (nameEl) {
                    const classes = (typeof nameEl.className === 'string' ? nameEl.className : (nameEl.className?.baseVal || '')).split(' ').filter(c => c);
                    fields.name = {
                        selector: nameEl.tagName.toLowerCase() + 
                                 (classes[0] ? '.' + classes[0] : ''),
                        strategy: 'innerText'
                    };
                }
                
                return fields;
            }
        """, container_selector)
        
        # Check if we got an error
        if result and result.get('error'):
            self._log(f"Field detection error: {result['error']}")
            return None
        
        # Check if we found at least price OR name
        if not result or (not result.get('price') and not result.get('name')):
            self._log("No critical fields found (need price or name)")
            return None
        
        self._log("Fields detected successfully", result)
        return result
    
    async def extract_all(
        self,
        container_selector: str,
        field_strategy: Dict[str, Any],
        max_items: int = 50
    ) -> List[Dict]:
        """
        Extract all items using detected strategy
        
        Completely generic!
        """
        self._log(f"Extracting up to {max_items} items")
        
        return await self.page.evaluate("""
            (args) => {
                const {containerSel, fields, maxItems} = args;
                const containers = document.querySelectorAll(containerSel);
                const products = [];
                
                const priceRegex = /\\d+[\\s,.]?\\d*[\\s,.]?\\d{2}\\s*(?:zł|PLN|€|\\$)/i;
                
                for (let i = 0; i < Math.min(containers.length, maxItems); i++) {
                    const container = containers[i];
                    const product = {};
                    
                    // Extract name
                    if (fields.name) {
                        const nameEl = container.querySelector(fields.name.selector);
                        if (nameEl) {
                            product.name = (nameEl.innerText || '').trim();
                        }
                    }
                    
                    // Extract price
                    if (fields.price) {
                        const priceEl = container.querySelector(fields.price.selector);
                        if (priceEl) {
                            const text = priceEl.innerText || '';
                            const match = text.match(priceRegex);
                            if (match) {
                                const priceStr = match[0].replace(/[^0-9.,]/g, '').replace(',', '.');
                                product.price = parseFloat(priceStr);
                            }
                        }
                    }
                    
                    // Extract URL
                    if (fields.url) {
                        const urlEl = container.querySelector(fields.url.selector);
                        if (urlEl && urlEl.href) {
                            product.url = urlEl.href;
                        }
                    }
                    
                    // Only add if has at least name or price
                    if (product.name || product.price) {
                        products.push(product);
                    }
                }
                
                return products;
            }
        """, {
            "containerSel": container_selector,
            "fields": field_strategy,
            "maxItems": max_items
        })


async def dynamic_extract(
    page,
    instruction: str,
    run_logger=None,
    max_items: int = 50
) -> Dict[str, Any]:
    """
    Fully dynamic extraction pipeline
    
    Usage:
        result = await dynamic_extract(page, "Find products under 500zł")
    """
    # Step 1: Detect containers dynamically
    detector = DynamicPatternDetector(page, run_logger)
    container_info = await detector.detect_product_containers()
    
    if not container_info:
        return {"products": [], "reason": "No patterns detected"}
    
    # Step 2: Detect fields generically
    extractor = GenericFieldExtractor(page, run_logger)
    field_strategy = await extractor.detect_fields(container_info['selector'])
    
    if not field_strategy:
        return {"products": [], "reason": "No fields detected"}
    
    # Step 3: Extract all items
    products = await extractor.extract_all(
        container_info['selector'],
        field_strategy,
        max_items
    )
    
    # Step 4: Apply filters from instruction
    # (Price filtering logic here)
    
    return {
        "products": products,
        "count": len(products),
        "method": "dynamic_detection",
        "container": container_info,
        "fields": field_strategy
    }
