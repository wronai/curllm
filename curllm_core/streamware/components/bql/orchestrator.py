"""
BQL Extraction Orchestrator - LLM-driven BQL query generation.

Uses LLM to analyze DOM and generate BQL queries for precise extraction.
"""
import json
from typing import Any, Dict, Optional, List


class BQLExtractionOrchestrator:
    """
    LLM-driven BQL query generation for data extraction.
    
    3-Phase extraction:
    1. DOM ANALYSIS - LLM analyzes DOM structure to find patterns
    2. BQL GENERATION - LLM generates BQL query based on patterns
    3. EXECUTION & VALIDATION - Execute BQL and validate results
    """
    
    def __init__(self, llm, instruction: str, page, run_logger=None):
        self.llm = llm
        self.instruction = instruction
        self.page = page
        self.run_logger = run_logger
        self.phases_log = []
        
    def _is_product_task(self) -> bool:
        """Check if instruction is about product extraction."""
        try:
            low = (self.instruction or "").lower()
            return any(k in low for k in ["product", "produkt", "price", "cena", "zł", "pln"])
        except Exception:
            return False
        
    async def orchestrate(self, page_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute 3-phase BQL extraction.
        
        Args:
            page_context: Page context with DOM, URL, etc.
            
        Returns:
            Extraction result or None if failed
        """
        try:
            self._log_header("🔍 BQL EXTRACTION ORCHESTRATOR")
            
            # Phase 1: DOM Analysis
            dom_analysis = await self._phase_dom_analysis(page_context)
            if not dom_analysis:
                return None
                
            # Phase 2: BQL Generation
            bql_query = await self._phase_bql_generation(page_context, dom_analysis)
            if not bql_query:
                return None
            
            # Phase 3: Execution & Validation
            result = await self._phase_execution(bql_query)
            self._log_summary(result)
            return result
            
        except Exception as e:
            self._log_error("orchestrate", str(e))
            return None
    
    async def _phase_dom_analysis(self, page_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 1: LLM analyzes DOM structure."""
        self._log_phase(1, "DOM Analysis")
        
        try:
            prompt = self._build_dom_analysis_prompt(page_context)
            response = await self._llm_invoke(prompt)
            
            analysis = json.loads(response)
            self._log_decision("DOM Analysis", analysis)
            self.phases_log.append({"phase": "dom_analysis", "result": analysis})
            return analysis
            
        except json.JSONDecodeError:
            self._log_error("DOM Analysis", "JSON decode error")
            return None
        except Exception as e:
            self._log_error("DOM Analysis", str(e))
            return None
    
    async def _phase_bql_generation(
        self,
        page_context: Dict[str, Any],
        dom_analysis: Dict[str, Any]
    ) -> Optional[str]:
        """Phase 2: LLM generates BQL query."""
        self._log_phase(2, "BQL Generation")
        
        if dom_analysis is None:
            self._log_error("BQL Generation", "DOM analysis is None")
            return None
        
        try:
            prompt = self._build_bql_generation_prompt(page_context, dom_analysis)
            response = await self._llm_invoke(prompt)
            
            # Extract BQL from response
            bql_query = self._extract_bql_from_response(response)
            if bql_query:
                self._log_decision("BQL Query", {"query": bql_query[:200]})
                self.phases_log.append({"phase": "bql_generation", "query": bql_query})
                return bql_query
            else:
                self._log_error("BQL Generation", "No valid BQL in response")
                return None
                
        except Exception as e:
            self._log_error("BQL Generation", str(e))
            return None
    
    async def _phase_execution(self, bql_query: str) -> Optional[Dict[str, Any]]:
        """Phase 3: Execute BQL and validate."""
        self._log_phase(3, "Execution")
        
        try:
            from .executor import BQLExecutor
            
            # Create executor with page context
            executor = BQLExecutor(self.page)
            result = await executor.execute(bql_query)
            
            self.phases_log.append({"phase": "execution", "result": result})
            return result
            
        except Exception as e:
            self._log_error("Execution", str(e))
            return None
    
    def _build_dom_analysis_prompt(self, page_context: Dict[str, Any]) -> str:
        """Build prompt for DOM analysis."""
        dom_snippet = page_context.get("dom", "")[:5000]
        
        return f"""Analyze this DOM structure to find repeating patterns for extraction.

Instruction: {self.instruction}

DOM (truncated):
{dom_snippet}

Find:
1. Container selector for repeating items (e.g., products, articles)
2. Selectors for fields inside each container (title, price, description, etc.)

Output JSON:
{{
    "container_selector": ".product-item",
    "fields": {{
        "title": ".product-title",
        "price": ".price",
        "description": ".desc"
    }},
    "pattern_confidence": 0.9
}}

JSON:"""

    def _build_bql_generation_prompt(
        self,
        page_context: Dict[str, Any],
        dom_analysis: Dict[str, Any]
    ) -> str:
        """Build prompt for BQL generation."""
        container = dom_analysis.get("container_selector", "<detect from DOM>")
        fields = dom_analysis.get("fields", {})
        
        return f"""Generate a BQL query to extract data.

Container: {container}
Fields: {json.dumps(fields)}
URL: {page_context.get('url', '')}

Generate BQL query:
```bql
query {{
    page(url: "...") {{
        items: select(css: "...") {{
            field1: text(css: "...")
            field2: text(css: "...")
        }}
    }}
}}
```

BQL:"""

    def _extract_bql_from_response(self, response: str) -> Optional[str]:
        """Extract BQL query from LLM response."""
        import re
        
        # Try to find code block
        match = re.search(r'```(?:bql)?\s*(query\s*{.*?})\s*```', response, re.DOTALL)
        if match:
            return match.group(1)
        
        # Try to find raw query
        match = re.search(r'(query\s*{.*})', response, re.DOTALL)
        if match:
            return match.group(1)
        
        return None
    
    async def _llm_invoke(self, prompt: str) -> str:
        """Invoke LLM with prompt."""
        if hasattr(self.llm, 'ainvoke'):
            result = await self.llm.ainvoke(prompt)
            return result.get('text', str(result))
        elif hasattr(self.llm, 'generate'):
            return await self.llm.generate(prompt)
        else:
            return str(await self.llm(prompt))
    
    def _log_header(self, text: str):
        """Log header."""
        if self.run_logger:
            self.run_logger.log_text(f"\n{'='*60}")
            self.run_logger.log_text(f"{text}")
            self.run_logger.log_text(f"{'='*60}")
    
    def _log_phase(self, num: int, name: str):
        """Log phase start."""
        if self.run_logger:
            self.run_logger.log_text(f"\n## Phase {num}: {name}")
    
    def _log_decision(self, name: str, data: Any):
        """Log decision."""
        if self.run_logger:
            self.run_logger.log_text(f"**{name}:** `{json.dumps(data)[:200]}`")
    
    def _log_error(self, phase: str, error: str):
        """Log error."""
        if self.run_logger:
            self.run_logger.log_text(f"❌ **{phase} failed:** {error}")
    
    def _log_summary(self, result: Any):
        """Log extraction summary."""
        if self.run_logger and result:
            items = result.get("data", {}).get("items", [])
            self.run_logger.log_text(f"\n✅ **Extracted {len(items)} items**")
