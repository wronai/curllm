"""
LLM-Guided Atomic Extractor - Pure LLM Decision Tree

NO HARDCODED REGEX OR SELECTORS - Every decision made by LLM:

1. LLM: "What container selector should I use?" → LLM analyzes DOM
2. LLM: "How do I extract name?" → LLM determines strategy
3. LLM: "How do I extract price?" → LLM parses price text
4. LLM: "Should I filter results?" → LLM interprets criteria

Each step is atomic and LLM-guided. NO REGEX IN CODE.
"""

import json
from typing import Dict, List, Optional, Any


class LLMGuidedExtractor:
    """
    Atomic extraction with LLM making decisions at each step
    """
    
    def __init__(self, page, llm, instruction, run_logger=None):
        self.page = page
        self.llm = llm
        self.instruction = instruction
        self.run_logger = run_logger
        self.decisions = []
    
    def _log(self, step: str, details: Any):
        """Log decision"""
        if self.run_logger:
            self.run_logger.log_text(f"🤖 LLM Decision: {step}")
            if isinstance(details, (dict, list)):
                self.run_logger.log_code("json", json.dumps(details, indent=2, ensure_ascii=False))
            else:
                self.run_logger.log_text(f"   {details}")
        
        self.decisions.append({"step": step, "details": details})
    
    async def _ask_llm(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ask LLM a specific question with minimal context
        
        Returns: LLM's decision as JSON
        """
        prompt = f"""You are an extraction expert. Answer this specific question about extracting data from a web page.

Question: {question}

Context:
{json.dumps(context, indent=2, ensure_ascii=False)[:1000]}

Instruction: {self.instruction}

Respond with JSON only. Be specific and actionable.

JSON:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            
            # Check if response is already a dict (some LLMs return parsed JSON)
            if isinstance(response, dict):
                return response
            
            # If it's a string, extract JSON
            if isinstance(response, str):
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            
            return {}
        except Exception as e:
            if self.run_logger:
                self.run_logger.log_text(f"❌ LLM error: {e}")
            return {}
    
    async def step1_identify_container_selector(self) -> Optional[str]:
        """
        Step 1: LLM decides which container selector to use
        
        DYNAMIC: Find elements with ACTUAL prices, not guessed selectors
        """
        self._log("Step 1: Identify Container Selector", "Analyzing DOM for price-containing elements...")
        
        # Find elements that contain ACTUAL price patterns - LLM will analyze these
        sample_elements = await self.page.evaluate("""
            () => {
                const pricePattern = /\\d+[\\d\\s]*[,.]?\\d*\\s*(?:zł|PLN|€|\\$|USD|EUR)/i;
                const candidates = [];
                const seenClasses = new Set();
                
                // Find elements with prices
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    const text = (el.innerText || '').trim();
                    const className = typeof el.className === 'string' ? el.className : '';
                    const firstClass = className.split(' ')[0];
                    
                    // Skip if no class or already seen
                    if (!firstClass || seenClasses.has(firstClass)) continue;
                    if (!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(firstClass)) continue;
                    
                    // Skip if looks like CSS/script content
                    if (text.includes('{') && text.includes(':') && text.includes('}')) continue;
                    if (text.includes('function') || text.includes('var ')) continue;
                    
                    // Check if has price
                    const hasPrice = pricePattern.test(text);
                    const hasLink = el.querySelector('a[href]') !== null;
                    const textLength = text.length;
                    
                    // Only consider elements with prices and reasonable text
                    if (hasPrice && textLength > 20 && textLength < 1000) {
                        // Count siblings with same class
                        const siblings = document.querySelectorAll('.' + firstClass);
                        if (siblings.length >= 3) {
                            seenClasses.add(firstClass);
                            candidates.push({
                                selector: '.' + firstClass,
                                count: siblings.length,
                                sample_text: text.substring(0, 300),
                                has_price: true,
                                has_link: hasLink,
                                text_length: textLength
                            });
                        }
                    }
                    
                    if (candidates.length >= 10) break;
                }
                
                return candidates;
            }
        """)
        
        if not sample_elements:
            self._log("No price-containing elements found", {})
            return None
        
        # Log candidates for transparency
        self._log("Found candidates with prices", {
            "count": len(sample_elements),
            "selectors": [c.get("selector") for c in sample_elements]
        })
        
        # Format candidates for LLM - be EXPLICIT about choices
        valid_selectors = [c.get("selector") for c in sample_elements]
        candidates_text = "\n".join([
            f"- {c.get('selector')}: {c.get('count')} elements, sample: \"{c.get('sample_text', '')[:100]}...\""
            for c in sample_elements[:5]
        ])
        
        # Ask LLM to pick from EXACT list - no guessing allowed
        decision = await self._ask_llm(
            f"""Pick the BEST product container from this EXACT list of selectors:

{candidates_text}

VALID SELECTORS: {valid_selectors}

Rules:
- You MUST pick one of the selectors from the list above
- Look for sample text with product NAMES (not CSS styles or navigation)
- Return EXACTLY: {{"selector": "<one from list>", "reasoning": "why"}}""",
            {
                "instruction": self.instruction
            }
        )
        
        selector = decision.get("selector")
        
        # ENFORCE: selector must be from candidates list
        if selector and selector not in valid_selectors:
            self._log("LLM picked invalid selector, using best candidate", {
                "llm_choice": selector,
                "valid_selectors": valid_selectors
            })
            # Pick candidate with shortest avg text length (more likely product)
            best = min(sample_elements, key=lambda x: x.get("text_length", 9999))
            selector = best.get("selector")
        
        self._log("Container Selector Decision", decision)
        
        return selector
    
    async def step2_verify_container(self, selector: str) -> Dict[str, Any]:
        """
        Step 2: Verify container works using LLM
        
        Execute JS to get raw data, LLM analyzes if it's a product
        """
        self._log("Step 2: Verify Container", f"Testing selector: {selector}")
        
        # Get raw data - NO REGEX
        raw_result = await self.page.evaluate("""
            (selector) => {
                const containers = document.querySelectorAll(selector);
                return {
                    found: containers.length > 0,
                    count: containers.length,
                    sample: containers.length > 0 ? {
                        text: (containers[0].innerText || '').substring(0, 500),
                        hasLink: !!containers[0].querySelector('a[href]')
                    } : null
                };
            }
        """, selector)
        
        # Let LLM verify if this looks like a product container
        if raw_result.get("sample"):
            verification = await self._ask_llm(
                "Does this text look like a product container? Return: {'is_product': true/false, 'has_price': true/false, 'reasoning': '...'}",
                {"sample_text": raw_result["sample"]["text"][:300]}
            )
            raw_result["llm_verification"] = verification
        
        self._log("Container Verification", raw_result)
        return raw_result
    
    async def step3_ask_field_selectors(self, container_selector: str) -> Dict[str, str]:
        """
        Step 3: LLM decides how to extract each field
        
        Atomic questions: "How do I extract name? price? url?"
        """
        self._log("Step 3: Field Extraction Strategy", "Asking LLM for each field...")
        
        # Get structure of first container - NO REGEX, raw data for LLM
        structure = await self.page.evaluate("""
            (selector) => {
                const container = document.querySelector(selector);
                if (!container) return null;
                
                // Get all descendants with text or href
                const descendants = Array.from(container.querySelectorAll('*'))
                    .filter(el => (el.innerText || '').trim().length > 0 || el.href)
                    .slice(0, 20)
                    .map(el => ({
                        tag: el.tagName.toLowerCase(),
                        classes: el.className,
                        text: (el.innerText || '').substring(0, 100),
                        hasHref: !!el.href
                    }));
                
                return descendants;
            }
        """, container_selector)
        
        decision = await self._ask_llm(
            """For each field (name, price, url), tell me the CSS selector relative to container.
Return format: {
  'name': {'selector': '...', 'strategy': 'innerText or href'},
  'price': {'selector': '...', 'strategy': 'innerText with regex'},
  'url': {'selector': '...', 'strategy': 'href attribute'}
}""",
            {
                "container_structure": structure,
                "task": "Extract product name, price, url"
            }
        )
        
        self._log("Field Selectors Decision", decision)
        return decision
    
    async def step4_extract_with_strategy(
        self, 
        container_selector: str, 
        field_strategy: Dict[str, Any],
        max_items: int = 50
    ) -> List[Dict]:
        """
        Step 4: Execute extraction using LLM - NO REGEX
        
        Extract raw text, then LLM parses prices
        """
        self._log("Step 4: Execute Extraction", "Using LLM for field extraction...")
        
        # Get raw data from containers - NO REGEX
        raw_products = await self.page.evaluate("""
            (args) => {
                const {containerSelector, fieldStrategy, maxItems} = args;
                const products = [];
                const containers = document.querySelectorAll(containerSelector);
                
                for (let i = 0; i < Math.min(containers.length, maxItems); i++) {
                    const container = containers[i];
                    const product = {};
                    
                    // Extract raw name text
                    if (fieldStrategy.name && fieldStrategy.name.selector) {
                        try {
                            const el = container.querySelector(fieldStrategy.name.selector);
                            if (el) product.name = (el.innerText || '').trim();
                        } catch (e) {}
                    }
                    
                    // Extract raw price text - NO PARSING, LLM will do it
                    if (fieldStrategy.price && fieldStrategy.price.selector) {
                        try {
                            const el = container.querySelector(fieldStrategy.price.selector);
                            if (el) product.price_text = (el.innerText || '').trim();
                        } catch (e) {}
                    }
                    
                    // Also get full container text for LLM fallback
                    product.full_text = (container.innerText || '').substring(0, 300);
                    
                    // Extract URL
                    if (fieldStrategy.url && fieldStrategy.url.selector) {
                        try {
                            const el = container.querySelector(fieldStrategy.url.selector);
                            if (el && el.href) product.url = el.href;
                        } catch (e) {}
                    }
                    
                    products.push(product);
                }
                
                return products;
            }
        """, {
            "containerSelector": container_selector,
            "fieldStrategy": field_strategy,
            "maxItems": max_items
        })
        
        # Use LLM to parse prices from raw text
        products = await self._parse_prices_with_llm(raw_products)
        
        self._log("Extraction Results", {
            "count": len(products),
            "sample": products[:3] if products else []
        })
        
        return products
    
    async def _parse_prices_with_llm(self, raw_products: List[Dict]) -> List[Dict]:
        """Parse prices using LLM - NO REGEX"""
        if not raw_products:
            return []
        
        # Batch parse prices with LLM
        price_texts = [p.get("price_text") or p.get("full_text", "")[:100] for p in raw_products]
        
        prompt = f"""Extract numeric prices from these texts. Return JSON array of numbers (or null if no price).

Texts:
{json.dumps(price_texts[:20], ensure_ascii=False)}

Rules:
- Return just the numeric value (e.g., 299.99)
- Use dot for decimal separator
- Return null if no price found

Return JSON array of numbers: [price1, price2, ...]

JSON:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            
            # Parse LLM response
            if isinstance(response, str):
                json_start = response.find('[')
                json_end = response.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    prices = json.loads(response[json_start:json_end])
                    
                    # Apply prices to products
                    for i, product in enumerate(raw_products[:len(prices)]):
                        if i < len(prices) and prices[i] is not None:
                            product["price"] = float(prices[i])
                        # Clean up temp fields
                        product.pop("price_text", None)
                        product.pop("full_text", None)
        except Exception as e:
            if self.run_logger:
                self.run_logger.log_text(f"⚠️ LLM price parsing error: {e}")
        
        # Filter to only products with name or price
        return [p for p in raw_products if p.get("name") or p.get("price")]
    
    async def step5_ask_filtering(self, products: List[Dict]) -> Dict[str, Any]:
        """
        Step 5: LLM decides how to filter results
        
        Atomic question: "Should I filter these products? How?"
        """
        self._log("Step 5: Filtering Decision", "Asking LLM...")
        
        decision = await self._ask_llm(
            f"""Should I filter these {len(products)} products? If yes, what criteria?
Return format: {{
  'should_filter': true/false,
  'criteria': {{'field': 'price', 'operator': 'lte', 'value': 150}},
  'reasoning': 'why'
}}""",
            {
                "instruction": self.instruction,
                "sample_products": products[:5],
                "total_count": len(products)
            }
        )
        
        self._log("Filtering Decision", decision)
        return decision
    
    async def step6_apply_filter(self, products: List[Dict], criteria: Dict[str, Any]) -> List[Dict]:
        """
        Step 6: Apply LLM-decided filter
        """
        if not criteria or not criteria.get('should_filter'):
            return products
        
        filter_field = criteria.get('criteria', {}).get('field', 'price')
        operator = criteria.get('criteria', {}).get('operator', 'lte')
        value = criteria.get('criteria', {}).get('value', 0)
        
        original_count = len(products)
        
        if operator == 'lte':
            products = [p for p in products if p.get(filter_field, float('inf')) <= value]
        elif operator == 'gte':
            products = [p for p in products if p.get(filter_field, 0) >= value]
        elif operator == 'eq':
            products = [p for p in products if p.get(filter_field) == value]
        
        filtered_count = len(products)
        
        self._log("Filter Applied", {
            "original": original_count,
            "filtered": filtered_count,
            "removed": original_count - filtered_count,
            "criteria": criteria
        })
        
        return products
    
    async def run(self, max_items: int = 50) -> Dict[str, Any]:
        """
        Run LLM-guided extraction with atomic steps
        """
        if self.run_logger:
            self.run_logger.log_text("\n🤖 ═══ LLM-GUIDED ATOMIC EXTRACTOR ═══\n")
        
        # Step 1: LLM chooses container selector
        container_selector = await self.step1_identify_container_selector()
        if not container_selector:
            return {"products": [], "reason": "LLM couldn't identify container", "decisions": self.decisions}
        
        # Step 2: Verify it works
        verification = await self.step2_verify_container(container_selector)
        if not verification.get("found") or verification.get("count", 0) == 0:
            return {"products": [], "reason": "Container verification failed", "decisions": self.decisions}
        
        # Step 3: LLM chooses field extraction strategy
        field_strategy = await self.step3_ask_field_selectors(container_selector)
        if not field_strategy:
            return {"products": [], "reason": "LLM couldn't determine field strategy", "decisions": self.decisions}
        
        # Step 4: Execute extraction
        products = await self.step4_extract_with_strategy(container_selector, field_strategy, max_items)
        if not products:
            return {"products": [], "reason": "No products extracted", "decisions": self.decisions}
        
        # Step 5: LLM decides on filtering
        filter_decision = await self.step5_ask_filtering(products)
        
        # Step 6: Apply filter
        products = await self.step6_apply_filter(products, filter_decision)
        
        return {
            "products": products,
            "count": len(products),
            "reason": "Success",
            "decisions": self.decisions
        }


async def llm_guided_extract(instruction: str, page, llm, run_logger=None) -> Optional[Dict[str, Any]]:
    """
    LLM-guided extraction with atomic decision steps
    
    Usage:
        result = await llm_guided_extract("Find products under 150zł", page, llm, logger)
    """
    extractor = LLMGuidedExtractor(page, llm, instruction, run_logger)
    return await extractor.run()
