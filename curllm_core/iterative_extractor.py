"""
Iterative Extractor - Small Atomic DOM Queries with Full Logging

DEPRECATED: Use streamware.components.extraction.LLMIterativeExtractor instead.

This module is kept for backward compatibility.
New code should use:
    from curllm_core.streamware.components.extraction import LLMIterativeExtractor, llm_extract_products

Instead of sending entire DOM tree to LLM, we:
1. Quick check: Does page have products? (fast)
2. Structure analysis: What containers? (targeted)
3. Field detection: Which fields exist? (specific)
4. Data extraction: Extract values (minimal)

Each step logs details and makes early decisions.
"""

import json
from typing import Dict, List, Optional, Any

# New LLM-based extraction (recommended)
try:
    from .streamware.components.extraction import LLMIterativeExtractor, llm_extract_products
    LLM_EXTRACTOR_AVAILABLE = True
except ImportError:
    LLM_EXTRACTOR_AVAILABLE = False

# Dynamic detection and filtering systems (legacy)
try:
    from .dynamic_container_detector import DynamicContainerDetector
    from .multi_criteria_filter import MultiCriteriaFilter
    DYNAMIC_SYSTEMS_AVAILABLE = True
except ImportError:
    DYNAMIC_SYSTEMS_AVAILABLE = False


