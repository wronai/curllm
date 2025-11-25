"""
LLM-Guided Atomic Extractor - Decision Tree with Small Steps

Instead of monolithic heuristics, LLM makes decisions at each atomic step:

1. LLM: "What container selector should I use?" → Dynamically detected from DOM
2. LLM: "How do I extract name?" → Analyze text patterns in containers
3. LLM: "How do I extract price?" → Detect price patterns dynamically
4. Execute extraction with LLM-chosen strategy
5. LLM: "Should I filter results?" → Yes, price < threshold

Each step is small, atomic, and LLM-guided.
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
        
        Small atomic question: "What selector contains product items?"
        """
        self._log("Step 1: Identify Container Selector", "Asking LLM...")
        
        # Get sample HTML structure
        sample_html = await self.page.evaluate("""
            () => {
                const body = document.body;
                // Get first 50 elements with classes
                const elements = Array.from(document.querySelectorAll('[class]')).slice(0, 50);
                return elements.map(el => ({
                    tag: el.tagName.toLowerCase(),
                    classes: el.className,
                    hasPrice: /\\d+[\\.,]\\d{2}\\s*(?:zł|PLN)/i.test(el.innerText || ''),
                    hasLink: !!el.querySelector('a[href]'),
                    textLength: (el.innerText || '').length
                }));
            }
        """)
        
        decision = await self._ask_llm(
            "What CSS selector should I use to find product containers? Return format: {'selector': '.class-name', 'reasoning': 'why'}",
            {
                "sample_elements": sample_html[:20],
                "task": "Find products with prices"
            }
        )
        
        selector = decision.get("selector")
        self._log("Container Selector Decision", decision)
        
        return selector
    
    async def step2_verify_container(self, selector: str) -> Dict[str, Any]:
        """
        Step 2: Verify container works
        
        Execute JS to check if selector finds items
        """
        self._log("Step 2: Verify Container", f"Testing selector: {selector}")
        
        result = await self.page.evaluate(f"""
            (selector) => {{
                const containers = document.querySelectorAll(selector);
                return {{
                    found: containers.length > 0,
                    count: containers.length,
                    sample: containers.length > 0 ? {{
                        hasText: !!(containers[0].innerText || '').trim(),
                        hasPrice: /\\d+[\\.,]\\d{{2}}\\s*(?:zł|PLN)/i.test(containers[0].innerText || ''),
                        hasLink: !!containers[0].querySelector('a[href]')
                    }} : null
                }};
            }}
        """, selector)
        
        self._log("Container Verification", result)
        return result
    
    async def step3_ask_field_selectors(self, container_selector: str) -> Dict[str, str]:
        """
        Step 3: LLM decides how to extract each field
        
        Atomic questions: "How do I extract name? price? url?"
        """
        self._log("Step 3: Field Extraction Strategy", "Asking LLM for each field...")
        
        # Get structure of first container
        structure = await self.page.evaluate(f"""
            (selector) => {{
                const container = document.querySelector(selector);
                if (!container) return null;
                
                // Get all descendants with text or href
                const descendants = Array.from(container.querySelectorAll('*'))
                    .filter(el => (el.innerText || '').trim().length > 0 || el.href)
                    .slice(0, 20)
                    .map(el => ({{
                        tag: el.tagName.toLowerCase(),
                        classes: el.className,
                        text: (el.innerText || '').substring(0, 100),
                        hasHref: !!el.href,
                        hasPrice: /\\d+[\\.,]\\d{{2}}\\s*(?:zł|PLN)/i.test(el.innerText || '')
                    }}));
                
                return descendants;
            }}
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
        Step 4: Execute extraction using LLM-decided strategy
        """
        self._log("Step 4: Execute Extraction", f"Using strategy from LLM...")
        
        # Build JS code from LLM strategy
        products = await self.page.evaluate("""
            (args) => {
                const {containerSelector, fieldStrategy, maxItems} = args;
                const products = [];
                const containers = document.querySelectorAll(containerSelector);
                
                for (let i = 0; i < Math.min(containers.length, maxItems); i++) {
                    const container = containers[i];
                    const product = {};
                    
                    // Extract name
                    if (fieldStrategy.name && fieldStrategy.name.selector) {
                        try {
                            const el = container.querySelector(fieldStrategy.name.selector);
                            if (el) product.name = (el.innerText || '').trim();
                        } catch (e) {}
                    }
                    
                    // Extract price
                    if (fieldStrategy.price && fieldStrategy.price.selector) {
                        try {
                            const el = container.querySelector(fieldStrategy.price.selector);
                            if (el) {
                                const text = (el.innerText || '').trim();
                                const match = text.match(/(\\d+[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN)/i);
                                if (match) {
                                    product.price = parseFloat(match[1].replace(/\\s/g, '').replace(',', '.'));
                                }
                            }
                        } catch (e) {}
                    }
                    
                    // Extract URL
                    if (fieldStrategy.url && fieldStrategy.url.selector) {
                        try {
                            const el = container.querySelector(fieldStrategy.url.selector);
                            if (el && el.href) product.url = el.href;
                        } catch (e) {}
                    }
                    
                    // Add if valid
                    if (product.name || product.price) {
                        products.push(product);
                    }
                }
                
                return products;
            }
        """, {
            "containerSelector": container_selector,
            "fieldStrategy": field_strategy,
            "maxItems": max_items
        })
        
        self._log("Extraction Results", {
            "count": len(products),
            "sample": products[:3] if products else []
        })
        
        return products
    
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
