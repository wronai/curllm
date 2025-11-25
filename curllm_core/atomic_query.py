"""
Atomic Query System - Composable DOM Queries

Small, reusable functions that can be composed:
- find_elements(selector) → List[Element]
- extract_text(element) → str
- extract_attr(element, attr) → str
- filter_by(elements, predicate) → List[Element]
- map_to(elements, transformer) → List[Any]

Example:
    products = (
        find_elements(".product")
        >> filter_by(lambda el: has_price(el))
        >> map_to(extract_product_data)
        >> export_to("json")
    )
"""

from typing import List, Dict, Any, Callable, Optional, TypeVar
from dataclasses import dataclass
import json

T = TypeVar('T')


@dataclass
class QueryResult:
    """Result of an atomic query"""
    data: List[Any]
    metadata: Dict[str, Any]
    
    def __len__(self):
        return len(self.data)
    
    def __iter__(self):
        return iter(self.data)


class AtomicQuery:
    """
    Atomic query builder for composable DOM operations
    
    Usage:
        query = AtomicQuery(page)
        # Use dynamic detection instead of hard-coded selectors:
        # from curllm_core.iterative_extractor import IterativeExtractor
        # extractor = IterativeExtractor(page)
        # products = await extractor.extract(...)
    """
    
    def __init__(self, page, run_logger=None):
        self.page = page
        self.run_logger = run_logger
        self.operations = []
        self.metadata = {"operations": []}
    
    def _log(self, operation: str, details: Any):
        """Log operation"""
        if self.run_logger:
            self.run_logger.log_text(f"🔍 Query: {operation}")
            if isinstance(details, dict):
                self.run_logger.log_code("json", json.dumps(details, indent=2, ensure_ascii=False)[:500])
        
        self.metadata["operations"].append({
            "operation": operation,
            "details": details
        })
    
    def find(self, selector: str) -> 'AtomicQuery':
        """
        Find elements by selector
        
        Args:
            selector: CSS selector
            
        Returns:
            AtomicQuery for chaining
        """
        self.operations.append({
            "type": "find",
            "selector": selector
        })
        self._log("find", {"selector": selector})
        return self
    
    def filter(self, predicate_js: str) -> 'AtomicQuery':
        """
        Filter elements with JavaScript predicate
        
        Args:
            predicate_js: JavaScript function as string
            
        Example:
            .filter("el => el.innerText.includes('Available')")
        """
        self.operations.append({
            "type": "filter",
            "predicate": predicate_js
        })
        self._log("filter", {"predicate": predicate_js[:100]})
        return self
    
    def map(self, transformer_js: str) -> 'AtomicQuery':
        """
        Map elements to data using JavaScript transformer
        
        Args:
            transformer_js: JavaScript function as string
            
        Example:
            .map("el => ({name: el.querySelector('h3').innerText, price: ...})")
        """
        self.operations.append({
            "type": "map",
            "transformer": transformer_js
        })
        self._log("map", {"transformer": transformer_js[:100]})
        return self
    
    def extract_text(self, child_selector: Optional[str] = None) -> 'AtomicQuery':
        """
        Extract text from elements
        
        Args:
            child_selector: Optional selector for child element
        """
        if child_selector:
            transformer = f"el => el.querySelector('{child_selector}')?.innerText?.trim() || ''"
        else:
            transformer = "el => el.innerText?.trim() || ''"
        
        return self.map(transformer)
    
    def extract_attr(self, attr: str, child_selector: Optional[str] = None) -> 'AtomicQuery':
        """
        Extract attribute from elements
        
        Args:
            attr: Attribute name (e.g., 'href', 'src')
            child_selector: Optional selector for child element
        """
        if child_selector:
            transformer = f"el => el.querySelector('{child_selector}')?.getAttribute('{attr}') || ''"
        else:
            transformer = f"el => el.getAttribute('{attr}') || ''"
        
        return self.map(transformer)
    
    def limit(self, count: int) -> 'AtomicQuery':
        """
        Limit number of results
        
        Args:
            count: Maximum number of results
        """
        self.operations.append({
            "type": "limit",
            "count": count
        })
        self._log("limit", {"count": count})
        return self
    
    async def execute(self) -> QueryResult:
        """
        Execute the query pipeline
        
        Returns:
            QueryResult with data and metadata
        """
        self._log("execute", {"operations_count": len(self.operations)})
        
        # Build JavaScript code from operations
        js_code = self._build_js_code()
        
        # Execute in browser
        try:
            result = await self.page.evaluate(js_code)
            
            self._log("result", {
                "count": len(result) if isinstance(result, list) else 0,
                "sample": result[:2] if isinstance(result, list) else result
            })
            
            return QueryResult(
                data=result if isinstance(result, list) else [result],
                metadata=self.metadata
            )
        except Exception as e:
            self._log("error", {"error": str(e)})
            return QueryResult(data=[], metadata=self.metadata)
    
    def _build_js_code(self) -> str:
        """Build JavaScript code from operations"""
        code_parts = []
        
        # Start with initial selector
        find_op = next((op for op in self.operations if op["type"] == "find"), None)
        if not find_op:
            return "() => []"
        
        code_parts.append(f"let elements = Array.from(document.querySelectorAll('{find_op['selector']}'));")
        
        # Apply operations in order
        for op in self.operations:
            if op["type"] == "filter":
                code_parts.append(f"elements = elements.filter({op['predicate']});")
            elif op["type"] == "map":
                code_parts.append(f"elements = elements.map({op['transformer']});")
            elif op["type"] == "limit":
                code_parts.append(f"elements = elements.slice(0, {op['count']});")
        
        code_parts.append("return elements;")
        
        return f"() => {{ {' '.join(code_parts)} }}"