class IterativeExtractor:
    """Iterative extraction with atomic DOM queries"""
    
    def __init__(self, page, llm, instruction, run_logger=None, use_dynamic_detection=True):
        self.page = page
        self.llm = llm
        self.instruction = instruction
        self.run_logger = run_logger
        self.use_dynamic_detection = use_dynamic_detection and DYNAMIC_SYSTEMS_AVAILABLE
        self.state = {
            "checks_performed": [],
            "decisions": [],
            "extraction_strategy": None
        }
        
        # Initialize dynamic systems if available
        if self.use_dynamic_detection:
            self.dynamic_detector = DynamicContainerDetector(llm, run_logger)
            self.multi_filter = MultiCriteriaFilter(llm, run_logger)
        else:
            self.dynamic_detector = None
            self.multi_filter = None
    
    def _log(self, step: str, details: Any):
        """Log with details"""
        if self.run_logger:
            self.run_logger.log_text(f"🔍 {step}")
            if isinstance(details, dict):
                self.run_logger.log_code("json", json.dumps(details, indent=2, ensure_ascii=False))
            else:
                self.run_logger.log_text(f"   {details}")
        
        self.state["checks_performed"].append({
            "step": step,
            "details": details
        })
    
    async def quick_page_check(self) -> Dict[str, Any]:
        """
        Step 1: Quick check - what type of page is this?
        
        Fast JavaScript check WITHOUT extracting all data.
        Returns: page type, approximate counts, indicators
        """
        self._log("Step 1: Quick Page Check", "Running fast indicators check...")
        
        result = await self.page.evaluate("""
            () => {
                // Fast indicators check
                const indicators = {
                    has_prices: false,
                    price_count: 0,
                    has_product_links: false,
                    product_link_count: 0,
                    has_list_structure: false,
                    has_add_to_cart: false,
                    has_price_images: false,
                    total_links: document.links.length,
                    page_type: 'unknown'
                };
                
                // Check for price patterns (fast regex) - TEXT prices
                const pricePattern = /(\\d+[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN|€|\\$|USD|EUR)/i;
                const bodyText = document.body?.innerText || '';
                const priceMatches = bodyText.match(new RegExp(pricePattern, 'g'));
                
                if (priceMatches) {
                    indicators.has_prices = true;
                    indicators.price_count = priceMatches.length;
                }
                
                // Check for IMAGE-based prices (common in Polish shops like gral.pl)
                // Pattern: img.php?im=cb_ or similar dynamic price images
                const priceImages = document.querySelectorAll('img[src*="cen"], img[src*="price"], img[src*="cb_"], img[src*="cn_"]');
                if (priceImages.length > 0) {
                    indicators.has_price_images = true;
                    indicators.price_count = Math.max(indicators.price_count, priceImages.length);
                    indicators.has_prices = true;
                }
                
                // Check for "Cena" labels near images
                const cenaLabels = document.querySelectorAll('*');
                let cenaCount = 0;
                for (const el of cenaLabels) {
                    if (el.innerText && /cena\\s*(brutto|netto)?:?/i.test(el.innerText) && el.innerText.length < 50) {
                        cenaCount++;
                    }
                }
                if (cenaCount >= 3) {
                    indicators.has_prices = true;
                    indicators.price_count = Math.max(indicators.price_count, cenaCount);
                }
                
                // Check for product-like links - multiple patterns
                let productLinks = 0;
                for (const link of document.links) {
                    const href = link.href || '';
                    const pathname = link.pathname || '';
                    
                    // Pattern 1: /12345 or _12345 (numeric product IDs with .html)
                    if (/[_\\/]\\d{3,}\\.html?$/i.test(pathname)) {
                        productLinks++;
                    }
                    // Pattern 1b: /123456789 (pure numeric ID, 6+ digits - ceneo.pl style)
                    else if (/^\\/\\d{6,}$/.test(pathname)) {
                        productLinks++;
                    }
                    // Pattern 1c: /offers/ID/ID (ceneo.pl offer links)
                    else if (/^\\/offers\\/\\d+\\/\\d+/.test(pathname)) {
                        productLinks++;
                    }
                    // Pattern 2: /product/ or /produkt/ in URL
                    else if (/\\/(product|produkt|item|towar)\\//i.test(pathname)) {
                        productLinks++;
                    }
                    // Pattern 3: Name+Product+Name_ID.html (gral.pl style)
                    else if (/[A-Za-z]+\\+[A-Za-z]+.*_\\d+\\.html$/i.test(pathname)) {
                        productLinks++;
                    }
                    // Pattern 4: ;123456 (ceneo.pl style - semicolon + numeric ID)
                    else if (/;\\d{4,}/.test(pathname)) {
                        productLinks++;
                    }
                    // Pattern 5: /p/123456 or /i/123456 (common e-commerce pattern)
                    else if (/\\/[pi]\\/\\d+/i.test(pathname)) {
                        productLinks++;
                    }
                }
                indicators.product_link_count = productLinks;
                indicators.has_product_links = productLinks > 0;
                
                // Check for "add to cart" buttons/links
                const cartPatterns = ['koszyk', 'cart', 'dodaj', 'add', 'kupuj', 'buy'];
                const buttons = document.querySelectorAll('button, a, input[type="submit"]');
                let cartButtons = 0;
                for (const btn of buttons) {
                    const text = (btn.innerText || btn.value || btn.title || '').toLowerCase();
                    if (cartPatterns.some(p => text.includes(p))) {
                        cartButtons++;
                    }
                }
                indicators.has_add_to_cart = cartButtons >= 3;
                
                // Check for list structure (dynamic detection)
                // Look for repeating elements with similar structure (not hard-coded selectors)
                const allElements = document.querySelectorAll('*');
                const classCount = {};
                
                // Count elements with same class (potential list)
                for (const el of allElements) {
                    if (el.className && typeof el.className === 'string') {
                        const firstClass = el.className.split(' ')[0];
                        if (firstClass && /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(firstClass)) {
                            classCount[firstClass] = (classCount[firstClass] || 0) + 1;
                        }
                    }
                }
                
                // If any class appears 5+ times, likely a list structure
                indicators.has_list_structure = Object.values(classCount).some(count => count >= 5);
                
                // Check for REAL product containers (price + name together)
                // Use dynamic link patterns - discovered from page structure
                let realProductContainers = 0;
                const potentialProducts = document.querySelectorAll('[class*="product"], [class*="item"], [class*="card"], [class*="box"], table tr');
                
                // Dynamic link check - analyze actual URL patterns on page
                const checkProductLink = (el) => {
                    const links = el.querySelectorAll('a[href]');
                    for (const link of links) {
                        const href = link.href || '';
                        // Check for common product URL patterns dynamically
                        if (/\\/[pi]\\/|product|produkt|item|towar|\\.html$|_\\d{4,}|[/]\\d{4,}/.test(href)) {
                            return true;
                        }
                    }
                    return false;
                };
                
                // Dynamic price image check
                const checkPriceImage = (el) => {
                    const imgs = el.querySelectorAll('img');
                    for (const img of imgs) {
                        const src = img.src || '';
                        if (/cb_|cena|price|_c\\d|_p\\d/i.test(src)) return true;
                    }
                    return false;
                };
                
                for (const el of potentialProducts) {
                    const text = el.textContent || '';
                    const hasName = text.length > 20 && text.length < 500;
                    const hasLink = checkProductLink(el);
                    const hasPriceInEl = /\\d+[,.]\\d{2}/.test(text) || checkPriceImage(el);
                    if (hasName && hasLink && hasPriceInEl) {
                        realProductContainers++;
                    }
                }
                indicators.real_product_containers = realProductContainers;
                
                // Determine page type with smarter heuristics
                const hasRealProducts = realProductContainers >= 3;
                const hasProductGrid = realProductContainers >= 5;
                const hasShopFeatures = indicators.has_add_to_cart && indicators.has_product_links;
                
                // Check for cart/header prices (low count, no product structure)
                const isCartOnly = indicators.price_count <= 2 && !hasRealProducts;
                
                // Check URL patterns for product pages
                const url = window.location.href.toLowerCase();
                const pathname = window.location.pathname;
                const isProductUrl = /\\/(product|produkt|item|towar|prod_lista)s?/i.test(url) ||
                                     /[\\?&](category|kategoria|cat|grp)[=]/i.test(url) ||
                                     /[_\\/]\\d{3,}\\.html?$/i.test(pathname);
                const isHomepage = pathname === '/' || pathname === '/index.html' || pathname === '/sklep.php';
                
                // Decision tree - more conservative
                if (hasProductGrid) {
                    // Found actual product containers
                    indicators.page_type = 'product_listing';
                } else if (hasRealProducts && isProductUrl) {
                    indicators.page_type = 'product_listing';
                } else if (isProductUrl && indicators.price_count >= 3) {
                    indicators.page_type = 'product_listing';
                } else if (isHomepage && !hasRealProducts) {
                    // Homepage without real products - needs navigation
                    indicators.page_type = 'homepage_shop';
                    indicators.needs_navigation = true;
                } else if (indicators.has_product_links && indicators.product_link_count >= 10 && !hasRealProducts) {
                    // Many category links but no products
                    indicators.page_type = 'category_index';
                    indicators.needs_navigation = true;
                } else if (indicators.price_count > 0 && hasRealProducts) {
                    indicators.page_type = 'product_listing';
                } else {
                    indicators.page_type = 'other';
                }
                
                return indicators;
            }
        """)
        
        self._log("Quick Check Results", result)
        
        # Decide whether to continue extraction
        extractable_types = ["product_listing", "category", "single_product"]
        needs_nav_types = ["homepage", "homepage_shop", "category_index", "other"]
        should_continue = result["page_type"] in extractable_types
        needs_navigation = result.get("needs_navigation", False) or result["page_type"] in needs_nav_types
        
        # Build reason based on page type
        real_products = result.get("real_product_containers", 0)
        if result["page_type"] in ["homepage_shop", "category_index"]:
            reason = f"Navigation page detected ({result['page_type']}). Found {real_products} real products. Navigate to a product category to find actual products."
        elif result["page_type"] == "homepage":
            reason = "Homepage detected (cart prices only). Navigate to product category first."
        elif should_continue:
            reason = f"Page type: {result['page_type']}, real products: {real_products}, prices: {result['price_count']}"
        else:
            reason = f"Page type: {result['page_type']} - not a product page"
        
        decision = {
            "should_continue": should_continue,
            "reason": reason,
            "needs_navigation": needs_navigation,
            "real_product_containers": real_products
        }
        self.state["decisions"].append(decision)
        
        if self.run_logger:
            self.run_logger.log_text(f"📊 Decision: {reason}")
        
        return result
    
    async def detect_container_structure(self, page_type: str) -> Dict[str, Any]:
        """
        Step 2: Detect container structure
        
        Find the PATTERN of product containers without extracting data.
        Uses DynamicContainerDetector if available (statistical + LLM-based)
        Returns: container selector, count, sample structure
        """
        self._log("Step 2: Container Structure Detection", f"Looking for {page_type} containers...")
        
        # Try dynamic container detection first (if available)
        if self.use_dynamic_detection and self.dynamic_detector:
            try:
                if self.run_logger:
                    self.run_logger.log_text("🎯 Using Dynamic Container Detector (Statistical + LLM)")
                
                detection = await self.dynamic_detector.detect_containers(
                    self.page,
                    instruction=self.instruction,
                    use_llm=True
                )
                
                if detection.get('best_container'):
                    best = detection['best_container']
                    result = {
                        "found": True,
                        "best": best,
                        "candidates": detection.get('containers', [])[:5],  # Top 5 only
                        "method": "dynamic_detection_llm",
                        "transparency": detection.get('transparency', {})
                    }
                    
                    self._log("Container Detection Results", result)
                    return result
                else:
                    if self.run_logger:
                        self.run_logger.log_text("⚠️ Dynamic detector found no containers, using fallback")
            except Exception as e:
                if self.run_logger:
                    self.run_logger.log_text(f"⚠️ Dynamic detection error: {e}, using fallback")
        
        # Fallback: Original algorithmic detection
        result = await self.page.evaluate("""
            (pageType) => {
                const candidates = [];
                const priceRegex = /\\d+[\\d\\s]*(?:[\\.,]\\d{2})?\\s*(?:zł|PLN|€|\\$)/i;
                
                // DYNAMIC DETECTION: Find elements with prices (signals)
                const signalElements = Array.from(document.querySelectorAll('*'))
                    .filter(el => {
                        const text = el.innerText || '';
                        return priceRegex.test(text) && text.length < 1000;
                    })
                    .slice(0, 100);  // Limit to first 100
                
                // Map to track parent patterns
                const parentPatterns = new Map();
                
                // Analyze parents of signal elements
                for (const signal of signalElements) {
                    // Check parents 1-3 levels up
                    let parent = signal.parentElement;
                    for (let depth = 0; depth < 3 && parent; depth++) {
                        parent = parent.parentElement;
                        if (!parent) break;
                        
                        // Build selector (filter invalid CSS class names)
                        const classNameStr = typeof parent.className === 'string'
                            ? parent.className
                            : (parent.className?.baseVal || '');
                        const classes = classNameStr ? 
                            classNameStr.split(' ')
                                .filter(c => c.length > 0)
                                .filter(c => /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(c))
                            : [];
                        
                        if (classes.length === 0) continue;  // Skip elements without classes
                        
                        const selector = parent.tagName.toLowerCase() + '.' + classes[0];
                        
                        // Check if this pattern appears multiple times
                        const allMatches = document.querySelectorAll(selector);
                        
                        if (allMatches.length >= 5) {  // Must appear at least 5 times
                            const key = selector;
                            
                            if (!parentPatterns.has(key)) {
                                // Check structure
                                const hasPrice = priceRegex.test(parent.innerText || '');
                                const hasLink = !!parent.querySelector('a[href]');
                                const hasImage = !!parent.querySelector('img');
                                
                                // CRITICAL: Must have price!
                                if (hasPrice) {
                                    parentPatterns.set(key, {
                                        selector: selector,
                                        count: allMatches.length,
                                        has_link: hasLink,
                                        has_price: hasPrice,
                                        has_image: hasImage,
                                        classes: parent.className,
                                        sample_text: (parent.innerText || '').substring(0, 100),
                                        specificity: classes.length
                                    });
                                }
                            }
                        }
                    }
                }
                
                // Convert map to array and sort
                const dynamicCandidates = Array.from(parentPatterns.values());
                
                // Score and sort candidates with smart heuristics
                dynamicCandidates.forEach(c => {
                    let score = 0;
                    
                    // SPECIFICITY (most important for precision)
                    if (c.specificity >= 3) score += 50;  // Very specific
                    else if (c.specificity >= 2) score += 35;
                    else if (c.specificity >= 1) score += 20;
                    
                    // PENALTY for generic utility/layout classes (Tailwind/Bootstrap/Generic)
                    const firstClass = c.classes.split(' ')[0] || '';
                    const utilityPrefixes = ['mt-', 'mb-', 'ml-', 'mr-', 'mx-', 'my-', 'p-', 'px-', 'py-', 'pt-', 'pb-', 'pl-', 'pr-', 'flex', 'grid', 'block', 'inline', 'hidden', 'relative', 'absolute', 'fixed', 'static', 'w-', 'h-', 'text-', 'bg-', 'border-', 'rounded', 'shadow'];
                    const genericLayouts = ['container', 'row', 'col', 'wrapper', 'inner', 'outer', 'main', 'content', 'section', 'header', 'footer', 'sidebar', 'nav'];
                    const isUtilityClass = utilityPrefixes.some(prefix => firstClass.startsWith(prefix)) || genericLayouts.includes(firstClass);
                    if (isUtilityClass) score -= 30;  // Heavy penalty for layout classes
                    
                    // SIZE score (reduced importance)
                    score += Math.min(c.count / 50, 1) * 15;  // Max 15 (reduced from 25)
                    
                    // STRUCTURE requirements
                    score += 25;  // Has price (guaranteed)
                    score += c.has_link ? 20 : 0;  // Link important
                    score += c.has_image ? 15 : 0;  // Image bonus
                    
                    // TEXT QUALITY heuristics
                    const text = c.sample_text || '';
                    const hasProductKeywords = /laptop|phone|notebook|komputer|telefon|monitor|keyboard|mysz|słuchawk/i.test(text);
                    const hasSpecs = /\\d+GB|\\d+TB|\\d+"|\\d+MHz|\\d+GHz|Core|Ryzen|GeForce|Radeon/i.test(text);
                    const hasMarketingNoise = /okazja|promocja|rabat|zwrot|kup|teraz|black|weeks|banner/i.test(text);
                    
                    // CRITICAL: Cart/navigation penalties
                    // Replace non-breaking spaces (U+00A0) with regular spaces
                    const normalizedText = text.replace(/[\u00a0\xa0]/g, ' ').toLowerCase();
                    // Match cart/navigation keywords with flexible whitespace
                    const cartKeywords = ['twój pc', 'twój koszyk', 'your cart', 'koszyk', 'cart', 'zaloguj', 'login', 'menu', 'nawigacja'];
                    const isCartNavigation = cartKeywords.some(kw => normalizedText.includes(kw));
                    const hasZeroPrice = normalizedText.includes('0,00') || normalizedText.includes('0.00');
                    
                    if (isCartNavigation) score -= 100;  // Heavy penalty for cart/nav
                    if (hasZeroPrice) score -= 50;  // Penalty for empty cart prices
                    
                    if (hasProductKeywords) score += 15;  // Product-like text
                    if (hasSpecs) score += 20;  // Technical specs present
                    if (hasMarketingNoise) score -= 15;  // Marketing content
                    
                    // COMPLETE STRUCTURE bonus
                    if (c.has_price && c.has_link && c.has_image) score += 10;
                    
                    c.score = score;
                });
                
                dynamicCandidates.sort((a, b) => b.score - a.score);
                
                // HARD FILTER: Remove candidates with negative scores (cart/navigation)
                const validCandidates = dynamicCandidates.filter(c => c.score > 0);
                
                return {
                    found: validCandidates.length > 0,
                    candidates: validCandidates.slice(0, 3),
                    best: validCandidates[0] || null,
                    method: 'dynamic_detection',
                    filtered_out: dynamicCandidates.length - validCandidates.length
                };
            }
        """, page_type)
        
        self._log("Container Detection Results", result)
        
        if result["best"]:
            self.state["extraction_strategy"] = {
                "container_selector": result["best"]["selector"],
                "container_count": result["best"]["count"]
            }
        
        return result
    
    async def detect_field_locations(self, container_selector: str) -> Dict[str, Any]:
        """
        Step 3: Detect field locations within containers
        
        Analyze FIRST container to find where name/price/url are.
        Returns: field selectors relative to container
        """
        self._log("Step 3: Field Location Detection", f"Analyzing fields in {container_selector}...")
        
        result = await self.page.evaluate("""
            (containerSelector) => {
                const container = document.querySelector(containerSelector);
                if (!container) return { found: false };
                
                const fields = {
                    name: null,
                    price: null,
                    url: null
                };
                
                // Find name (likely in h2, h3, a, span with most text)
                const textElements = container.querySelectorAll('h1, h2, h3, h4, a, span, div[class*="name"], div[class*="title"]');
                let longestText = '';
                let nameElement = null;
                
                for (const el of textElements) {
                    const text = (el.innerText || '').trim();
                    if (text.length > longestText.length && text.length > 10 && text.length < 150) {
                        if (!/^\\d+[\\s\\d,\\.]*(?:zł|PLN)/.test(text)) {  // Not a price
                            longestText = text;
                            nameElement = el;
                        }
                    }
                }
                
                if (nameElement) {
                    fields.name = {
                        selector: nameElement.tagName.toLowerCase() + (nameElement.className ? '.' + nameElement.className.split(' ')[0] : ''),
                        sample: longestText.substring(0, 50)
                    };
                }
                
                // Find price (element with price pattern)
                const pricePattern = /(\\d+[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN)/i;
                const allElements = container.querySelectorAll('*');
                
                for (const el of allElements) {
                    const text = (el.innerText || '').trim();
                    const match = text.match(pricePattern);
                    if (match && text.length < 50) {  // Price text should be short
                        fields.price = {
                            selector: el.tagName.toLowerCase() + (el.className ? '.' + el.className.split(' ')[0] : ''),
                            sample: text,
                            value: parseFloat(match[1].replace(/\\s/g, '').replace(',', '.'))
                        };
                        break;
                    }
                }
                
                // Find URL (first meaningful link)
                const link = container.querySelector('a[href]');
                if (link && link.href) {
                    fields.url = {
                        selector: 'a[href]',
                        sample: link.href
                    };
                }
                
                return {
                    found: !!(fields.name || fields.price || fields.url),
                    fields: fields,
                    completeness: [fields.name, fields.price, fields.url].filter(f => f !== null).length / 3
                };
            }
        """, container_selector)
        
        self._log("Field Detection Results", result)
        
        if result["found"]:
            # Ensure extraction_strategy exists
            if self.state["extraction_strategy"] is None:
                self.state["extraction_strategy"] = {"container_selector": container_selector}
            self.state["extraction_strategy"]["fields"] = result["fields"]
        
        return result
    
    async def extract_with_strategy(self, strategy: Dict[str, Any], max_items: int = 50) -> List[Dict]:
        """
        Step 4: Extract data using detected strategy
        
        Now that we know WHERE data is, extract it efficiently.
        Returns: list of extracted products
        """
        self._log("Step 4: Data Extraction", f"Extracting up to {max_items} items using strategy...")
        
        result = await self.page.evaluate("""
            (args) => {
                const strategy = args.strategy;
                const maxItems = args.maxItems;
                const products = [];
                const containers = document.querySelectorAll(strategy.container_selector);
                
                for (let i = 0; i < Math.min(containers.length, maxItems); i++) {
                    const container = containers[i];
                    const product = {};
                    
                    // Extract name - try multiple approaches
                    if (strategy.fields.name) {
                        try {
                            const nameEl = container.querySelector(strategy.fields.name.selector);
                            if (nameEl) {
                                product.name = (nameEl.innerText || '').trim();
                            }
                        } catch (e) {}
                        
                        // Fallback: try any link or heading with substantial text
                        if (!product.name) {
                            const textElements = container.querySelectorAll('a, h1, h2, h3, h4, span, div');
                            for (const el of textElements) {
                                const text = (el.innerText || '').trim();
                                if (text.length > 10 && text.length < 200 && !/^\\d+[\\s\\d,\\.]*(?:zł|PLN)/.test(text)) {
                                    product.name = text;
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Extract price - robust pattern matching
                    if (strategy.fields.price) {
                        try {
                            const priceEl = container.querySelector(strategy.fields.price.selector);
                            if (priceEl) {
                                const text = (priceEl.innerText || '').trim();
                                const match = text.match(/(\\d+[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN)/i);
                                if (match) {
                                    product.price = parseFloat(match[1].replace(/\\s/g, '').replace(',', '.'));
                                }
                            }
                        } catch (e) {}
                        
                        // Fallback: search entire container text for price
                        if (!product.price) {
                            const containerText = container.innerText || '';
                            const pricePattern = /(\\d+[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN)/gi;
                            const matches = containerText.match(pricePattern);
                            if (matches && matches.length > 0) {
                                const firstPrice = matches[0];
                                const numMatch = firstPrice.match(/(\\d+[\\d\\s]*(?:[\\.,]\\d{2})?)/);
                                if (numMatch) {
                                    product.price = parseFloat(numMatch[1].replace(/\\s/g, '').replace(',', '.'));
                                }
                            }
                        }
                    }
                    
                    // Extract URL - find first meaningful link
                    if (strategy.fields.url) {
                        try {
                            const linkEl = container.querySelector(strategy.fields.url.selector);
                            if (linkEl && linkEl.href) {
                                product.url = linkEl.href;
                            }
                        } catch (e) {}
                        
                        // Fallback: find any product link
                        if (!product.url) {
                            const links = container.querySelectorAll('a[href]');
                            for (const link of links) {
                                if (link.href && link.href.includes('ceneo.pl') && /\\d{4,}/.test(link.href)) {
                                    product.url = link.href;
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Add if has at least name AND price (url optional)
                    if (product.name && product.price) {
                        products.push(product);
                    }
                }
                
                return products;
            }
        """, {"strategy": strategy, "maxItems": max_items})
        
        self._log("Extraction Results", {
            "count": len(result),
            "sample": result[:3] if result else []
        })
        
        return result
    
    def _validate_results(self, products: List[Dict], price_limit: Optional[float]) -> Dict[str, Any]:
        """
        Validate extracted results against instruction criteria.
        
        Checks:
        1. Products have required fields (name, price)
        2. Prices are within limit
        3. Data makes sense (not cart items, not duplicates)
        """
        issues = []
        valid_count = 0
        
        if not products:
            return {"valid": False, "issues": ["No products extracted"], "valid_count": 0}
        
        seen_names = set()
        cart_keywords = ["koszyk", "cart", "twój pc", "suma", "razem", "total"]
        
        for i, product in enumerate(products):
            name = str(product.get("name", "")).lower().strip()
            price = product.get("price")
            
            # Check for required fields
            if not name or len(name) < 3:
                issues.append(f"Product {i}: Missing or invalid name")
                continue
            
            if price is None:
                issues.append(f"Product {i}: Missing price")
                continue
            
            # Check for cart/navigation items
            if any(kw in name for kw in cart_keywords):
                issues.append(f"Product {i}: Appears to be cart/navigation item: '{name[:30]}'")
                continue
            
            # Check for duplicates
            if name in seen_names:
                issues.append(f"Product {i}: Duplicate name: '{name[:30]}'")
                continue
            seen_names.add(name)
            
            # Check price limit
            if price_limit and price > price_limit:
                issues.append(f"Product {i}: Price {price} exceeds limit {price_limit}")
                continue
            
            valid_count += 1
        
        return {
            "valid": valid_count > 0,
            "valid_count": valid_count,
            "total_count": len(products),
            "issues": issues[:10] if issues else None  # Limit to first 10 issues
        }
    
    def _extract_price_limit(self, instruction: str) -> Optional[float]:
        """Extract price limit from instruction"""
        import re
        
        # Patterns for price limits
        patterns = [
            r'under\s+(\d+)\s*(?:zł|PLN)',
            r'poniżej\s+(\d+)\s*(?:zł|PLN)',
            r'below\s+(\d+)\s*(?:zł|PLN)',
            r'do\s+(\d+)\s*(?:zł|PLN)',
            r'maksymalnie\s+(\d+)\s*(?:zł|PLN)',
            r'max\s+(\d+)\s*(?:zł|PLN)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction.lower())
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    async def _try_fallback_extraction(self, max_items: int, price_limit: Optional[float]) -> Dict[str, Any]:
        """
        Fallback extraction for table-based layouts (common in Polish e-commerce)
        
        This handles sites like gral.pl that use table layouts and image-based prices.
        """
        self._log("Fallback Extraction", "Trying table-based and link-based extraction...")
        
        result = await self.page.evaluate(f"""
            () => {{
                const products = [];
                const priceLimit = {price_limit or 'null'};
                const maxItems = {max_items};
                
                // Strategy 1: Find elements with product links (URLs ending in _12345.html)
                const productLinks = Array.from(document.querySelectorAll('a[href]'))
                    .filter(a => {{
                        const href = a.href || '';
                        // Match gral.pl style links: Name_12345.html
                        return /[A-Za-z]+.*_\\d+\\.html$/i.test(href) ||
                               /[_\\/]\\d{{4,}}\\.html?$/i.test(href);
                    }});
                
                // Group links by finding their common parent that contains product info
                const seenUrls = new Set();
                const seenNames = new Set();
                
                for (const link of productLinks) {{
                    if (products.length >= maxItems) break;
                    
                    const href = link.href;
                    if (seenUrls.has(href)) continue;
                    seenUrls.add(href);
                    
                    // Find the product container - go up until we find one with price indicators
                    let container = link;
                    for (let i = 0; i < 5 && container; i++) {{
                        const text = container.textContent || '';
                        const hasPrice = container.querySelector('img[src*="cb_"], img[src*="cn_"], img[src*="cena"]') ||
                                        /\\d+[,.]\\d{{2}}\\s*(?:zł|PLN)/i.test(text);
                        if (hasPrice && text.length > 30 && text.length < 1000) {{
                            break;
                        }}
                        container = container.parentElement;
                    }}
                    
                    if (!container) continue;
                    
                    // Extract name from link or container
                    let name = (link.textContent || link.title || '').trim();
                    if (!name || name.length < 5) {{
                        // Try to find name in container
                        const textNodes = Array.from(container.querySelectorAll('*'))
                            .map(el => (el.textContent || '').trim())
                            .filter(t => t.length > 10 && t.length < 150);
                        if (textNodes.length > 0) {{
                            name = textNodes[0];
                        }}
                    }}
                    
                    // Skip if name already seen (duplicate)
                    if (seenNames.has(name)) continue;
                    seenNames.add(name);
                    
                    // Extract price from text or look for price images
                    let price = null;
                    const containerText = container.textContent || '';
                    const priceMatch = containerText.match(/(\\d+[\\s\\d]*(?:[,.]\\d{{2}})?)\\s*(?:zł|PLN)/i);
                    if (priceMatch) {{
                        price = parseFloat(priceMatch[1].replace(/\\s/g, '').replace(',', '.'));
                    }}
                    
                    // Skip if price exceeds limit
                    if (priceLimit && price && price > priceLimit) {{
                        continue;
                    }}
                    
                    // Get image
                    const img = container.querySelector('img[src]:not([src*="cb_"]):not([src*="cn_"])');
                    const image = img ? img.src : null;
                    
                    products.push({{
                        name: name,
                        price: price,
                        url: href,
                        image: image,
                        extraction_method: 'fallback_link_based'
                    }});
                }}
                
                return products;
            }}
        """)
        
        if result and len(result) > 0:
            self._log("Fallback Extraction Results", {"count": len(result)})
            return {
                "products": result,
                "extraction_method": "fallback_table_based",
                "metadata": self.state
            }
        
        return {"products": [], "reason": "Fallback extraction found no products"}
    
    async def run(self, max_items: int = 50) -> Dict[str, Any]:
        """
        Run full iterative extraction pipeline
        
        Returns: {products: [...], metadata: {...}}
        """
        if self.run_logger:
            self.run_logger.log_text("\n🔄 ═══ ITERATIVE EXTRACTOR ═══\n")
        
        # Extract price limit from instruction
        price_limit = self._extract_price_limit(self.instruction)
        if price_limit and self.run_logger:
            self.run_logger.log_text(f"💰 Price limit detected: {price_limit} zł")
        
        # Step 1: Quick check
        quick_check = await self.quick_page_check()
        
        page_type = quick_check.get("page_type") if quick_check else "unknown"
        extractable_types = ["product_listing", "category", "single_product"]
        
        needs_nav_types = ["homepage", "homepage_shop", "category_index"]
        
        if page_type not in extractable_types:
            # Provide specific feedback for different page types
            real_products = quick_check.get("real_product_containers", 0)
            
            if page_type in ["homepage_shop", "category_index"]:
                reason = f"Navigation page ({page_type}) - found {real_products} potential products but need to navigate to a category. " \
                         f"Links found: {quick_check.get('product_link_count', 0)}. " \
                         f"Try clicking on a category link like 'Monitory', 'Drukarki', etc."
            elif page_type == "homepage":
                reason = "Homepage detected - prices visible are from cart/header, not products. Navigate to a product category first."
            elif page_type == "other":
                reason = "Page does not appear to contain products. Try navigating to a product listing or category page."
            else:
                reason = f"Page type '{page_type}' not suitable for product extraction"
            
            if self.run_logger:
                self.run_logger.log_text(f"⚠️ {reason}")
            
            return {
                "products": [],
                "reason": reason,
                "page_type": page_type,
                "needs_navigation": page_type in needs_nav_types,
                "suggested_action": "Navigate to a product category page" if page_type in needs_nav_types else None,
                "metadata": self.state
            }
        
        # Step 2: Detect containers
        containers = await self.detect_container_structure(quick_check["page_type"])
        
        if not containers.get("best"):
            # Fallback: try table-based or generic extraction if page has products
            real_products = quick_check.get("real_product_containers", 0)
            if real_products >= 3:
                if self.run_logger:
                    self.run_logger.log_text(f"⚠️ Container detection failed but {real_products} products detected - trying fallback extraction")
                
                # Try table-based fallback for Polish e-commerce sites
                fallback_result = await self._try_fallback_extraction(max_items, price_limit)
                if fallback_result.get("products"):
                    return fallback_result
            
            return {
                "products": [],
                "reason": "No product containers found",
                "metadata": self.state
            }
        
        # Step 3: Detect fields
        fields = await self.detect_field_locations(containers["best"]["selector"])
        
        if not fields.get("found") or fields.get("completeness", 0) < 0.5:
            return {
                "products": [],
                "reason": f"Insufficient field detection (completeness: {fields.get('completeness', 0):.0%})",
                "metadata": self.state
            }
        
        # Step 4: Extract data
        products = await self.extract_with_strategy(self.state["extraction_strategy"], max_items)
        
        # Step 5: Apply multi-criteria filtering (if available and has products)
        if products and self.use_dynamic_detection and self.multi_filter:
            try:
                if self.run_logger:
                    self.run_logger.log_text("\n🎯 ═══ MULTI-CRITERIA FILTERING ═══\n")
                
                filter_result = await self.multi_filter.filter_products(
                    products=products,
                    instruction=self.instruction,
                    use_llm=True
                )
                
                if self.run_logger:
                    self.run_logger.log_text(f"📊 Filtering Report")
                    self.run_logger.log_code("json", json.dumps({
                        "original_count": filter_result['original_count'],
                        "filtered_count": filter_result['filtered_count'],
                        "criteria_summary": filter_result.get('criteria_summary', 'N/A'),
                        "stages": len(filter_result.get('stages', []))
                    }, indent=2, ensure_ascii=False))
                
                products = filter_result['filtered_products']
                
                # Add filtering metadata to state
                self.state['filtering_applied'] = True
                self.state['filtering_stages'] = filter_result.get('stages', [])
                
            except Exception as e:
                if self.run_logger:
                    self.run_logger.log_text(f"⚠️ Multi-criteria filtering failed: {e}")
                # Continue with unfiltered products on error
        
        # Legacy price filter (fallback if multi-criteria not used)
        elif price_limit is not None and products:
            original_count = len(products)
            products = [p for p in products if p.get("price") and p["price"] <= price_limit]
            filtered_count = len(products)
            
            if self.run_logger:
                self.run_logger.log_text(
                    f"💰 Price Filter Applied: {original_count} → {filtered_count} products "
                    f"(removed {original_count - filtered_count} above {price_limit} zł)"
                )
        
        # Step 6: Validate results against instruction
        validation = self._validate_results(products, price_limit)
        if self.run_logger and validation.get("issues"):
            self.run_logger.log_text(f"⚠️ Validation Issues: {validation['issues']}")
        
        # Step 7: Screenshot for documentation
        screenshot_path = None
        if self.run_logger:
            try:
                import time
                screenshot_path = f"screenshots/extraction_{int(time.time())}.png"
                await self.page.screenshot(path=screenshot_path)
                
                self.run_logger.log_text("\n## 📸 Extraction Screenshot\n")
                self.run_logger.log_text(f"> `streamware.page.screenshot(path=\"{screenshot_path}\")`")
                self.run_logger.log_text(f"\n![Extraction result](../{screenshot_path})\n")
            except Exception as e:
                if self.run_logger:
                    self.run_logger.log_text(f"⚠️ Screenshot failed: {e}")
        
        return {
            "products": products,
            "count": len(products),
            "reason": "Success" if products else "No products matched criteria",
            "metadata": self.state,
            "price_limit": price_limit,
            "screenshot": screenshot_path
        }


async def iterative_extract(instruction: str, page, llm, run_logger=None, use_dynamic_detection=True) -> Optional[Dict[str, Any]]:
    """
    Convenience function for iterative extraction
    
    Usage:
        result = await iterative_extract("Find products under 150zł", page, llm, logger)
    
    Args:
        instruction: User's extraction instruction
        page: Playwright page object
        llm: LLM client
        run_logger: Logger instance
        use_dynamic_detection: Enable DynamicContainerDetector + MultiCriteriaFilter (default: True)
    """
    extractor = IterativeExtractor(page, llm, instruction, run_logger, use_dynamic_detection=use_dynamic_detection)
    return await extractor.run()
