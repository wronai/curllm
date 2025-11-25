"""
Iterative Extractor - Small Atomic DOM Queries with Full Logging

Instead of sending entire DOM tree to LLM, we:
1. Quick check: Does page have products? (fast)
2. Structure analysis: What containers? (targeted)
3. Field detection: Which fields exist? (specific)
4. Data extraction: Extract values (minimal)

Each step logs details and makes early decisions.
"""

import json
from typing import Dict, List, Optional, Any


class IterativeExtractor:
    """Iterative extraction with atomic DOM queries"""
    
    def __init__(self, page, llm, instruction, run_logger=None):
        self.page = page
        self.llm = llm
        self.instruction = instruction
        self.run_logger = run_logger
        self.state = {
            "checks_performed": [],
            "decisions": [],
            "extraction_strategy": None
        }
    
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
                    total_links: document.links.length,
                    page_type: 'unknown'
                };
                
                // Check for price patterns (fast regex)
                const pricePattern = /(\\d+[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN|€|\\$|USD|EUR)/i;
                const bodyText = document.body?.innerText || '';
                const priceMatches = bodyText.match(new RegExp(pricePattern, 'g'));
                
                if (priceMatches) {
                    indicators.has_prices = true;
                    indicators.price_count = priceMatches.length;
                }
                
                // Check for product-like links (contains numbers = product IDs)
                const productLinkPattern = /\\/\\d{4,}/;
                let productLinks = 0;
                for (const link of document.links) {
                    if (productLinkPattern.test(link.pathname)) {
                        productLinks++;
                    }
                }
                indicators.product_link_count = productLinks;
                indicators.has_product_links = productLinks > 0;
                
                // Check for list structure
                const listSelectors = [
                    '.product-list', '.products', '[data-product]',
                    '.cat-prod-row', '.offers', '.items-list'
                ];
                for (const sel of listSelectors) {
                    if (document.querySelector(sel)) {
                        indicators.has_list_structure = true;
                        break;
                    }
                }
                
                // Determine page type
                if (indicators.has_prices && indicators.has_product_links) {
                    indicators.page_type = 'product_listing';
                } else if (indicators.price_count > 0) {
                    indicators.page_type = 'single_product';
                } else if (indicators.product_link_count > 5) {
                    indicators.page_type = 'category';
                } else {
                    indicators.page_type = 'other';
                }
                
                return indicators;
            }
        """)
        
        self._log("Quick Check Results", result)
        
        decision = {
            "should_continue": result["page_type"] in ["product_listing", "category"],
            "reason": f"Page type: {result['page_type']}, prices: {result['price_count']}, product links: {result['product_link_count']}"
        }
        self.state["decisions"].append(decision)
        
        return result
    
    async def detect_container_structure(self, page_type: str) -> Dict[str, Any]:
        """
        Step 2: Detect container structure
        
        Find the PATTERN of product containers without extracting data.
        Returns: container selector, count, sample structure
        """
        self._log("Step 2: Container Structure Detection", f"Looking for {page_type} containers...")
        
        result = await self.page.evaluate("""
            (pageType) => {
                const candidates = [];
                
                // Known product container patterns
                const patterns = [
                    '.product-box', '.product-item', '.product-card',
                    '[data-product-id]', '[data-offer-id]',
                    'article[itemtype*="Product"]',
                    '.cat-prod-row', '.offer-item'
                ];
                
                for (const selector of patterns) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length >= 3) {  // At least 3 = likely a list
                        // Get structure of first element
                        const first = elements[0];
                        const structure = {
                            selector: selector,
                            count: elements.length,
                            has_link: !!first.querySelector('a[href]'),
                            has_price: /\\d+[\\d\\s]*(?:[\\.,]\\d{2})?\\s*(?:zł|PLN)/i.test(first.innerText || ''),
                            has_image: !!first.querySelector('img'),
                            classes: first.className,
                            sample_text: (first.innerText || '').substring(0, 100)
                        };
                        
                        candidates.push(structure);
                    }
                }
                
                // Sort by count (more = better)
                candidates.sort((a, b) => b.count - a.count);
                
                return {
                    found: candidates.length > 0,
                    candidates: candidates.slice(0, 3),  // Top 3
                    best: candidates[0] || null
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
                    
                    // Add if has at least name OR (price AND url)
                    if ((product.name && product.url) || (product.price && product.url)) {
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
        
        if not quick_check or quick_check.get("page_type") not in ["product_listing", "category", "single_product"]:
            return {
                "products": [],
                "reason": "Page type not suitable for extraction",
                "metadata": self.state
            }
        
        # Step 2: Detect containers
        containers = await self.detect_container_structure(quick_check["page_type"])
        
        if not containers.get("best"):
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
        
        # Apply price filter if specified
        if price_limit is not None and products:
            original_count = len(products)
            products = [p for p in products if p.get("price") and p["price"] <= price_limit]
            filtered_count = len(products)
            
            if self.run_logger:
                self.run_logger.log_text(
                    f"💰 Price Filter Applied: {original_count} → {filtered_count} products "
                    f"(removed {original_count - filtered_count} above {price_limit} zł)"
                )
        
        return {
            "products": products,
            "count": len(products),
            "reason": "Success" if products else "No products matched criteria",
            "metadata": self.state,
            "price_limit": price_limit
        }


async def iterative_extract(instruction: str, page, llm, run_logger=None) -> Optional[Dict[str, Any]]:
    """
    Convenience function for iterative extraction
    
    Usage:
        result = await iterative_extract("Find products under 150zł", page, llm, logger)
    """
    extractor = IterativeExtractor(page, llm, instruction, run_logger)
    return await extractor.run()
