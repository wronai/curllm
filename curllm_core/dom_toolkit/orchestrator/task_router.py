"""
Extraction Orchestrator - Minimal LLM, Maximum Efficiency

Design Philosophy:
- LLM receives TINY context (< 500 chars)
- LLM makes ATOMIC decisions (one thing at a time)
- Heavy lifting done by JavaScript analyzers
- LLM validates results, not raw DOM

LLM Query Types:
1. INTERPRET: What does user want? → {task_type, fields_needed}
2. CHOOSE: Which selector is best? → {selected_index, reason}
3. VALIDATE: Is result correct? → {valid, issues}
4. RECOVER: What to try next? → {action, params}
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class AtomicLLMQuery:
    """
    Represents a minimal LLM query.
    
    Designed to be:
    - Small context (< 500 chars input)
    - Focused question (one decision)
    - Structured output (JSON)
    """
    query_type: str  # interpret, choose, validate, recover
    context: str     # Minimal context (< 500 chars)
    question: str    # Specific question
    options: Optional[List[str]] = None  # For choice queries
    
    def to_prompt(self) -> str:
        """Generate minimal prompt for LLM."""
        parts = [f"Task: {self.query_type.upper()}"]
        
        if self.context:
            parts.append(f"Context: {self.context[:500]}")
        
        parts.append(f"Question: {self.question}")
        
        if self.options:
            parts.append("Options:")
            for i, opt in enumerate(self.options):
                parts.append(f"  {i}: {opt[:100]}")
        
        parts.append("Respond with JSON only. Be brief.")
        
        return "\n".join(parts)


class ExtractionOrchestrator:
    """
    Orchestrate extraction with minimal LLM usage.
    
    Pipeline:
    1. Interpret user instruction (LLM: 1 call)
    2. Analyze DOM structure (JS: 0 LLM calls)
    3. Find container candidates (JS: 0 LLM calls)
    4. Score candidates statistically (JS: 0 LLM calls)
    5. LLM selects best candidate (LLM: 1 call) - OPTIONAL
    6. Extract data (JS: 0 LLM calls)
    7. Validate results (LLM: 1 call) - OPTIONAL
    
    Total LLM calls: 1-3 (vs. 5-20 in traditional approach)
    """
    
    def __init__(self, llm_client, run_logger=None):
        self.llm = llm_client
        self.logger = run_logger
        
        # Import analyzers lazily
        from ..analyzers import DOMStructureAnalyzer, PatternDetector, SelectorGenerator, PriceDetector
        from ..statistics import FrequencyAnalyzer, ElementClusterer, CandidateScorer
        
        self.structure = DOMStructureAnalyzer
        self.patterns = PatternDetector
        self.selectors = SelectorGenerator
        self.prices = PriceDetector
        self.frequency = FrequencyAnalyzer
        self.clustering = ElementClusterer
        self.scoring = CandidateScorer
    
    def _log(self, msg: str, data: Any = None):
        if self.logger:
            self.logger.log_text(msg)
            if data:
                self.logger.log_code("json", json.dumps(data, indent=2, ensure_ascii=False)[:1000])
    
    async def _llm_query(self, query: AtomicLLMQuery) -> Dict[str, Any]:
        """Execute atomic LLM query with minimal context."""
        prompt = query.to_prompt()
        
        self._log(f"🧠 LLM Query ({query.query_type})", {"prompt_length": len(prompt)})
        
        try:
            response = await self.llm.ainvoke(prompt)
            text = response.get("text", "") if isinstance(response, dict) else str(response)
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"raw": text}
        except Exception as e:
            self._log(f"⚠️ LLM Error: {e}")
            return {"error": str(e)}
    
    # =========================================================================
    # ATOMIC LLM QUERIES
    # =========================================================================
    
    async def interpret_task(self, instruction: str) -> Dict[str, Any]:
        """
        LLM Call #1: Interpret what user wants.
        
        Input: User instruction (< 200 chars)
        Output: {task_type, fields_needed, filters}
        """
        query = AtomicLLMQuery(
            query_type="interpret",
            context="",
            question=f"What extraction task is this? Instruction: '{instruction[:200]}'"
        )
        
        # Add expected output format
        query.context = """
