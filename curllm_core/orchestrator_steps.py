"""
Orchestrator Step Executors - Modular step execution logic

This module contains individual step executors for the Orchestrator.
Each step type has its own executor function for better maintainability.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime

from .task_planner import StepType, TaskStep
from .command_parser import ParsedCommand
from .url_types import TaskGoal

logger = logging.getLogger(__name__)


class StepExecutor:
    """
    Executes individual orchestrator steps.
    
    Separates step execution logic from the main Orchestrator class
    for better testability and maintainability.
    """
    
    def __init__(self, page, resolver, element_finder, llm=None, log_fn=None):
        self.page = page
        self.resolver = resolver
        self.element_finder = element_finder
        self.llm = llm
        self._log = log_fn or (lambda *args: None)
    
    async def execute(
        self,
        step: TaskStep,
        parsed: ParsedCommand
    ) -> Optional[Dict[str, Any]]:
        """Execute a single step and return result data"""
        
        step_type = step.step_type
        params = step.params
        
        # Route to appropriate executor
        executors = {
            StepType.NAVIGATE: self._execute_navigate,
            StepType.RESOLVE: self._execute_resolve,
            StepType.ANALYZE: self._execute_analyze,
            StepType.WAIT: self._execute_wait,
            StepType.SEARCH: self._execute_search,
            StepType.FILL_FIELD: self._execute_fill_field,
            StepType.FILL_FORM: self._execute_fill_form,
            StepType.CLICK: self._execute_click,
            StepType.SUBMIT: self._execute_submit,
            StepType.EXTRACT: self._execute_extract,
            StepType.VERIFY: self._execute_verify,
            StepType.SCREENSHOT: self._execute_screenshot,
        }
        
        executor = executors.get(step_type)
        if executor:
            return await executor(step, parsed, params)
        else:
            raise Exception(f"Unknown step type: {step_type}")
    
    async def _execute_navigate(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Navigate to URL"""
        url = params.get("url")
        await self.page.goto(url, wait_until="domcontentloaded", timeout=step.timeout_ms)
        return {"url": self.page.url}
    
    async def _execute_resolve(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Resolve URL for a specific goal"""
        goal_str = params.get("goal")
        goal = TaskGoal(goal_str) if goal_str else TaskGoal.GENERIC
        result = await self.resolver.resolve_for_goal(self.page.url, goal)
        return {
            "resolved_url": result.resolved_url,
            "success": result.success,
            "method": result.resolution_method
        }
    
    async def _execute_analyze(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Analyze page structure"""
        page_info = await self.page.evaluate("""
            () => ({
                title: document.title,
                url: location.href,
                forms: document.querySelectorAll('form').length,
                inputs: document.querySelectorAll('input, textarea').length,
                products: document.querySelectorAll('[class*="product"], [class*="offer"]').length
            })
        """)
        return page_info
    
    async def _execute_wait(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Wait for specified time"""
        ms = params.get("ms", 1000)
        await asyncio.sleep(ms / 1000)
        return {"waited_ms": ms}
    
    async def _execute_search(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Fill search input and submit"""
        query = params.get("query", "")
        
        self._log("step", f"  🔍 Finding search input using {'LLM' if self.llm else 'heuristics'}...")
        
        search_match = await self.element_finder.find_search_input()
        search_input = None
        
        if search_match and search_match.selector:
            self._log("step", f"  Found: {search_match.selector} (confidence: {search_match.confidence:.0%})")
            try:
                search_input = await self.page.query_selector(search_match.selector)
                if search_input and not await search_input.is_visible():
                    await search_input.scroll_into_view_if_needed()
            except Exception as e:
                self._log("step", f"  Selector failed: {e}")
        
        if search_input:
            await search_input.click()
            await search_input.fill("")
            await search_input.type(query, delay=50)
            await asyncio.sleep(0.3)
            await self.page.keyboard.press("Enter")
            
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                await asyncio.sleep(2)
            
            return {
                "query": query,
                "filled": True,
                "url": self.page.url,
                "method": "llm" if self.llm else "heuristic",
                "selector": search_match.selector if search_match else None
            }
        else:
            raise Exception("Could not find search input")
    
    async def _execute_fill_field(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """
        Fill a single form field using LLM-DSL approach.
        
        Dynamically resolves field values from parsed.form_data using getattr
        instead of hardcoded field mappings.
        """
        field_type = params.get("field_type", "text")
        value = params.get("value", "")
        
        # Dynamic value resolution from parsed.form_data (no hardcoded field names)
        if not value and parsed.form_data:
            # Try to get value dynamically by field_type attribute name
            value = getattr(parsed.form_data, field_type, None) or ""
            
            # Fallback: use original instruction for message-like fields
            if not value and field_type in {"message", "description", "content", "text"}:
                value = parsed.form_data.message if hasattr(parsed.form_data, 'message') else ""
                if not value:
                    value = parsed.original_instruction
        
        self._log("step", f"  🔍 Finding {field_type} field using {'LLM' if self.llm else 'heuristics'}...")
        
        field_match = await self.element_finder.find_form_field(
            field_purpose=field_type,
            value_to_fill=value
        )
        
        if field_match and field_match.selector:
            self._log("step", f"  Found: {field_match.selector} (confidence: {field_match.confidence:.0%})")
            try:
                el = await self.page.query_selector(field_match.selector)
                if el and await el.is_visible():
                    input_type = (await el.get_attribute("type")) or ""
                    input_type = input_type.lower()
                    # Checkbox / radio: treat as toggle, not text fill
                    if input_type in {"checkbox", "radio"}:
                        is_checked = False
                        try:
                            is_checked = await el.is_checked()
                        except Exception:
                            # Some elements may not support is_checked; ignore
                            pass
                        if not is_checked:
                            # Try multiple strategies for clicking checkbox
                            clicked = False
                            
                            # Strategy 1: JavaScript click (most reliable, bypasses overlay)
                            try:
                                await el.evaluate("el => el.click()")
                                clicked = True
                                logger.debug("Checkbox clicked via JS")
                            except Exception as e:
                                logger.debug(f"JS click failed: {e}")
                            
                            # Strategy 2: Click parent label (for nested checkboxes)
                            if not clicked:
                                try:
                                    parent_label = await el.evaluate_handle("el => el.closest('label')")
                                    if parent_label:
                                        await parent_label.as_element().click(timeout=3000)
                                        clicked = True
                                        logger.debug("Checkbox clicked via parent label")
                                except Exception as e:
                                    logger.debug(f"Parent label click failed: {e}")
                            
                            # Strategy 3: Click label with for attribute
                            if not clicked:
                                el_id = await el.get_attribute("id")
                                if el_id:
                                    label = await self.page.query_selector(f'label[for="{el_id}"]')
                                    if label:
                                        try:
                                            await label.click(timeout=3000)
                                            clicked = True
                                        except Exception:
                                            pass
                            
                            # Strategy 4: Force click as last resort
                            if not clicked:
                                await el.click(force=True, timeout=5000)
                    else:
                        await el.click()
                        await el.fill(value)
                    return {
                        "field": field_type,
                        "filled": True,
                        "selector": field_match.selector,
                        "method": "llm" if self.llm else "heuristic"
                    }
            except Exception as e:
                self._log("step", f"  Fill failed: {e}")
        
        # Determine if field is optional using semantic analysis (no hardcoded list)
        # Required fields typically: email (core identifier)
        # Optional: anything else that's not strictly required for contact
        is_required = field_type in {"email"}  # Minimal - only email is truly required
        
        # Use LLM to determine if field is required (if available)
        if self.llm and not is_required:
            try:
                prompt = f"Is '{field_type}' a required field for a contact form? Answer only YES or NO."
                response = await self.llm.aquery(prompt)
                is_required = "YES" in response.upper()
            except Exception:
                pass
        
        if not is_required:
            self._log("step", f"  ⚠️ Optional field {field_type} not found, skipping")
            return {"field": field_type, "filled": False, "skipped": True}
        
        raise Exception(f"Could not find required {field_type} field")
    
    async def _execute_fill_form(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Fill multiple form fields"""
        form_data = params.get("data", {})
        filled = []
        
        for field_name, value in form_data.items():
            field_match = await self.element_finder.find_form_field(
                field_purpose=field_name,
                value_to_fill=value
            )
            
            if field_match and field_match.selector:
                try:
                    el = await self.page.query_selector(field_match.selector)
                    if el and await el.is_visible():
                        await el.fill(value)
                        filled.append(field_name)
                except Exception:
                    continue
        
        return {"filled_fields": filled, "method": "llm" if self.llm else "heuristic"}
    
    async def _execute_click(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Click an element"""
        selector = params.get("selector", "")
        await self.page.click(selector, timeout=step.timeout_ms)
        return {"clicked": selector}
    
    async def _execute_submit(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Find and click submit button"""
        wait_after = params.get("wait_after_ms", 2000)
        form_context = params.get("form_context", "form")
        
        self._log("step", f"  🔍 Finding submit button using {'LLM' if self.llm else 'heuristics'}...")
        
        button_match = await self.element_finder.find_submit_button(form_context)
        
        if button_match and button_match.selector:
            self._log("step", f"  Found: {button_match.selector} (confidence: {button_match.confidence:.0%})")
            try:
                el = await self.page.query_selector(button_match.selector)
                if el and await el.is_visible():
                    await el.click()
                    await asyncio.sleep(wait_after / 1000)
                    return {
                        "submitted": True,
                        "selector": button_match.selector,
                        "method": "llm" if self.llm else "heuristic"
                    }
            except Exception as e:
                self._log("step", f"  Submit failed: {e}")
        
        raise Exception("Could not find submit button")
    
    async def _execute_extract(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Extract data from page"""
        extract_type = params.get("type", "page_content")
        
        if extract_type == "products":
            from .iterative_extractor import extract_products_iteratively
            products = await extract_products_iteratively(self.page, max_items=50)
            return {"products": products, "count": len(products)}
        
        elif extract_type == "links":
            links = await self.page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    href: a.href,
                    text: a.innerText.trim().slice(0, 100)
                })).slice(0, 100)
            """)
            return {"links": links, "count": len(links)}
        
        elif extract_type == "forms":
            forms = await self.page.evaluate("""
                () => Array.from(document.querySelectorAll('form')).map(f => ({
                    id: f.id,
                    action: f.action,
                    method: f.method,
                    fields: f.querySelectorAll('input, textarea, select').length
                }))
            """)
            return {"forms": forms, "count": len(forms)}
        
        elif extract_type == "pricing":
            pricing = await self.page.evaluate(r"""
                () => {
                    const pricePatterns = [
                        /(\d+[\s,.]?\d*)\s*(zł|PLN|EUR|€|\$|USD)/gi,
                        /(zł|PLN|EUR|€|\$|USD)\s*(\d+[\s,.]?\d*)/gi
                    ];
                    const text = document.body.innerText;
                    const prices = [];
                    for (const pattern of pricePatterns) {
                        const matches = text.matchAll(pattern);
                        for (const m of matches) {
                            prices.push(m[0]);
                        }
                    }
                    return [...new Set(prices)].slice(0, 50);
                }
            """)
            return {"pricing": pricing, "count": len(pricing), "method": "intelligent"}
        
        else:
            content = await self.page.evaluate("() => document.body.innerText.slice(0, 5000)")
            return {"content": content}
    
    async def _execute_verify(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """
        Verify page state using LLM-DSL approach.
        
        Uses LLM to semantically analyze page content for success/error/security indicators
        instead of hardcoded selectors and keyword lists.
        """
        expected = params.get("expected", "")
        strict = params.get("strict", False)
        verify_type = params.get("verify_type", "submit")
        
        # Get page content for analysis
        page_text = await self.page.evaluate("() => document.body.innerText.substring(0, 3000)")
        
        # LLM-based verification if available
        if self.llm:
            try:
                prompt = f"""Analyze this webpage text after a form submission attempt.

Page content:
{page_text[:2000]}

Determine:
1. SUCCESS: Is there a success/thank you message? (e.g., "dziękujemy", "wysłano", "thank you")
2. ERROR: Is there a form error message? (e.g., "wymagane", "required", "błąd")
3. SECURITY: Is there a CAPTCHA or security block? (e.g., "captcha", "robot", "weryfikacja")

Reply with exactly one line in format:
RESULT: [SUCCESS|ERROR|SECURITY|UNKNOWN] - [brief reason]"""

                response = await self.llm.aquery(prompt)
                response_text = response.strip().upper()
                
                if "SUCCESS" in response_text:
                    is_verified = True
                    reason = "llm_detected_success"
                elif "ERROR" in response_text:
                    is_verified = False
                    reason = "llm_detected_error"
                elif "SECURITY" in response_text:
                    is_verified = False
                    reason = "llm_detected_security"
                else:
                    is_verified = False
                    reason = "llm_uncertain"
                
                self._log("step", f"  📋 LLM Verification:")
                self._log("step", f"     LLM response: {response[:100]}")
                self._log("step", f"     Result: {'✅ VERIFIED' if is_verified else '⚠️ NOT VERIFIED'} ({reason})")
                
                return {
                    "verified": is_verified,
                    "reason": reason,
                    "llm_response": response[:200],
                    "method": "llm"
                }
            except Exception as e:
                logger.debug(f"LLM verification failed: {e}, falling back to heuristic")
        
        # Fallback: Semantic heuristic analysis (no hardcoded selectors)
        content_lower = page_text.lower()
        
        # Dynamic success detection via DOM analysis
        success_element = await self.page.evaluate("""
            () => {
                // Find any visible element that appeared after form submit
                // Look for elements with success-like styling or content
                const allElements = document.querySelectorAll('*');
                for (const el of allElements) {
                    if (!el.innerText || el.innerText.length < 5) continue;
                    const text = el.innerText.toLowerCase();
                    const style = window.getComputedStyle(el);
                    
                    // Skip hidden elements
                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                    
                    // Check for success-like content (semantic, not selector-based)
                    const successWords = ['dzięk', 'thank', 'wysłan', 'sent', 'success', 'otrzym'];
                    const hasSuccessWord = successWords.some(w => text.includes(w));
                    
                    // Check for success-like styling (green color, etc.)
                    const hasSuccessStyle = style.color.includes('0, 128') || 
                                           style.backgroundColor.includes('0, 128') ||
                                           el.className.toLowerCase().includes('success');
                    
                    if (hasSuccessWord || hasSuccessStyle) {
                        return text.substring(0, 200);
                    }
                }
                return null;
            }
        """)
        
        # Semantic analysis of page content
        has_success = bool(success_element)
        has_error = any(w in content_lower for w in ['wymagan', 'required', 'błąd', 'error', 'nieprawidł'])
        has_security = any(w in content_lower for w in ['captcha', 'robot', 'weryfikacj', 'cloudflare'])
        
        if has_security:
            is_verified = False
            reason = "security_block"
        elif has_success and not has_error:
            is_verified = True
            reason = "success"
        elif has_error:
            is_verified = False
            reason = "form_error"
        else:
            is_verified = False
            reason = "no_confirmation"
        
        self._log("step", f"  📋 Verification check:")
        self._log("step", f"     Success element found: {bool(success_element)}")
        self._log("step", f"     Error indicators found: {has_error}")
        self._log("step", f"     Security block detected: {has_security}")
        self._log("step", f"     Result: {'✅ VERIFIED' if is_verified else '⚠️ NOT VERIFIED'} ({reason})")
        
        if strict and not is_verified:
            raise Exception(f"Verification failed: {reason}")
        
        return {
            "verified": is_verified,
            "has_success": has_success,
            "has_error": has_error,
            "has_security": has_security,
            "reason": reason,
            "method": "heuristic"
        }
    
    async def _execute_screenshot(
        self, step: TaskStep, parsed: ParsedCommand, params: Dict
    ) -> Dict[str, Any]:
        """Take screenshot"""
        name = params.get("name", "screenshot")
        # Screenshot logic is handled by the orchestrator
        return {"name": name, "requested": True}
