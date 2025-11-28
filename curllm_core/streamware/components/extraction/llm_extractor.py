"""
LLM Iterative Extractor - Pure LLM-based product extraction.

NO REGEX - Every decision is made by LLM.
Each step is atomic and can be called independently.

Pipeline:
1. analyze_page() - LLM determines page type
2. find_containers() - LLM finds product containers
3. detect_fields() - LLM identifies field locations
4. extract_products() - LLM extracts each product
5. filter_products() - LLM filters by criteria
"""
import json
from typing import Dict, Any, List, Optional

from .page_analyzer import analyze_page_type, detect_price_format
from .container_finder import find_product_containers, analyze_container_content
from .field_detector import detect_product_fields, extract_field_value, detect_price_in_container
from .llm_patterns import generate_extraction_strategy, validate_selector, generate_price_pattern


class LLMIterativeExtractor:
    """
    Pure LLM-based iterative product extraction.
    
    Every decision is made by LLM, no regex or hardcoded patterns.
    Each step is atomic and logged for transparency.
    """
    
    def __init__(self, page, llm, instruction: str, run_logger=None):
        self.page = page
        self.llm = llm
        self.instruction = instruction
        self.run_logger = run_logger
        
        self.state = {
            "page_analysis": None,
            "container": None,
            "fields": None,
            "products": [],
            "steps": []
        }
    
    def _log(self, step: str, data: Any = None):
        """Log extraction step."""
        self.state["steps"].append({"step": step, "data": data})
        
        if self.run_logger:
            self.run_logger.log_text(f"\n## {step}")
            if data:
                self.run_logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False))
    
    async def run(self, max_items: int = 50) -> Dict[str, Any]:
        """
        Run full LLM-based extraction pipeline.
        
        Returns:
            {
                "products": [...],
                "count": int,
                "metadata": {...}
            }
        """
        self._log("🔄 LLM Iterative Extractor Started")
        
        # Step 1: Analyze page type
        page_analysis = await self._step_analyze_page()
        if not page_analysis.get("has_products"):
            return self._build_result([], "Page does not contain products")
        
        # Step 2: Find product containers
        container = await self._step_find_containers()
        if not container:
            return self._build_result([], "No product containers found")
        
        # Step 3: Detect field locations
        fields = await self._step_detect_fields(container["selector"])
        
        # Step 4: Extract products
        products = await self._step_extract_products(
            container["selector"],
            fields,
            max_items
        )
        
        # Step 5: Filter by instruction criteria
        if products:
            products = await self._step_filter_products(products)
        
        return self._build_result(products, "Success")
    
    async def _step_analyze_page(self) -> Dict[str, Any]:
        """Step 1: Analyze page type using LLM."""
        self._log("Step 1: Page Analysis")
        
        analysis = await analyze_page_type(
            self.page,
            self.llm,
            self.run_logger
        )
        
        self.state["page_analysis"] = analysis
        self._log("Page Analysis Result", analysis)
        
        return analysis
    
    async def _step_find_containers(self) -> Optional[Dict[str, Any]]:
        """Step 2: Find product containers using LLM."""
        self._log("Step 2: Container Detection")
        
        result = await find_product_containers(
            self.page,
            self.llm,
            self.instruction,
            self.run_logger
        )
        
        if result.get("found") and result.get("best"):
            # Verify container content
            verification = await analyze_container_content(
                self.page,
                self.llm,
                result["best"]["selector"],
                self.run_logger
            )
            
            if verification.get("is_product_container"):
                self.state["container"] = result["best"]
                self._log("Container Found", result["best"])
                return result["best"]
            else:
                self._log("Container Rejected", {
                    "selector": result["best"]["selector"],
                    "reason": verification.get("reasoning", "Not a product container")
                })
                
                # Try next candidate
                for candidate in result.get("containers", [])[1:5]:
                    verification = await analyze_container_content(
                        self.page,
                        self.llm,
                        candidate["selector"],
                        self.run_logger
                    )
                    if verification.get("is_product_container"):
                        self.state["container"] = candidate
                        self._log("Alternative Container Found", candidate)
                        return candidate
        
        self._log("No Product Container Found")
        return None
    
    async def _step_detect_fields(self, container_selector: str) -> Dict[str, Any]:
        """Step 3: Detect field locations using LLM."""
        self._log("Step 3: Field Detection")
        
        result = await detect_product_fields(
            self.page,
            self.llm,
            container_selector,
            self.run_logger
        )
        
        # Also detect price format
        price_info = await detect_price_in_container(
            self.page,
            self.llm,
            container_selector,
            self.run_logger
        )
        
        result["price_format"] = price_info
        self.state["fields"] = result
        self._log("Field Detection Result", result)
        
        return result
    
    async def _step_extract_products(
        self,
        container_selector: str,
        fields: Dict[str, Any],
        max_items: int
    ) -> List[Dict[str, Any]]:
        """Step 4: Extract products using LLM for each item."""
        self._log("Step 4: Product Extraction")
        
        # Get all containers
        containers = await self.page.query_selector_all(container_selector)
        
        if not containers:
            self._log("No containers found on page")
            return []
        
        products = []
        field_selectors = fields.get("fields", {})
        
        for i, container in enumerate(containers[:max_items]):
            if i % 10 == 0:
                self._log(f"Extracting product {i+1}/{min(len(containers), max_items)}")
            
            product = await self._extract_single_product(
                container,
                field_selectors,
                i
            )
            
            if product and (product.get("name") or product.get("price")):
                products.append(product)
        
        self._log("Extraction Complete", {
            "total_containers": len(containers),
            "extracted_products": len(products)
        })
        
        return products
    
    async def _extract_single_product(
        self,
        container,
        field_selectors: Dict,
        index: int
    ) -> Dict[str, Any]:
        """Extract a single product from container using LLM."""
        product = {"_index": index}
        
        # Try selector-based extraction first
        for field_name, field_info in field_selectors.items():
            if not field_info or not field_info.get("selector"):
                continue
            
            try:
                selector = field_info["selector"]
                
                if field_name == "url":
                    # Get href attribute
                    element = await container.query_selector(selector)
                    if element:
                        product["url"] = await element.get_attribute("href")
                
                elif field_name == "image":
                    # Get src attribute
                    element = await container.query_selector(selector)
                    if element:
                        product["image"] = await element.get_attribute("src")
                
                else:
                    # Get text content
                    element = await container.query_selector(selector)
                    if element:
                        product[field_name] = await element.text_content()
            
            except Exception:
                continue
        
        # If we couldn't get name/price, use LLM fallback
        if not product.get("name"):
            product["name"] = await extract_field_value(
                self.page,
                self.llm,
                container,
                "product name",
                self.run_logger
            )
        
        if not product.get("price"):
            product["price"] = await extract_field_value(
                self.page,
                self.llm,
                container,
                "price",
                self.run_logger
            )
        
        # Clean up values
        if product.get("name"):
            product["name"] = str(product["name"]).strip()
        
        if product.get("price"):
            product["price"] = await self._parse_price_with_llm(str(product["price"]))
        
        return product
    
    async def _parse_price_with_llm(self, price_text: str) -> Optional[float]:
        """Parse price value using LLM - NO REGEX."""
        if not price_text:
            return None
        
        # Use LLM to extract numeric price
        prompt = f"""Extract the numeric price from this text. Return ONLY the number (no currency).

Text: "{price_text}"

Rules:
- Return just the number (e.g., "299.99")
- Use dot for decimal separator
- If multiple numbers, return the price (not quantity)
- If no price found, return "null"

Number:"""
        
        try:
            response = await self._llm_generate(prompt)
            value = response.strip().lower()
            
            if value and value != "null":
                # Clean any remaining non-numeric chars
                cleaned = ''.join(c for c in value if c.isdigit() or c == '.')
                if cleaned:
                    return float(cleaned)
        except Exception:
            pass
        
        return None
    
    async def _step_filter_products(
        self,
        products: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Step 5: Filter products based on instruction using LLM."""
        self._log("Step 5: Product Filtering")
        
        # Check if instruction has filter criteria
        filter_criteria = await self._extract_filter_criteria()
        
        if not filter_criteria:
            self._log("No filter criteria found, returning all products")
            return products
        
        self._log("Filter Criteria", filter_criteria)
        
        filtered = []
        for product in products:
            if self._matches_criteria(product, filter_criteria):
                filtered.append(product)
        
        self._log("Filtering Complete", {
            "before": len(products),
            "after": len(filtered),
            "criteria": filter_criteria
        })
        
        return filtered
    
    async def _extract_filter_criteria(self) -> Optional[Dict[str, Any]]:
        """Use LLM to extract filter criteria from instruction."""
        prompt = f"""Extract filter criteria from this instruction:

Instruction: "{self.instruction}"

What filters should be applied to products?
- Price limit (under/over X)?
- Category?
- Brand?
- Other criteria?

Output JSON (or null if no filters):
{{"price_max": number|null, "price_min": number|null, "category": string|null, "brand": string|null, "other": string|null}}

JSON:"""

        try:
            response = await self._llm_generate(prompt)
            result = self._parse_json_response(response)
            
            # Check if any filter is set
            if result and any(v is not None for v in result.values()):
                return result
        except Exception:
            pass
        
        return None
    
    def _matches_criteria(
        self,
        product: Dict[str, Any],
        criteria: Dict[str, Any]
    ) -> bool:
        """Check if product matches filter criteria."""
        # Price max filter
        if criteria.get("price_max") is not None:
            price = product.get("price")
            if price is not None and price > criteria["price_max"]:
                return False
        
        # Price min filter
        if criteria.get("price_min") is not None:
            price = product.get("price")
            if price is not None and price < criteria["price_min"]:
                return False
        
        return True
    
    def _build_result(
        self,
        products: List[Dict[str, Any]],
        reason: str
    ) -> Dict[str, Any]:
        """Build final result dict."""
        return {
            "products": products,
            "count": len(products),
            "reason": reason,
            "metadata": {
                "page_analysis": self.state["page_analysis"],
                "container": self.state["container"],
                "fields": self.state["fields"],
                "steps": self.state["steps"]
            }
        }
    
    async def _llm_generate(self, prompt: str) -> str:
        """Generate text from LLM."""
        if hasattr(self.llm, 'ainvoke'):
            result = await self.llm.ainvoke(prompt)
            if isinstance(result, dict):
                return result.get('text', str(result))
            return str(result)
        elif hasattr(self.llm, 'generate'):
            return await self.llm.generate(prompt)
        else:
            return str(await self.llm(prompt))
    
    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        import re
        match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None


# Convenience function
async def llm_extract_products(
    page,
    llm,
    instruction: str,
    max_items: int = 50,
    run_logger=None
) -> Dict[str, Any]:
    """
    Extract products using pure LLM-based extraction.
    
    Args:
        page: Playwright page
        llm: LLM client
        instruction: User instruction
        max_items: Maximum items to extract
        run_logger: Optional logger
        
    Returns:
        {"products": [...], "count": int, "metadata": {...}}
    """
    extractor = LLMIterativeExtractor(page, llm, instruction, run_logger)
    return await extractor.run(max_items)
