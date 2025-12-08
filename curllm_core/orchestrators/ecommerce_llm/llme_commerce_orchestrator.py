from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from curllm_core.llm_dsl import AtomicFunctions

from .checkout_step import CheckoutStep
from .shopping_intent import ShoppingIntent
from .shopping_result import ShoppingResult

class LLMECommerceOrchestrator:
    """
    LLM-driven e-commerce orchestrator.
    
    NO HARDCODED:
    - Product selectors
    - Cart button texts
    - Keyword lists
    - Payment method patterns
    """
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        self.atoms = None
        
        if page and llm:
            self.atoms = AtomicFunctions(page=page, llm=llm)
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> ShoppingResult:
        """Execute e-commerce workflow using LLM."""
        self._log("🛒 LLM E-COMMERCE ORCHESTRATOR", "header")
        
        if not self.atoms:
            return ShoppingResult(
                success=False, action='error',
                error="No LLM/page available"
            )
        
        try:
            # Phase 1: LLM parses shopping intent
            intent = await self._parse_intent_llm(instruction)
            self._log(f"Intent: {intent.action} (confidence: {intent.confidence:.0%})")
            
            # Phase 2: Execute action
            if intent.action == 'search':
                return await self._search_products_llm(intent.query)
            elif intent.action == 'add_to_cart':
                return await self._add_to_cart_llm()
            elif intent.action == 'checkout':
                return await self._process_checkout_llm(intent)
            else:
                # Browse/analyze
                cart = await self._get_cart_llm()
                return ShoppingResult(
                    success=True, action='browse',
                    cart=cart,
                )
                
        except Exception as e:
            self._log(f"Error: {e}", "error")
            return ShoppingResult(
                success=False, action='error',
                error=str(e)
            )
    
    async def _parse_intent_llm(self, instruction: str) -> ShoppingIntent:
        """Parse shopping intent using LLM."""
        if not self.llm:
            return ShoppingIntent(
                action='browse', query=None,
                payment_method=None, shipping={},
                confidence=0.3,
            )
        
        prompt = f"""Parse this e-commerce instruction.

Instruction: "{instruction}"

Return JSON:
{{
    "action": "search|add_to_cart|checkout|browse",
    "query": "search query if searching",
    "payment_method": "detected payment method if any",
    "shipping": {{"name": "", "address": "", "city": "", "zip": "", "phone": ""}},
    "confidence": 0.0-1.0
}}

Return ONLY valid JSON."""

        try:
            response = await self.llm.agenerate([prompt])
            answer = response.generations[0][0].text.strip()
            
            import json
            import re
            if '```' in answer:
                answer = re.sub(r'```\w*\n?', '', answer)
            
            data = json.loads(answer)
            return ShoppingIntent(
                action=data.get('action', 'browse'),
                query=data.get('query'),
                payment_method=data.get('payment_method'),
                shipping=data.get('shipping', {}),
                confidence=data.get('confidence', 0.7),
            )
        except Exception:
            return ShoppingIntent(
                action='browse', query=None,
                payment_method=None, shipping={},
                confidence=0.3,
            )
    
    async def _search_products_llm(self, query: str) -> ShoppingResult:
        """Search for products using LLM to find search input."""
        if not query:
            return ShoppingResult(
                success=False, action='search',
                error="No search query"
            )
        
        # LLM finds search input
        search_input = await self.atoms.find_input_by_context(
            "search input field for finding products"
        )
        
        if search_input.success and search_input.data:
            selector = search_input.data.get('selector')
            try:
                await self.page.fill(selector, query)
                await self.page.press(selector, 'Enter')
                await self.page.wait_for_timeout(2000)
                self._log(f"Searched: {query}")
                
                # Extract products
                products = await self._extract_products_llm()
                
                return ShoppingResult(
                    success=True, action='search',
                    products=products,
                    message=f"Found {len(products)} products"
                )
            except Exception as e:
                return ShoppingResult(
                    success=False, action='search',
                    error=str(e)
                )
        
        return ShoppingResult(
            success=False, action='search',
            error="Could not find search input"
        )
    
    async def _add_to_cart_llm(self) -> ShoppingResult:
        """Add product to cart using LLM to find button."""
        # LLM finds add to cart button
        cart_btn = await self.atoms.find_clickable_by_intent(
            "add to cart button / buy button / add to basket"
        )
        
        if cart_btn.success and cart_btn.data:
            selector = cart_btn.data.get('selector')
            try:
                await self.page.click(selector)
                await self.page.wait_for_timeout(1500)
                self._log(f"Clicked add to cart: {selector}")
                
                # Get cart contents
                cart = await self._get_cart_llm()
                
                return ShoppingResult(
                    success=True, action='add_to_cart',
                    cart=cart,
                    message="Added to cart"
                )
            except Exception as e:
                return ShoppingResult(
                    success=False, action='add_to_cart',
                    error=str(e)
                )
        
        return ShoppingResult(
            success=False, action='add_to_cart',
            error="Could not find add to cart button"
        )
    
    async def _process_checkout_llm(self, intent: ShoppingIntent) -> ShoppingResult:
        """Process checkout using LLM."""
        result = ShoppingResult(
            success=False, action='checkout',
            checkout_step=CheckoutStep.CART.value,
        )
        
        # Step 1: Go to cart / checkout
        checkout_btn = await self.atoms.find_clickable_by_intent(
            "go to cart / proceed to checkout / view cart"
        )
        
        if checkout_btn.success:
            try:
                await self.page.click(checkout_btn.data.get('selector'))
                await self.page.wait_for_timeout(2000)
                result.checkout_step = CheckoutStep.SHIPPING.value
            except Exception:
                pass
        
        # Step 2: Fill shipping if provided
        if intent.shipping:
            for field, value in intent.shipping.items():
                if value:
                    field_result = await self.atoms.find_input_by_context(
                        f"shipping form field for {field}"
                    )
                    if field_result.success:
                        try:
                            await self.page.fill(
                                field_result.data.get('selector'), value
                            )
                        except Exception:
                            pass
            result.checkout_step = CheckoutStep.PAYMENT.value
        
        # Step 3: Select payment method
        if intent.payment_method:
            payment_result = await self.atoms.find_clickable_by_intent(
                f"select {intent.payment_method} payment method"
            )
            if payment_result.success:
                try:
                    await self.page.click(payment_result.data.get('selector'))
                except Exception:
                    pass
        
        result.success = True
        result.message = f"Checkout at step: {result.checkout_step}"
        return result
    
    async def _get_cart_llm(self) -> List[Dict[str, Any]]:
        """Get cart contents using LLM."""
        if not self.atoms:
            return []
        
        result = await self.atoms.extract_data_pattern(
            "shopping cart items: product names, prices, quantities"
        )
        
        if result.success and result.data:
            items = result.data.get('items', [])
            if isinstance(items, list):
                return items
        
        return []
    
    async def _extract_products_llm(self) -> List[Dict[str, Any]]:
        """Extract products from page using LLM."""
        if not self.atoms:
            return []
        
        result = await self.atoms.extract_data_pattern(
            "product listings: names, prices, and URLs"
        )
        
        if result.success and result.data:
            products = result.data.get('products', [])
            if isinstance(products, list):
                return products[:20]  # Limit
        
        return []
    
    def _log(self, message: str, level: str = "info"):
        """Log message."""
        if self.run_logger:
            if level == "header":
                self.run_logger.log_text(f"\n{'='*50}\n{message}\n{'='*50}")
            elif level == "error":
                self.run_logger.log_text(f"❌ {message}")
            else:
                self.run_logger.log_text(f"   {message}")
        logger.info(message)
