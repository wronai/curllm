"""
Atomic Functions - Small, Composable DOM Operations

Each function does ONE thing well and is fully observable/debuggable.

Benefits over monolithic heuristics:
1. Granular debugging - see exactly which step fails
2. Composable - LLM can combine them creatively
3. Testable - each function unit-testable
4. Observable - full execution trace
5. Adaptive - can try alternative strategies per-step
"""

import re
from typing import Any, Dict, List, Optional, Tuple


class AtomicFunctionExecutor:
    """Execute atomic DOM operations with full observability"""
    
    def __init__(self, page, run_logger=None):
        self.page = page
        self.run_logger = run_logger
        self.execution_trace = []
    
    def _log(self, step: str, result: Any):
        """Log execution step"""
        self.execution_trace.append({"step": step, "result": result})
        if self.run_logger:
            self.run_logger.log_text(f"      • {step}: {result}")
    
    async def _discover_selectors_with_llm(self, entity_type: str) -> List[str]:
        """
        Use LLM to discover appropriate selectors for entity type.
        
        No hardcoded selectors - LLM analyzes page structure and suggests selectors.
        """
        # Get page structure sample
        dom_sample = await self.page.evaluate("""
        () => {
            const elements = [];
            document.querySelectorAll('*').forEach((el, i) => {
                if (i > 500) return;
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    const classes = el.className ? 
                        (typeof el.className === 'string' ? el.className : '') : '';
                    if (classes.length > 0 || el.id) {
                        elements.push({
                            tag: el.tagName.toLowerCase(),
                            id: el.id || '',
                            class: classes.substring(0, 100),
                            text: (el.innerText || '').substring(0, 50)
                        });
                    }
                }
            });
            return elements.slice(0, 100);
        }
        """)
        
        # Ask LLM to suggest selectors
        try:
            from curllm_core.streamware.llm_client import get_llm
            llm = get_llm()
            
            prompt = f"""Analyze this DOM structure and suggest CSS selectors for finding {entity_type} containers.

DOM sample (tag, id, class, text preview):
{dom_sample[:2000]}

Return JSON array of selectors to try, ordered by likelihood:
["selector1", "selector2", ...]

JSON:"""
            
            response = await llm.generate(prompt)
            
            import json
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                selectors = json.loads(match.group())
                self._log("llm_selectors", f"LLM suggested: {selectors}")
                return selectors
        except Exception as e:
            self._log("llm_selectors", f"LLM failed: {e}, using fallback")
        
        # Fallback: generic dynamic detection
        return await self._fallback_selector_discovery(entity_type)
    
    async def _fallback_selector_discovery(self, entity_type: str) -> List[str]:
        """Fallback dynamic selector discovery without hardcoded patterns."""
        # Find elements with repeating patterns
        patterns = await self.page.evaluate("""
        () => {
            const classCount = {};
            document.querySelectorAll('*').forEach(el => {
                if (el.className && typeof el.className === 'string') {
                    const first = el.className.split(' ')[0];
                    if (first && first.length > 2) {
                        classCount[first] = (classCount[first] || 0) + 1;
                    }
                }
            });
            // Return classes that appear 3+ times (potential containers)
            return Object.entries(classCount)
                .filter(([_, count]) => count >= 3)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([cls, _]) => '.' + cls);
        }
        """)
        return patterns if patterns else []
    
    async def find_containers(self, entity_type: str = "product", min_count: int = 1) -> List[Dict]:
        """
        Find DOM containers that likely contain entities.
        
        Strategy:
        1. Try known selectors for entity_type
        2. Try heuristic pattern matching
        3. Return containers with metadata
        
        Returns:
            [
                {
                    "selector": ".product-box",
                    "index": 0,
                    "element_handle": <handle>,
                    "preview_text": "Product Name 149.99 zł..."
                },
                ...
            ]
        """
        self._log("find_containers", f"Looking for {entity_type} containers...")
        
        # Use LLM to discover selectors dynamically
        # No hardcoded selector patterns!
        selectors = await self._discover_selectors_with_llm(entity_type)
        
        containers = []
        for selector in selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                if len(elements) >= min_count:
                    self._log("find_containers", f"Found {len(elements)} with {selector}")
                    
                    # Get preview text for first few
                    for i, elem in enumerate(elements[:50]):  # Limit to 50
                        try:
                            text = await elem.inner_text()
                            containers.append({
                                "selector": selector,
                                "index": i,
                                "element": elem,
                                "preview_text": text[:100]
                            })
                        except Exception:
                            continue
                    
                    break  # Use first matching selector
            except Exception:
                continue
        
        # Fallback: heuristic container detection
        if not containers:
            self._log("find_containers", "No known selectors worked, trying heuristics...")
            containers = await self._find_containers_heuristic(entity_type)
        
        return containers
    
    async def _find_containers_heuristic(self, entity_type: str) -> List[Dict]:
        """Heuristic container detection based on patterns"""
        
        # Look for repeated structures with similar characteristics
        result = await self.page.evaluate("""
            (entityType) => {
                const containers = [];
                const allElements = Array.from(document.querySelectorAll('*'));
                
                // For products: look for elements with price patterns
                if (entityType === 'product') {
                    const pricePattern = /(\\d+[\\d\\s]*(?:[\\.,]\\d{2})?)\\s*(?:zł|PLN|€|\\$|USD|EUR)/i;
                    
                    for (const el of allElements) {
                        const text = el.innerText || '';
                        const hasPrice = pricePattern.test(text);
                        const hasLink = el.querySelector('a[href]') !== null;
                        
                        if (hasPrice && hasLink && text.length > 20 && text.length < 500) {
                            containers.push({
                                tag: el.tagName,
                                className: el.className,
                                preview: text.substring(0, 100)
                            });
                        }
                        
                        if (containers.length >= 50) break;
                    }
                }
                
                return containers;
            }
        """, entity_type)
        
        self._log("find_containers_heuristic", f"Found {len(result)} by heuristic")
        return result
    
    async def extract_field(self, container: Dict, field_spec) -> Optional[Any]:
        """
        Extract a single field from container.
        
        Args:
            container: Container dict with element handle
            field_spec: FieldSpec describing what to extract
        
        Returns:
            Extracted value (typed according to field_spec.type)
        """
        field_name = field_spec.name
        field_type = field_spec.type
        element = container.get("element")
        
        if not element:
            # Fallback to text-based extraction
            return await self._extract_from_text(container.get("preview_text", ""), field_spec)
        
        # Try selectors first
        if field_spec.selectors:
            for selector in field_spec.selectors:
                try:
                    sub_elem = await element.query_selector(selector)
                    if sub_elem:
                        text = await sub_elem.inner_text()
                        return self._transform_value(text.strip(), field_type, field_spec.transform)
                except Exception:
                    continue
        
        # Fallback: extract from container text using patterns
        try:
            text = await element.inner_text()
            return await self._extract_from_text(text, field_spec)
        except Exception:
            return None
    
    async def _extract_from_text(self, text: str, field_spec) -> Optional[Any]:
        """Extract field value from text using patterns"""
        field_type = field_spec.type
        
        if field_type == "price" or field_type == "number":
            return self._extract_price(text)
        elif field_type == "url":
            return self._extract_url(text)
        elif field_type == "text":
            # Use patterns if provided
            if field_spec.patterns:
                for pattern in field_spec.patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return match.group(1) if match.groups() else match.group(0)
            
            # Default: extract longest meaningful line
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            for line in lines:
                if 5 < len(line) < 140:
                    # Skip lines with prices/numbers only
                    if not re.match(r'^[\d\s\.,]+$', line):
                        return line
        
        return None
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Extract numeric price from text"""
        patterns = [
            r'(\d+[\d\s]*(?:[\\.,]\d{2})?)\s*(?:zł|PLN|złotych)',
            r'od\s*(\d+[\d\s]*(?:[\\.,]\d{2})?)\s*(?:zł|PLN)',
            r'cena[:\s]*(\d+[\d\s]*(?:[\\.,]\d{2})?)\s*(?:zł|PLN)',
            r'(\d+[\d\s]*(?:[\\.,]\d{2})?)\s*(?:€|EUR)',
            r'(\d+[\d\s]*(?:[\\.,]\d{2})?)\s*(?:\$|USD)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(1)
                # Normalize: remove spaces, convert comma to dot
                price_str = price_str.replace(' ', '').replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        
        return None
    
    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from text"""
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        match = re.search(url_pattern, text)
        return match.group(0) if match else None
    
    def _transform_value(self, value: str, field_type: str, transform: Optional[str]) -> Any:
        """Transform extracted value according to type and transform spec"""
        if not value:
            return None
        
        if field_type == "number" or field_type == "price":
            # Extract numeric value
            price = self._extract_price(value)
            if price:
                return price
            # Fallback: try to parse as float
            try:
                return float(re.sub(r'[^\d.]', '', value))
            except ValueError:
                return None
        
        elif field_type == "url":
            if value.startswith('http'):
                return value
            # Try to extract URL from text
            return self._extract_url(value)
        
        elif field_type == "text":
            return value.strip()
        
        return value
    
    async def validate_entities(self, entities: List[Dict], field_specs: List) -> List[Dict]:
        """
        Validate extracted entities against field specifications.
        
        Returns only entities that pass validation.
        """
        validated = []
        
        for entity in entities:
            valid = True
            
            # Check required fields
            for field_spec in field_specs:
                if field_spec.required:
                    value = entity.get(field_spec.name)
                    if value is None or value == "":
                        valid = False
                        break
            
            if valid:
                validated.append(entity)
        
        self._log("validate_entities", f"Validated {len(validated)}/{len(entities)} entities")
        return validated
    
    def get_execution_trace(self) -> List[Dict]:
        """Get full execution trace for debugging"""
        return self.execution_trace