class ProductQuery(AtomicQuery):
    """
    Specialized query for product extraction
    
    Pre-configured patterns for e-commerce sites
    """
    
    def extract_product(self, name_sel: str, price_sel: str, url_sel: str) -> 'ProductQuery':
        """
        Extract product data with common patterns
        
        Args:
            name_sel: Selector for product name
            price_sel: Selector for price
            url_sel: Selector for URL
        """
        transformer = f"""
        el => {{
            const name = el.querySelector('{name_sel}')?.innerText?.trim() || '';
            const priceText = el.querySelector('{price_sel}')?.innerText?.trim() || '';
            const priceMatch = priceText.match(/(\\d+[\\d\\s]*(?:[\\.,]\\d{{2}})?)\\s*(?:zł|PLN|€|\\$)/i);
            const price = priceMatch ? parseFloat(priceMatch[1].replace(/\\s/g, '').replace(',', '.')) : null;
            const url = el.querySelector('{url_sel}')?.href || '';
            
            return {{ name, price, url }};
        }}
        """
        return self.map(transformer)
    
    def filter_by_price(self, min_price: Optional[float] = None, max_price: Optional[float] = None) -> 'ProductQuery':
        """
        Filter products by price range
        
        Args:
            min_price: Minimum price (inclusive)
            max_price: Maximum price (inclusive)
        """
        conditions = []
        if min_price is not None:
            conditions.append(f"item.price >= {min_price}")
        if max_price is not None:
            conditions.append(f"item.price <= {max_price}")
        
        predicate = " && ".join(conditions) if conditions else "true"
        return self.filter(f"item => item.price !== null && ({predicate})")


# Convenience functions for quick queries

async def quick_find(page, selector: str, limit: int = 50) -> List[Any]:
    """
    Quick find with selector
    
    Usage:
        # For product extraction, use dynamic detection:
        # from curllm_core.iterative_extractor import IterativeExtractor
        # extractor = IterativeExtractor(page)
        # results = await extractor.extract(instruction, page_type="product_listing")
    """
    query = AtomicQuery(page)
    result = await query.find(selector).limit(limit).execute()
    return result.data


async def quick_extract_text(page, selector: str, child_selector: Optional[str] = None) -> List[str]:
    """
    Quick text extraction
    
    Usage:
        names = await quick_extract_text(page, ".product", "h3.name")
    """
    query = AtomicQuery(page)
    query.find(selector)
    if child_selector:
        query.extract_text(child_selector)
    else:
        query.extract_text()
    result = await query.execute()
    return result.data


async def quick_extract_products(
    page,
    container_selector: str,
    name_selector: str,
    price_selector: str,
    url_selector: str,
    max_price: Optional[float] = None,
    limit: int = 50
) -> List[Dict]:
    """
    Quick product extraction with filtering
    
    Usage:
        # DEPRECATED: Use dynamic detection instead
        # from curllm_core.iterative_extractor import IterativeExtractor
        # extractor = IterativeExtractor(page)
        # products = await extractor.extract(instruction="Find products")
            max_price=150,
            limit=50
        )
    """
    query = ProductQuery(page)
    query.find(container_selector)
    query.extract_product(name_selector, price_selector, url_selector)
    
    if max_price is not None:
        query.filter_by_price(max_price=max_price)
    
    query.limit(limit)
    
    result = await query.execute()
    return result.data