Respond with JSON:
{
  "task_type": "products|articles|links|form|screenshot|other",
  "fields": ["name", "price", "url"],
  "filter": {"max_price": null, "keyword": null}
}
"""
        
        return await self._llm_query(query)
    
    async def choose_selector(
        self, 
        candidates: List[Dict],
        task_description: str
    ) -> Dict[str, Any]:
        """
        LLM Call #2: Choose best selector from candidates.
        
        Input: 3-5 candidate selectors with stats
        Output: {selected_index, reason}
        """
        # Build minimal options list
        options = []
        for i, c in enumerate(candidates[:5]):
            options.append(
                f"count={c.get('count', 0)}, "
                f"price_ratio={c.get('metrics', {}).get('price_ratio', 0)}, "
                f"selector={c.get('selector', '')[:50]}"
            )
        
        query = AtomicLLMQuery(
            query_type="choose",
            context=f"Task: {task_description[:100]}",
            question="Which container is best for extracting items?",
            options=options
        )
        
        return await self._llm_query(query)
    
    async def validate_results(
        self,
        results: List[Dict],
        expected_fields: List[str]
    ) -> Dict[str, Any]:
        """
        LLM Call #3: Validate extraction results.
        
        Input: Sample of results (2-3 items)
        Output: {valid, issues, suggestions}
        """
        # Build minimal sample
        sample = []
        for r in results[:3]:
            item = {}
            for field in expected_fields:
                value = r.get(field)
                if value:
                    item[field] = str(value)[:50]
            sample.append(item)
        
        query = AtomicLLMQuery(
            query_type="validate",
            context=f"Expected fields: {expected_fields}",
            question=f"Are these results valid? Sample: {json.dumps(sample)[:300]}"
        )
        
        return await self._llm_query(query)
    
    # =========================================================================
    # MAIN EXTRACTION PIPELINE
    # =========================================================================
    
    async def extract(
        self,
        page,
        instruction: str,
        use_llm_selection: bool = False,
        max_items: int = 50
    ) -> Dict[str, Any]:
        """
        Main extraction pipeline with minimal LLM usage.
        
        Args:
            page: Playwright page
            instruction: User's extraction instruction
            use_llm_selection: Use LLM to choose selector (adds 1 call)
            max_items: Maximum items to extract
        
        Returns:
            {items: [...], selector_used, stats, llm_calls}
        """
        llm_calls = 0
        
        # Step 1: Interpret task (LLM call)
        self._log("📝 Step 1: Interpreting task...")
        task = await self.interpret_task(instruction)
        llm_calls += 1
        
        task_type = task.get("task_type", "products")
        fields = task.get("fields", ["name", "price", "url"])
        
        self._log("Task interpretation", task)
        
        # Step 2: Analyze page structure (NO LLM)
        self._log("🔍 Step 2: Analyzing DOM structure...")
        
        page_summary = await self.structure.get_page_summary(page)
        repeating = await self.patterns.find_repeating_containers(
            page, 
            min_count=5,
            require_links=True,
            require_price_signals=("price" in fields)
        )
        
        self._log("Found repeating containers", {"count": len(repeating)})
        
        if not repeating:
            # Fallback: try list structures
            repeating = await self.patterns.find_list_structures(page)
            self._log("Fallback to list structures", {"count": len(repeating)})
        
        if not repeating:
            return {
                "items": [],
                "error": "No suitable containers found",
                "llm_calls": llm_calls
            }
        
        # Step 3: Score candidates (NO LLM)
        self._log("📊 Step 3: Scoring candidates...")
        
        selectors = [c.get("selector") for c in repeating if c.get("selector")]
        scored = await self.scoring.score_containers(page, selectors)
        
        self._log("Top candidates", {"top_3": scored[:3]})
        
        # Step 4: Select best candidate
        if use_llm_selection and len(scored) > 1:
            # LLM selection (optional)
            self._log("🧠 Step 4: LLM selecting best container...")
            choice = await self.choose_selector(scored, instruction)
            llm_calls += 1
            
            selected_idx = choice.get("selected_index", 0)
            if isinstance(selected_idx, int) and 0 <= selected_idx < len(scored):
                best = scored[selected_idx]
            else:
                best = scored[0]
        else:
            # Statistical selection (default)
            self._log("📈 Step 4: Statistical selection...")
            best = scored[0] if scored else None
        
        if not best:
            return {
                "items": [],
                "error": "No valid container selected",
                "llm_calls": llm_calls
            }
        
        self._log("Selected container", best)
        
        # Step 5: Extract field selectors (NO LLM)
        self._log("🔧 Step 5: Extracting field selectors...")
        
        field_info = await self.selectors.extract_field_selectors(
            page, 
            best.get("selector")
        )
        
        self._log("Field selectors", field_info)
        
        # Step 6: Extract data (NO LLM)
        self._log("📦 Step 6: Extracting data...")
        
        items = await self._extract_items(
            page,
            best.get("selector"),
            field_info.get("fields", {}),
            max_items
        )
        
        self._log(f"Extracted {len(items)} items")
        
        # Step 7: Filter if needed
        price_filter = task.get("filter", {}).get("max_price")
        if price_filter and isinstance(price_filter, (int, float)):
            items = [i for i in items if i.get("price", 0) <= price_filter]
            self._log(f"Filtered to {len(items)} items under {price_filter}")
        
        return {
            "items": items,
            "selector_used": best.get("selector"),
            "fields_detected": list(field_info.get("fields", {}).keys()),
            "candidates_evaluated": len(scored),
            "llm_calls": llm_calls,
            "task_interpretation": task
        }
    
    async def _extract_items(
        self,
        page,
        container_selector: str,
        field_selectors: Dict,
        max_items: int
    ) -> List[Dict]:
        """
        Extract items using detected selectors.
        
        Pure JavaScript extraction - no LLM.
        """
        return await page.evaluate("""
            (args) => {
                const containers = document.querySelectorAll(args.containerSelector);
                const items = [];
                const pricePattern = /(\\d+[\\d\\s]*[,.]\\d{2})\\s*(?:zł|PLN|€|\\$)/i;
                
                for (let i = 0; i < Math.min(containers.length, args.maxItems); i++) {
                    const el = containers[i];
                    const item = {};
                    
                    // Extract name
                    if (args.fields.name?.selector) {
                        try {
                            const nameEl = el.querySelector(args.fields.name.selector);
                            if (nameEl) item.name = nameEl.textContent?.trim().slice(0, 200);
                        } catch (e) {}
                    }
                    if (!item.name) {
                        // Fallback: longest text in heading/link
                        const textEls = el.querySelectorAll('h1, h2, h3, h4, a');
                        for (const t of textEls) {
                            const txt = t.textContent?.trim();
                            if (txt && txt.length > (item.name?.length || 0) && txt.length < 200) {
                                if (!pricePattern.test(txt)) item.name = txt;
                            }
                        }
                    }
                    
                    // Extract price
                    if (args.fields.price?.selector) {
                        try {
                            const priceEl = el.querySelector(args.fields.price.selector);
                            if (priceEl) {
                                const match = priceEl.textContent?.match(pricePattern);
                                if (match) {
                                    item.price = parseFloat(match[1].replace(/\\s/g, '').replace(',', '.'));
                                }
                            }
                        } catch (e) {}
                    }
                    if (!item.price) {
                        // Fallback: first price in container
                        const match = (el.textContent || '').match(pricePattern);
                        if (match) {
                            item.price = parseFloat(match[1].replace(/\\s/g, '').replace(',', '.'));
                        }
                    }
                    
                    // Extract URL
                    if (args.fields.url?.selector) {
                        try {
                            const urlEl = el.querySelector(args.fields.url.selector);
                            if (urlEl?.href) item.url = urlEl.href;
                        } catch (e) {}
                    }
                    if (!item.url) {
                        const link = el.querySelector('a[href]');
                        if (link?.href) item.url = link.href;
                    }
                    
                    // Extract image
                    if (args.fields.image?.selector) {
                        try {
                            const imgEl = el.querySelector(args.fields.image.selector);
                            if (imgEl?.src) item.image = imgEl.src;
                        } catch (e) {}
                    }
                    if (!item.image) {
                        const img = el.querySelector('img[src]');
                        if (img?.src) item.image = img.src;
                    }
                    
                    // Only add if we have at least name or url
                    if (item.name || item.url) {
                        items.push(item);
                    }
                }
                
                return items;
            }
        """, {
            "containerSelector": container_selector,
            "fields": field_selectors,
            "maxItems": max_items
        })
