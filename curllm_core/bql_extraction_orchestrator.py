"""
BQL-based Extraction Orchestrator
LLM analyzes DOM tree and generates BQL queries for precise extraction
"""
import json
import time
from typing import Any, Dict, Optional, List


class BQLExtractionOrchestrator:
    """LLM-driven BQL query generation for data extraction"""
    
    def __init__(self, llm, instruction: str, page, run_logger=None):
        self.llm = llm
        self.instruction = instruction
        self.page = page
        self.run_logger = run_logger
        self.phases_log = []
        
    async def orchestrate(self, page_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute 3-phase BQL extraction:
        1. DOM ANALYSIS - LLM analyzes DOM structure to find product patterns
        2. BQL GENERATION - LLM generates BQL query based on patterns
        3. EXECUTION & VALIDATION - Execute BQL and validate results
        """
        try:
            self._log_header("🔍 BQL EXTRACTION ORCHESTRATOR")
            
            # Phase 1: DOM Analysis
            try:
                dom_analysis = await self._phase_dom_analysis(page_context)
                if not dom_analysis:
                    return None
            except Exception as e:
                if self.run_logger:
                    self.run_logger.log_text(f"❌ Phase 1 failed: {type(e).__name__}: {e}")
                return None
                
            # Phase 2: BQL Generation
            try:
                bql_query = await self._phase_bql_generation(page_context, dom_analysis)
                if not bql_query:
                    return None
            except Exception as e:
                if self.run_logger:
                    self.run_logger.log_text(f"❌ Phase 2 failed: {type(e).__name__}: {e}")
                return None
            
            # Phase 3: Execution & Validation
            try:
                result = await self._phase_execution(bql_query)
                self._log_summary(result)
                return result
            except Exception as e:
                if self.run_logger:
                    self.run_logger.log_text(f"❌ Phase 3 failed: {type(e).__name__}: {e}")
                return None
            
        except Exception as e:
            if self.run_logger:
                self.run_logger.log_text(f"❌ BQL orchestrator failed: {type(e).__name__}: {e}")
            return None
    
    async def _phase_dom_analysis(self, page_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 1: LLM analyzes DOM structure to identify extraction patterns"""
        self._log_phase(1, "DOM Analysis")
        
        try:
            prompt = self._build_dom_analysis_prompt(page_context)
            response = await self._llm_invoke(prompt)
            
            analysis = json.loads(response)
            self._log_decision("DOM Analysis", analysis)
            self.phases_log.append({"phase": "dom_analysis", "result": analysis})
            return analysis
        except json.JSONDecodeError as e:
            self._log_error("DOM Analysis", f"JSON decode error: {e}")
            if self.run_logger:
                self.run_logger.log_text(f"   LLM Response: {response[:500]}")
            return None
        except Exception as e:
            self._log_error("DOM Analysis", f"{type(e).__name__}: {e}")
            return None
    
    async def _phase_bql_generation(self, page_context: Dict[str, Any], dom_analysis: Dict[str, Any]) -> Optional[str]:
        """Phase 2: LLM generates BQL query based on DOM analysis"""
        self._log_phase(2, "BQL Generation")
        
        if dom_analysis is None:
            self._log_error("BQL Generation", "DOM analysis is None")
            return None
        
        prompt = self._build_bql_generation_prompt(page_context, dom_analysis)
        response = await self._llm_invoke(prompt)
        
        try:
            bql_data = json.loads(response)
            bql_query = bql_data.get("bql_query", "")
            
            if not bql_query:
                self._log_error("BQL Generation", "Empty BQL query")
                return None
            
            self._log_decision("BQL Generation", {"bql_query": bql_query, "reasoning": bql_data.get("reasoning")})
            self.phases_log.append({"phase": "bql_generation", "query": bql_query})
            return bql_query
        except Exception as e:
            self._log_error("BQL Generation", str(e))
            return None
    
    async def _phase_execution(self, bql_query: str) -> Optional[Dict[str, Any]]:
        """Phase 3: Execute BQL query and validate results"""
        self._log_phase(3, "Execution & Validation")
        
        try:
            from .bql import BQLExecutor
            
            # Get browser context from page
            browser_context = self.page.context
            bql_executor = BQLExecutor(browser_context)
            
            # Execute BQL query
            result = await bql_executor.execute(bql_query)
            
            if result and isinstance(result, dict):
                data = result.get("data")
                if data:
                    # Count extracted items
                    count = 0
                    if isinstance(data, dict):
                        if "products" in data:
                            count = len(data.get("products", []))
                        elif "page" in data:
                            page_data = data.get("page", {})
                            if "items" in page_data:
                                count = len(page_data.get("items", []))
                    elif isinstance(data, list):
                        count = len(data)
                    
                    self._log_decision("Execution", {"status": "success", "count": count})
                    self.phases_log.append({"phase": "execution", "count": count})
                    return data
            
            self._log_decision("Execution", {"status": "empty", "count": 0})
            return None
            
        except Exception as e:
            self._log_error("Execution", str(e))
            return None
    
    # ========== Prompt Builders ==========
    
    def _build_dom_analysis_prompt(self, page_context: Dict[str, Any]) -> str:
        """Build prompt for DOM analysis phase"""
        if not page_context:
            raise ValueError("page_context is None or empty")
        
        url = page_context.get("url", "")
        title = page_context.get("title", "")
        links = (page_context.get("links") or [])[:20]
        headings = (page_context.get("headings") or [])[:10]
        
        # Build links summary
        links_text = "\n".join([
            f"  - {link.get('text', '')[:50]} -> {link.get('href', '')}"
            for link in links[:15]
            if isinstance(link, dict)
        ]) if links else "  (no links)"
        
        return f"""You are analyzing DOM structure to identify product listing patterns.

Instruction: {self.instruction}
URL: {url}
Title: {title}

Headings (structure):
{json.dumps(headings, indent=2)}

Links (sample):
{links_text}

TASK: Analyze the page structure and identify:
1. Product container patterns (CSS selectors, class names, tags)
2. Price location patterns (where prices appear in product containers)
3. Product name/title patterns
4. Product URL patterns

Look for repeating patterns that indicate product listings:
- Multiple similar elements with same classes
- Price indicators (zł, PLN, price, cena)
- Product links with IDs in URLs
- Structured data (lists, grids, cards)

Respond with JSON only:
{{
  "product_container_selector": ".product-card|.product-item|article.product",
  "product_link_selector": "a.product-link|a[href*='/product/']|h2 a",
  "price_selector": ".price|.product-price|span.price",
  "name_selector": ".product-name|h3.title|.product-title",
  "pattern_confidence": 0.8,
  "reasoning": "Found 20+ elements with class 'product-card' containing prices in 'span.price'"
}}

JSON:"""
    
    def _build_bql_generation_prompt(self, page_context: Dict[str, Any], dom_analysis: Dict[str, Any]) -> str:
        """Build prompt for BQL generation phase"""
        url = page_context.get("url", "")
        
        # Extract price limit from instruction
        price_limit = 150
        try:
            import re
            m = re.search(r'under\s*(\d+)|poniżej\s*(\d+)|below\s*(\d+)', self.instruction.lower())
            if m:
                for g in m.groups():
                    if g:
                        price_limit = int(g)
                        break
        except:
            pass
        
        return f"""You are generating a BQL (Browser Query Language) query for product extraction.

Instruction: {self.instruction}
URL: {url}
Price Limit: {price_limit}

DOM Analysis Result:
{json.dumps(dom_analysis, indent=2)}

BQL SYNTAX REFERENCE:
```
page.select("css_selector")                    # Select elements
  .map(item => ({{                              # Transform each element
    title: item.select("h3").text(),           # Extract text
    price: item.select(".price").text(),       # Extract price
    url: item.select("a").attr("href")         # Extract href attribute
  }}))
  .filter(item => parseFloat(item.price) < {price_limit})  # Filter by price
```

TASK: Generate a BQL query that:
1. Selects product containers using patterns from DOM analysis
2. Extracts: name/title, price, url
3. Filters products by price limit ({price_limit}zł)
4. Returns array of products

Use the selectors identified in DOM analysis. Be specific and precise.

Respond with JSON only:
{{
  "bql_query": "page.select('.product-card').map(...)...",
  "reasoning": "Brief explanation of the query logic"
}}

JSON:"""
    
    # ========== Helper Methods ==========
    
    async def _llm_invoke(self, prompt: str) -> str:
        """Invoke LLM and extract JSON response"""
        response = await self.llm.ainvoke(prompt)
        text = response.get("text", "")
        
        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start:end+1]
        return text
    
    def _log_header(self, message: str):
        """Log orchestrator header"""
        if self.run_logger:
            self.run_logger.log_text(f"\n{'='*60}")
            self.run_logger.log_text(message)
            self.run_logger.log_text(f"{'='*60}\n")
    
    def _log_phase(self, phase_num: int, phase_name: str):
        """Log phase start"""
        if self.run_logger:
            self.run_logger.log_text(f"\n━━━ PHASE {phase_num}: {phase_name} ━━━")
    
    def _log_decision(self, phase: str, decision: Dict[str, Any]):
        """Log LLM decision"""
        if self.run_logger:
            self.run_logger.log_text(f"   🎯 DECISION ({phase}):")
            self.run_logger.log_code("json", json.dumps(decision, indent=2))
    
    def _log_error(self, phase: str, error: str):
        """Log error"""
        if self.run_logger:
            self.run_logger.log_text(f"   ❌ ERROR ({phase}): {error}")
    
    def _log_summary(self, result: Optional[Dict[str, Any]]):
        """Log orchestration summary"""
        if self.run_logger:
            count = 0
            if result:
                if isinstance(result, dict):
                    if "products" in result:
                        count = len(result.get("products", []))
                    elif "page" in result:
                        count = len(result.get("page", {}).get("items", []))
                elif isinstance(result, list):
                    count = len(result)
            
            self.run_logger.log_text(f"\n{'='*60}")
            self.run_logger.log_text(f"✅ BQL Orchestration Complete")
            self.run_logger.log_text(f"   Phases: {len(self.phases_log)}")
            self.run_logger.log_text(f"   Items extracted: {count}")
            self.run_logger.log_text(f"{'='*60}\n")
