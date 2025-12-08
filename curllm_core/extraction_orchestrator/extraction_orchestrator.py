import json
import time
from typing import Any, Dict, Optional, List


class ExtractionOrchestrator:
    """Multi-phase extraction orchestrator with full LLM transparency"""
    
    def __init__(self, llm, instruction: str, page, run_logger=None):
        self.llm = llm
        self.instruction = instruction
        self.page = page
        self.run_logger = run_logger
        self.phases_log = []
        
    async def orchestrate(self, page_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute 6-phase extraction orchestration:
        1. DETECTION - Detect extraction type (products, links, articles, etc.)
        2. STRATEGY - Plan extraction strategy (direct, navigate+extract, scroll+extract)
        3. NAVIGATION - Navigate to target pages if needed
        4. FORM FILLING - Apply filters (price, category, etc.) if needed
        5. EXTRACTION - Execute extraction using tools
        6. VALIDATION - Verify extracted data
        """
        try:
            self._log_header("🎭 TRANSPARENT EXTRACTION ORCHESTRATOR")
            
            # Phase 1: Detection
            detection = await self._phase_detection(page_context)
            if not detection:
                return None
                
            # Phase 2: Strategy
            strategy = await self._phase_strategy(page_context, detection)
            if not strategy:
                return None
            
            # Phase 3: Navigation (if needed)
            if strategy.get("requires_navigation"):
                nav_result = await self._phase_navigation(strategy)
                if not nav_result:
                    return None
                # Refresh page context after navigation
                page_context = await self._get_page_context()
            
            # Phase 4: Form Filling (apply filters if needed)
            if strategy.get("requires_form_fill"):
                form_result = await self._phase_form_filling(strategy, page_context)
                if form_result:
                    # Refresh page context after form submission
                    page_context = await self._get_page_context()
            
            # Phase 5: Extraction
            extraction = await self._phase_extraction(page_context, strategy)
            if not extraction:
                return None
            
            # Phase 6: Validation
            validation = await self._phase_validation(extraction, strategy)
            
            self._log_summary(validation)
            return extraction if validation.get("approved") else None
            
        except Exception as e:
            if self.run_logger:
                self.run_logger.log_text(f"❌ Extraction orchestrator failed: {e}")
            return None
    
    async def _phase_detection(self, page_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 1: Detect what type of data to extract"""
        self._log_phase(1, "Detection")
        
        prompt = self._build_detection_prompt(page_context)
        response = await self._llm_invoke(prompt)
        
        try:
            decision = json.loads(response)
            self._log_decision("Detection", decision)
            self.phases_log.append({"phase": "detection", "decision": decision})
            return decision
        except Exception as e:
            self._log_error("Detection", str(e))
            return None
    
    async def _phase_strategy(self, page_context: Dict[str, Any], detection: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 2: Plan extraction strategy"""
        self._log_phase(2, "Strategy")
        
        if detection is None:
            self._log_error("Strategy", "Detection is None - cannot proceed")
            return None
        
        prompt = self._build_strategy_prompt(page_context, detection)
        response = await self._llm_invoke(prompt)
        
        try:
            decision = json.loads(response)
            self._log_decision("Strategy", decision)
            self.phases_log.append({"phase": "strategy", "decision": decision})
            return decision
        except Exception as e:
            self._log_error("Strategy", str(e))
            return None
    
    async def _phase_navigation(self, strategy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 3: Navigate to target pages"""
        self._log_phase(3, "Navigation")
        
        nav_actions = strategy.get("navigation_actions", [])
        for action in nav_actions:
            action_type = action.get("type")
            if action_type == "click":
                # Support both href (URL) and selector
                href = action.get("href")
                selector = action.get("selector")
                
                try:
                    if href:
                        # Navigate directly to URL (handle encoding issues)
                        import urllib.parse
                        # Parse and re-encode URL to handle Polish characters properly
                        parsed = urllib.parse.urlparse(href)
                        # Re-encode path component
                        encoded_path = urllib.parse.quote(parsed.path.encode('utf-8'), safe='/:')
                        clean_url = f"{parsed.scheme}://{parsed.netloc}{encoded_path}"
                        if parsed.query:
                            clean_url += f"?{parsed.query}"
                        if parsed.fragment:
                            clean_url += f"#{parsed.fragment}"
                        
                        await self.page.goto(clean_url, wait_until="domcontentloaded", timeout=30000)
                        await self.page.wait_for_timeout(3000)  # Wait for dynamic content
                        self._log_decision("Navigation", {"action": "goto", "href": clean_url, "status": "success"})
                    elif selector:
                        # Click on selector
                        await self.page.click(selector, timeout=22000)
                        await self.page.wait_for_timeout(2000)
                        self._log_decision("Navigation", {"action": "click", "selector": selector, "status": "success"})
                    else:
                        self._log_error("Navigation", "Click action requires 'href' or 'selector'")
                        return None
                except Exception as e:
                    self._log_error("Navigation", f"Navigation failed: {e}")
                    return None
            elif action_type == "scroll":
                times = action.get("times", 3)
                try:
                    for i in range(times):
                        await self.page.evaluate("window.scrollBy(0, window.innerHeight);")
                        # Longer wait for first scroll to let content load
                        wait_time = 1500 if i == 0 else 800
                        await self.page.wait_for_timeout(wait_time)
                    self._log_decision("Navigation", {"action": "scroll", "times": times, "status": "success"})
                except Exception as e:
                    self._log_error("Navigation", f"Scroll failed: {e}")
        
        self.phases_log.append({"phase": "navigation", "actions": nav_actions})
        return {"success": True}
    
    async def _phase_form_filling(self, strategy: Dict[str, Any], page_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 4: Fill forms with filters (price, category, etc.)"""
        self._log_phase(4, "Form Filling")
        
        form_actions = strategy.get("form_actions", [])
        if not form_actions:
            return None
        
        for action in form_actions:
            field_name = action.get("field_name")
            value = action.get("value")
            action_type = action.get("action", "fill")  # fill, click, select
            
            try:
                if action_type == "fill":
                    # Try multiple selector strategies
                    selectors = [
                        f"input[name*='{field_name}' i]",
                        f"input[id*='{field_name}' i]",
                        f"input[placeholder*='{field_name}' i]",
                        f"input[type='text']",
                        f"input[type='number']"
                    ]
                    filled = False
                    for selector in selectors:
                        try:
                            elements = await self.page.query_selector_all(selector)
                            if elements:
                                await elements[0].fill(str(value))
                                filled = True
                                self._log_decision("Form Filling", {"action": "fill", "selector": selector, "value": value, "status": "success"})
                                break
                        except Exception:
                            continue
                    
                    if not filled:
                        self._log_error("Form Filling", f"Could not find field: {field_name}")
                
                elif action_type == "submit":
                    # Try to submit form
                    try:
                        # Look for submit button
                        submit_selectors = [
                            "button[type='submit']",
                            "input[type='submit']",
                            "button:has-text('Zastosuj')",
                            "button:has-text('Filtruj')",
                            "button:has-text('Apply')",
                            "button:has-text('Filter')"
                        ]
                        for selector in submit_selectors:
                            try:
                                await self.page.click(selector, timeout=5000)
                                await self.page.wait_for_timeout(3000)  # Wait for results to load
                                self._log_decision("Form Filling", {"action": "submit", "selector": selector, "status": "success"})
                                break
                            except Exception:
                                continue
                    except Exception as e:
                        self._log_error("Form Filling", f"Submit failed: {e}")
                
            except Exception as e:
                self._log_error("Form Filling", f"Form action failed: {e}")
        
        self.phases_log.append({"phase": "form_filling", "actions": form_actions})
        return {"success": True}
    
    async def _phase_extraction(self, page_context: Dict[str, Any], strategy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 5: Execute extraction"""
        self._log_phase(5, "Extraction")
        
        extraction_tool = strategy.get("extraction_tool")
        tool_args = strategy.get("tool_args", {})
        
        from .extraction import product_heuristics, extract_links_by_selectors, extract_articles_eval
        
        result = None
        count = 0
        try:
            if extraction_tool == "products.heuristics":
                result = await product_heuristics(self.instruction, self.page, self.run_logger)
                if result:
                    count = len(result.get("products", []))
            elif extraction_tool == "extract.links":
                # Use direct page evaluation for links
                links = await self.page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        return links.slice(0, 50).map(a => ({
                            text: a.innerText.trim(),
                            href: a.href
                        }));
                    }
                """)
                if links:
                    result = {"links": links}
                    count = len(links)
            elif extraction_tool == "articles.extract":
                articles = await extract_articles_eval(self.page)
                if articles:
                    result = {"articles": articles}
                    count = len(articles)
            
            if result and count > 0:
                self._log_decision("Extraction", {"tool": extraction_tool, "count": count, "status": "success"})
            else:
                self._log_decision("Extraction", {"tool": extraction_tool, "count": 0, "status": "empty"})
            
            self.phases_log.append({"phase": "extraction", "tool": extraction_tool, "result_count": count})
            return result
            
        except Exception as e:
            self._log_error("Extraction", str(e))
            return None
    
    async def _phase_validation(self, extraction: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 6: Validate extracted data"""
        self._log_phase(6, "Validation")
        
        prompt = self._build_validation_prompt(extraction, strategy)
        response = await self._llm_invoke(prompt)
        
        try:
            decision = json.loads(response)
            self._log_decision("Validation", decision)
            self.phases_log.append({"phase": "validation", "decision": decision})
            return decision
        except Exception as e:
            self._log_error("Validation", str(e))
            return {"approved": False, "reason": f"Validation failed: {e}"}
    
    # ========== Prompt Builders ==========
    
    def _build_detection_prompt(self, page_context: Dict[str, Any]) -> str:
        """Build prompt for detection phase - optimized with minimal context"""
        url = page_context.get("url", "")
        title = page_context.get("title", "")[:100]  # Limit title length
        
        # Extract key signals from instruction
        lower_instr = self.instruction.lower()
        has_products = any(k in lower_instr for k in ["product", "produkt", "price", "cena"])
        has_links = "link" in lower_instr
        has_articles = any(k in lower_instr for k in ["article", "artykuł", "title", "tytuł"])
        
        return f"""Analyze extraction task.

Instruction: {self.instruction}
URL: {url}
Title: {title}
Signals: products={has_products}, links={has_links}, articles={has_articles}

Respond JSON:
{{
  "extraction_type": "products|links|articles",
  "criteria": {{"price_limit": 150}},
  "reasoning": "brief"
}}

JSON:"""
    
    def _build_strategy_prompt(self, page_context: Dict[str, Any], detection: Dict[str, Any]) -> str:
        """Build prompt for strategy phase - optimized with minimal context"""
        url = page_context.get("url", "")
        # Limit to top 10 most relevant links
        links = (page_context.get("links") or [])[:10]
        headings = (page_context.get("headings") or [])[:3]
        
        # Build available links summary - compact format
        links_text_lines = []
        for i, link in enumerate(links[:8]):  # Top 8 only
            if isinstance(link, dict):
                text = str(link.get('text', ''))[:40]  # Shorter text
                href = str(link.get('href', ''))
                if href:  # Only include if href exists
                    links_text_lines.append(f"{i+1}. {text} -> {href}")
        links_text = "\n".join(links_text_lines) if links_text_lines else "(none)"
        
        # Safe extraction of price limit
        price_limit = 150
        try:
            criteria = detection.get('criteria')
            if isinstance(criteria, dict):
                price_limit = int(criteria.get('price_limit', 150))
        except:
            pass
        
        # Check if instruction mentions price filtering or limits
        lower_task = self.instruction.lower()
        needs_price_filter = any(keyword in lower_task for keyword in [
            "set price", "ustaw cen", "apply filter", "zastosuj filtr", "price filter", "filtr cen",
            "under", "poniżej", "below", "maksymalnie", "max", "do"  # Price limit keywords
        ]) and any(k in lower_task for k in ["price", "cena", "zł", "z\u0142"])
        
        return f"""Plan extraction strategy.

Task: {self.instruction}
URL: {url}
Type: {detection.get('extraction_type')}
Price limit: {price_limit}zł
Need filter: {needs_price_filter}

Links:
{links_text}

RULES:
1. Use EXACT href from links (not selectors)
2. If "set price filter" in task: set requires_form_fill=true
3. Scroll 6-8 times to load products

JSON response:
{{
  "requires_navigation": false,
  "navigation_actions": [{{"type": "scroll", "times": 8}}],
  "requires_form_fill": {str(needs_price_filter).lower()},
  "form_actions": [{{"field_name": "price_to", "value": {price_limit}, "action": "fill"}}, {{"action": "submit"}}],
  "extraction_tool": "products.heuristics",
  "tool_args": {{"threshold": {price_limit}}}
}}

JSON:"""
    
    def _build_validation_prompt(self, extraction: Dict[str, Any], strategy: Dict[str, Any]) -> str:
        """Build prompt for validation phase - optimized"""
        count = len(extraction.get("products") or extraction.get("links") or extraction.get("articles") or [])
        sample = str(extraction)[:300] if extraction else "empty"
        
        return f"""Validate extraction.

Task: {self.instruction}
Extracted: {count} items
Sample: {sample}

JSON:
{{
  "approved": {str(count > 0).lower()},
  "quality_score": 0.8,
  "reasoning": "brief"
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
    
    async def _get_page_context(self) -> Dict[str, Any]:
        """Get current page context"""
        from .page_context import extract_page_context
        return await extract_page_context(self.page, dom_max_chars=20000, include_dom=False)
    
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
    
    def _log_summary(self, validation: Dict[str, Any]):
        """Log orchestration summary"""
        if self.run_logger:
            self.run_logger.log_text(f"\n{'='*60}")
            self.run_logger.log_text(f"✅ Orchestration Complete")
            self.run_logger.log_text(f"   Phases: {len(self.phases_log)}")
            self.run_logger.log_text(f"   Approved: {validation.get('approved')}")
            self.run_logger.log_text(f"   Quality: {validation.get('quality_score', 'N/A')}")
            self.run_logger.log_text(f"{'='*60}\n")
