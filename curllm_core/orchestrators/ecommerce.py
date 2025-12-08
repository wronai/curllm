"""
E-Commerce Orchestrator - Specialized orchestrator for shopping tasks

Handles:
- Product search and selection
- Add to cart operations
- Cart management
- Checkout flows
- Payment handling
- Order confirmation
"""



import warnings
warnings.warn(
    "This module is deprecated. Use curllm_core.v2.LLMECommerceOrchestrator instead.",
    DeprecationWarning,
    stacklevel=2
)



import json
import re
from typing import Any, Dict, List, Optional
from enum import Enum


class CheckoutStep(Enum):
    """Checkout workflow steps"""
    CART = "cart"
    SHIPPING = "shipping"
    PAYMENT = "payment"
    CONFIRMATION = "confirmation"


class ECommerceOrchestrator:
    """
    Specialized orchestrator for e-commerce tasks.
    
    Workflow:
    1. Navigate to product/search page
    2. Find and select products
    3. Add to cart
    4. Proceed to checkout
    5. Fill shipping information
    6. Process payment
    7. Confirm order
    """
    
    def __init__(self, llm=None, page=None, run_logger=None):
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute e-commerce workflow.
        
        Args:
            instruction: User's shopping instruction
            page_context: Current page state
            
        Returns:
            Shopping result with cart, checkout status
        """
        self._log("🛒 E-COMMERCE ORCHESTRATOR", "header")
        
        result = {
            'success': False,
            'cart': [],
            'checkout_step': None,
            'order': None
        }
        
        try:
            # Phase 1: Parse shopping intent
            intent = self._parse_shopping_intent(instruction)
            self._log(f"Intent: {intent['action']}")
            
            # Phase 2: Execute based on intent
            if intent['action'] == 'search':
                result['products'] = await self._search_products(intent['query'])
                
            elif intent['action'] == 'add_to_cart':
                cart_result = await self._add_to_cart(intent)
                result['cart'] = cart_result.get('items', [])
                result['success'] = cart_result.get('added', False)
                
            elif intent['action'] == 'checkout':
                checkout_result = await self._process_checkout(intent)
                result.update(checkout_result)
                
            elif intent['action'] == 'full_purchase':
                # Complete flow: search -> add -> checkout
                purchase_result = await self._full_purchase_flow(intent)
                result.update(purchase_result)
            
            else:
                # Default: analyze cart
                result['cart'] = await self._get_cart_contents()
            
            self._log(f"Result: {result.get('success', False)}")
            
        except Exception as e:
            result['error'] = str(e)
            self._log(f"E-commerce failed: {e}", "error")
        
        return result
    
    def _parse_shopping_intent(self, instruction: str) -> Dict[str, Any]:
        """Parse shopping intent from instruction"""
        instr_lower = instruction.lower()
        intent = {
            'action': 'browse',
            'products': [],
            'query': None,
            'payment_method': None,
            'shipping': {}
        }
        
        # Determine action
        if any(kw in instr_lower for kw in ['search', 'find', 'szukaj', 'znajdź']):
            intent['action'] = 'search'
            # Extract search query
            query_match = re.search(r'(?:search|find|szukaj|znajdź)\s+["\']?([^"\']+)["\']?', instr_lower)
            if query_match:
                intent['query'] = query_match.group(1).strip()
        
        # Check for "add to cart" with flexible patterns (add X to cart, add to cart X, buy X)
        elif (re.search(r'\badd\b.*\bcart\b', instr_lower) or 
              re.search(r'\bdodaj\b.*\bkoszyk', instr_lower) or 
              'add to cart' in instr_lower or 
              'dodaj do koszyka' in instr_lower or
              any(kw in instr_lower for kw in ['buy', 'kup', 'purchase now', 'kup teraz'])):
            intent['action'] = 'add_to_cart'
            # Extract product names or selectors
            
        elif any(kw in instr_lower for kw in ['checkout', 'pay', 'order', 'zamów', 'zapłać', 'proceed to']):
            intent['action'] = 'checkout'
            
        elif 'full purchase' in instr_lower or 'zakup' in instr_lower:
            intent['action'] = 'full_purchase'
        
        # Parse payment method
        if 'blik' in instr_lower:
            intent['payment_method'] = 'blik'
        elif 'card' in instr_lower or 'karta' in instr_lower:
            intent['payment_method'] = 'card'
        elif 'paypal' in instr_lower:
            intent['payment_method'] = 'paypal'
        elif 'przelewy24' in instr_lower or 'p24' in instr_lower:
            intent['payment_method'] = 'przelewy24'
        elif 'transfer' in instr_lower or 'przelew' in instr_lower:
            intent['payment_method'] = 'bank_transfer'
        
        # Parse shipping info
        shipping_patterns = {
            'name': r'name[=:]\s*["\']?([^,\'"]+)',
            'address': r'address[=:]\s*["\']?([^,\'"]+)',
            'city': r'city[=:]\s*["\']?([^,\'"]+)',
            'zip': r'(?:zip|postal)[=:]\s*["\']?([^,\'"]+)',
            'phone': r'(?:phone|tel)[=:]\s*["\']?([^,\'"]+)'
        }
        
        for field, pattern in shipping_patterns.items():
            match = re.search(pattern, instruction, re.I)
            if match:
                intent['shipping'][field] = match.group(1).strip()
        
        return intent
    
    async def _search_products(self, query: str) -> List[Dict[str, Any]]:
        """Search for products"""
        if not self.page:
            return []
        
        try:
            # Find and fill search input
            search_selectors = [
                'input[type="search"]',
                'input[name="search"]',
                'input[name="q"]',
                '#search',
                '.search-input',
                '[placeholder*="szukaj"]',
                '[placeholder*="search"]'
            ]
            
            for selector in search_selectors:
                try:
                    await self.page.fill(selector, query)
                    await self.page.press(selector, 'Enter')
                    await self.page.wait_for_timeout(2000)
                    break
                except Exception:
                    continue
            
            # Extract products
            products = await self._extract_products()
            return products
            
        except Exception as e:
            self._log(f"Search failed: {e}", "error")
            return []
    
    async def _add_to_cart(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Add product to cart"""
        if not self.page:
            return {'added': False}
        
        result = {'added': False, 'items': []}
        
        try:
            # Find add to cart button
            cart_selectors = [
                'button:has-text("Add to Cart")',
                'button:has-text("Dodaj do koszyka")',
                'button:has-text("Buy")',
                'button:has-text("Kup")',
                '.add-to-cart',
                '#add-to-cart',
                '[data-action="add-to-cart"]',
                'button[class*="cart"]'
            ]
            
            for selector in cart_selectors:
                try:
                    await self.page.click(selector, timeout=3000)
                    await self.page.wait_for_timeout(1500)
                    result['added'] = True
                    break
                except Exception:
                    continue
            
            # Get cart contents
            result['items'] = await self._get_cart_contents()
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _process_checkout(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Process checkout flow"""
        if not self.page:
            return {'success': False}
        
        result = {
            'success': False,
            'checkout_step': CheckoutStep.CART.value,
            'steps_completed': []
        }
        
        try:
            # Step 1: Go to cart/checkout
            checkout_links = [
                'a:has-text("Checkout")',
                'a:has-text("Kasa")',
                'a:has-text("Przejdź do kasy")',
                '.checkout-button',
                '#checkout'
            ]
            
            for selector in checkout_links:
                try:
                    await self.page.click(selector, timeout=3000)
                    await self.page.wait_for_timeout(2000)
                    result['steps_completed'].append('cart')
                    result['checkout_step'] = CheckoutStep.SHIPPING.value
                    break
                except Exception:
                    continue
            
            # Step 2: Fill shipping info
            shipping = intent.get('shipping', {})
            if shipping:
                for field, value in shipping.items():
                    selectors = [
                        f'input[name*="{field}"]',
                        f'input[id*="{field}"]',
                        f'input[placeholder*="{field}"]'
                    ]
                    for selector in selectors:
                        try:
                            await self.page.fill(selector, value, timeout=2000)
                            break
                        except Exception:
                            continue
                
                result['steps_completed'].append('shipping')
                result['checkout_step'] = CheckoutStep.PAYMENT.value
            
            # Step 3: Select payment method
            payment_method = intent.get('payment_method')
            if payment_method:
                await self._select_payment_method(payment_method)
                result['steps_completed'].append('payment')
                result['checkout_step'] = CheckoutStep.CONFIRMATION.value
            
            # Note: We don't auto-submit payment for safety
            result['success'] = len(result['steps_completed']) > 0
            result['note'] = 'Payment submission requires manual confirmation'
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def _full_purchase_flow(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete purchase flow"""
        result = {
            'success': False,
            'steps': []
        }
        
        # Search for product
        if intent.get('query'):
            products = await self._search_products(intent['query'])
            result['products_found'] = len(products)
            result['steps'].append('search')
            
            if products:
                # Click on first product
                await self._click_first_product()
                result['steps'].append('select_product')
        
        # Add to cart
        cart_result = await self._add_to_cart(intent)
        if cart_result.get('added'):
            result['cart'] = cart_result.get('items', [])
            result['steps'].append('add_to_cart')
        
        # Process checkout
        checkout_result = await self._process_checkout(intent)
        result.update(checkout_result)
        result['steps'].extend(checkout_result.get('steps_completed', []))
        
        result['success'] = len(result['steps']) > 2
        
        return result
    
    async def _extract_products(self) -> List[Dict[str, Any]]:
        """Extract products from current page"""
        if not self.page:
            return []
        
        try:
            return await self.page.evaluate('''() => {
                const items = document.querySelectorAll(
                    '[class*="product"], [class*="item"], article'
                );
                return Array.from(items).slice(0, 20).map(el => {
                    const name = el.querySelector('h2, h3, .name, .title')?.textContent?.trim() || '';
                    const price = el.querySelector('.price, [class*="price"]')?.textContent?.trim() || '';
                    const url = el.querySelector('a')?.href || '';
                    return { name, price, url };
                }).filter(p => p.name);
            }''')
        except Exception:
            return []
    
    async def _get_cart_contents(self) -> List[Dict[str, Any]]:
        """Get current cart contents"""
        if not self.page:
            return []
        
        try:
            return await self.page.evaluate('''() => {
                const items = document.querySelectorAll(
                    '.cart-item, [class*="cart-item"], .basket-item'
                );
                return Array.from(items).map(el => {
                    const name = el.querySelector('.name, .title, h3, h4')?.textContent?.trim() || '';
                    const price = el.querySelector('.price, [class*="price"]')?.textContent?.trim() || '';
                    const qty = el.querySelector('input[type="number"]')?.value || '1';
                    return { name, price, quantity: parseInt(qty) };
                });
            }''')
        except Exception:
            return []
    
    async def _click_first_product(self):
        """Click on first product in list using LLM-first approach"""
        if not self.page:
            return
        
        # Try LLM-based element finding first
        if hasattr(self, 'llm') and self.llm:
            try:
                from curllm_core.llm_dsl.selector_generator import LLMSelectorGenerator
                generator = LLMSelectorGenerator(llm=self.llm)
                result = await generator.generate_field_selector(
                    self.page, 
                    purpose="first product link in product listing"
                )
                if result.confidence > 0.5 and result.selector:
                    await self.page.click(result.selector)
                    return
            except Exception:
                pass
        
        # Fallback: common product link patterns (semantic element types)
        try:
            product_selectors = [
                '.product a',
                '.product-item a',
                '.item a',
                'article a'
            ]
            
            for selector in product_selectors:
                try:
                    await self.page.click(selector, timeout=3000)
                    await self.page.wait_for_timeout(2000)
                    break
                except Exception:
                    continue
        except Exception:
            pass
    
    async def _select_payment_method(self, method: str):
        """Select payment method"""
        if not self.page:
            return
        
        method_selectors = {
            'blik': ['input[value="blik"]', 'label:has-text("BLIK")', '#blik'],
            'card': ['input[value="card"]', 'label:has-text("Card")', 'label:has-text("Karta")'],
            'paypal': ['input[value="paypal"]', 'label:has-text("PayPal")'],
            'przelewy24': ['input[value="p24"]', 'label:has-text("Przelewy24")'],
            'bank_transfer': ['input[value="transfer"]', 'label:has-text("Przelew")']
        }
        
        selectors = method_selectors.get(method, [])
        for selector in selectors:
            try:
                await self.page.click(selector, timeout=2000)
                break
            except Exception:
                continue
    
    def _log(self, message: str, level: str = "info"):
        """Log message"""
        if self.run_logger:
            if level == "header":
                self.run_logger.log_text(f"\n{'='*50}")
                self.run_logger.log_text(message)
                self.run_logger.log_text(f"{'='*50}\n")
            elif level == "error":
                self.run_logger.log_text(f"❌ {message}")
            else:
                self.run_logger.log_text(f"   {message}")

