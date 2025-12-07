"""
Orchestrator - Execute task plans step by step

The main coordinator that:
1. Takes a natural language command
2. Parses it into structured format
3. Creates an execution plan
4. Executes each step with proper error handling
5. Logs everything for debugging
6. Returns structured results

Usage:
    orchestrator = Orchestrator()
    result = await orchestrator.execute(
        "Wejdź na example.com i wyślij formularz kontaktowy..."
    )
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

from .command_parser import CommandParser, ParsedCommand
from .task_planner import TaskPlanner, TaskPlan, TaskStep, StepType, StepStatus
from .url_resolver import UrlResolver, TaskGoal
from .stealth import StealthConfig
from .llm_element_finder import LLMElementFinder

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Result of a single step execution"""
    step_index: int
    step_type: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    screenshot_path: Optional[str] = None


@dataclass
class OrchestratorResult:
    """Final result of orchestration"""
    success: bool
    command: str
    parsed: Optional[ParsedCommand] = None
    plan: Optional[TaskPlan] = None
    step_results: List[StepResult] = field(default_factory=list)
    final_url: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    log_path: Optional[str] = None


@dataclass
class OrchestratorConfig:
    """Configuration for orchestrator"""
    headless: bool = True
    stealth_mode: bool = True
    timeout_seconds: int = 120
    screenshot_on_error: bool = True
    screenshot_on_success: bool = True
    log_to_file: bool = True
    log_dir: str = "logs"
    dry_run: bool = False  # Parse and plan only, don't execute


class Orchestrator:
    """
    Main orchestrator for executing complex commands.
    
    Example:
        orch = Orchestrator()
        result = await orch.execute(
            "Wejdź na prototypowanie.pl i wyślij wiadomość..."
        )
        
        if result.success:
            print(f"Form submitted successfully!")
        else:
            print(f"Failed: {result.error}")
    """
    
    def __init__(self, config: Optional[OrchestratorConfig] = None, llm=None):
        self.config = config or OrchestratorConfig()
        self.parser = CommandParser()
        self.planner = TaskPlanner()
        self.llm = llm  # LangChain-compatible LLM for intelligent element finding
        
        # Runtime state
        self.browser = None
        self.context = None
        self.page = None
        self.resolver = None
        self.element_finder = None  # LLMElementFinder instance
        self.run_log = []
        self.run_id = None
    
    async def execute(self, command: str) -> OrchestratorResult:
        """
        Execute a natural language command.
        
        Args:
            command: Natural language command
            
        Returns:
            OrchestratorResult with execution details
        """
        start_time = datetime.now()
        self.run_id = start_time.strftime("%Y%m%d-%H%M%S")
        self.run_log = []
        
        self._log("header", f"🚀 ORCHESTRATOR START: {self.run_id}")
        self._log("info", f"Command: {command[:100]}...")
        
        result = OrchestratorResult(
            success=False,
            command=command
        )
        
        try:
            # Phase 1: Parse command
            self._log("phase", "Phase 1: Parsing command")
            parsed = self.parser.parse(command)
            result.parsed = parsed
            
            self._log("info", f"Domain: {parsed.target_domain}")
            self._log("info", f"Goal: {parsed.primary_goal.value}")
            self._log("info", f"Confidence: {parsed.confidence:.0%}")
            
            if not parsed.target_domain:
                raise ValueError("Could not extract domain from command")
            
            # Phase 2: Create plan
            self._log("phase", "Phase 2: Creating execution plan")
            plan = self.planner.plan(parsed)
            result.plan = plan
            
            self._log("info", f"Plan: {len(plan.steps)} steps")
            for i, step in enumerate(plan.steps):
                self._log("step", f"  {i+1}. {step.step_type.value}: {step.description}")
            
            # Dry run mode - stop here
            if self.config.dry_run:
                self._log("info", "DRY RUN - stopping before execution")
                result.success = True
                return result
            
            # Phase 3: Setup browser
            self._log("phase", "Phase 3: Setting up browser")
            await self._setup_browser()
            
            # Phase 4: Execute plan
            self._log("phase", "Phase 4: Executing plan")
            step_results = await self._execute_plan(plan, parsed)
            result.step_results = step_results
            
            # Check results
            failed_steps = [r for r in step_results if not r.success and not plan.steps[r.step_index].optional]
            
            if failed_steps:
                result.success = False
                result.error = f"Step {failed_steps[0].step_index + 1} failed: {failed_steps[0].error}"
            else:
                result.success = True
            
            # Get final state
            if self.page:
                result.final_url = self.page.url
                
                # Extract any data from last extract step
                for sr in reversed(step_results):
                    if sr.step_type == "extract" and sr.data:
                        result.extracted_data = sr.data
                        break
            
        except Exception as e:
            logger.exception(f"Orchestration failed: {e}")
            result.error = str(e)
            self._log("error", f"Fatal error: {e}")
            
            # Screenshot on error
            if self.config.screenshot_on_error and self.page:
                try:
                    path = await self._take_screenshot("error")
                    self._log("info", f"Error screenshot: {path}")
                except Exception:
                    pass
        
        finally:
            # Cleanup
            await self._cleanup()
            
            # Calculate duration
            duration = datetime.now() - start_time
            result.duration_ms = int(duration.total_seconds() * 1000)
            
            self._log("header", f"🏁 ORCHESTRATOR END: {'SUCCESS' if result.success else 'FAILED'}")
            self._log("info", f"Duration: {duration.total_seconds():.1f}s")
            
            # Save log
            if self.config.log_to_file:
                log_path = self._save_log(result)
                result.log_path = log_path
        
        return result
    
    async def _setup_browser(self):
        """Setup browser with stealth using playwright directly"""
        from playwright.async_api import async_playwright
        
        self._playwright = await async_playwright().start()
        
        launch_args = {
            "headless": self.config.headless,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        }
        
        if self.config.stealth_mode:
            stealth = StealthConfig()
            launch_args["args"].extend(stealth.get_chrome_args())
        
        self.browser = await self._playwright.chromium.launch(**launch_args)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        
        self.page = await self.context.new_page()
        
        if self.config.stealth_mode:
            stealth = StealthConfig()
            await stealth.apply_to_context(self.context)
        
        self.resolver = UrlResolver(self.page, llm=self.llm)
        self.element_finder = LLMElementFinder(llm=self.llm, page=self.page)
        self._log("info", f"Browser ready (LLM: {'enabled' if self.llm else 'heuristic mode'})")
    
    async def _cleanup(self):
        """Cleanup browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, '_playwright') and self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")
    
    async def _execute_plan(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand
    ) -> List[StepResult]:
        """Execute all steps in the plan"""
        results = []
        
        for i, step in enumerate(plan.steps):
            self._log("step", f"Executing step {i+1}/{len(plan.steps)}: {step.step_type.value}")
            
            start = datetime.now()
            step_result = StepResult(
                step_index=i,
                step_type=step.step_type.value,
                success=False
            )
            
            try:
                # Check dependencies
                for dep_idx in step.depends_on:
                    if dep_idx < len(results) and not results[dep_idx].success:
                        if not plan.steps[dep_idx].optional:
                            raise Exception(f"Dependency step {dep_idx + 1} failed")
                
                # Execute step
                data = await self._execute_step(step, parsed)
                step_result.success = True
                step_result.data = data
                step.status = StepStatus.COMPLETED
                
                self._log("success", f"  ✅ {step.description}")
                
            except Exception as e:
                step_result.error = str(e)
                step.status = StepStatus.FAILED
                step.error = str(e)
                
                self._log("error", f"  ❌ {step.description}: {e}")
                
                # Try fallback
                if step.fallback:
                    self._log("info", f"  Trying fallback...")
                    try:
                        data = await self._execute_step(step.fallback, parsed)
                        step_result.success = True
                        step_result.data = data
                        step.status = StepStatus.COMPLETED
                        self._log("success", f"  ✅ Fallback succeeded")
                    except Exception as fe:
                        self._log("error", f"  ❌ Fallback failed: {fe}")
                
                # Stop if required step failed
                if not step.optional and not step_result.success:
                    if plan.stop_on_failure:
                        self._log("error", "Stopping due to required step failure")
                        results.append(step_result)
                        break
            
            finally:
                duration = datetime.now() - start
                step_result.duration_ms = int(duration.total_seconds() * 1000)
            
            results.append(step_result)
        
        return results
    
    async def _execute_step(
        self,
        step: TaskStep,
        parsed: ParsedCommand
    ) -> Optional[Dict[str, Any]]:
        """Execute a single step"""
        
        step_type = step.step_type
        params = step.params
        
        if step_type == StepType.NAVIGATE:
            url = params.get("url")
            await self.page.goto(url, wait_until="domcontentloaded", timeout=step.timeout_ms)
            return {"url": self.page.url}
        
        elif step_type == StepType.RESOLVE:
            goal_str = params.get("goal")
            goal = TaskGoal(goal_str) if goal_str else TaskGoal.GENERIC
            result = await self.resolver.resolve_for_goal(self.page.url, goal)
            return {
                "resolved_url": result.resolved_url,
                "success": result.success,
                "method": result.resolution_method
            }
        
        elif step_type == StepType.ANALYZE:
            # Analyze page structure
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
        
        elif step_type == StepType.WAIT:
            ms = params.get("ms", 1000)
            await asyncio.sleep(ms / 1000)
            return {"waited_ms": ms}
        
        elif step_type == StepType.SEARCH:
            query = params.get("query", "")
            
            # Use LLM Element Finder to locate search input
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
                # Clear and fill using intelligent typing
                await search_input.click()
                await search_input.fill("")
                await search_input.type(query, delay=50)
                await asyncio.sleep(300)
                
                # Submit search
                await self.page.keyboard.press("Enter")
                
                # Wait for navigation or results
                try:
                    await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    await asyncio.sleep(2000)
                
                return {
                    "query": query, 
                    "filled": True, 
                    "url": self.page.url,
                    "method": "llm" if self.llm else "heuristic",
                    "selector": search_match.selector if search_match else None
                }
            else:
                # Try URL-based search as fallback
                from urllib.parse import urljoin, quote_plus
                current_url = self.page.url
                search_url = urljoin(current_url, f"/search?q={quote_plus(query)}")
                try:
                    await self.page.goto(search_url, timeout=10000)
                    return {"query": query, "filled": False, "fallback": "url", "url": self.page.url}
                except Exception:
                    pass
            
            return {"query": query, "filled": False, "url": self.page.url}
        
        elif step_type == StepType.FILL_FIELD:
            value = params.get("value", "")
            field_type = params.get("field_type", "")
            
            # Use LLM Element Finder to locate the field
            self._log("step", f"  🔍 Finding {field_type} field using {'LLM' if self.llm else 'heuristics'}...")
            
            field_match = await self.element_finder.find_form_field(
                field_purpose=field_type,
                value_to_fill=value
            )
            
            if field_match and field_match.selector:
                self._log("step", f"  Found: {field_match.selector} (confidence: {field_match.confidence:.0%})")
                try:
                    el = await self.page.query_selector(field_match.selector)
                    if el:
                        await el.scroll_into_view_if_needed()
                        if await el.is_visible():
                            await el.click()
                            await el.fill("")
                            await el.type(value, delay=30)
                            return {
                                "selector": field_match.selector,
                                "filled": True,
                                "value": value[:20],
                                "method": "llm" if self.llm else "heuristic",
                                "confidence": field_match.confidence
                            }
                except Exception as e:
                    self._log("step", f"  Fill failed: {e}")
            
            raise Exception(f"Could not find {field_type} field")
        
        elif step_type == StepType.FILL_FORM:
            # Fill multiple fields using LLM Element Finder
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
        
        elif step_type == StepType.CLICK:
            selector = params.get("selector", "")
            await self.page.click(selector, timeout=step.timeout_ms)
            return {"clicked": selector}
        
        elif step_type == StepType.SUBMIT:
            wait_after = params.get("wait_after_ms", 2000)
            form_context = params.get("form_context", "form")
            
            # Use LLM Element Finder to locate submit button
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
        
        elif step_type == StepType.EXTRACT:
            extract_type = params.get("type", "page_content")
            
            if extract_type == "products":
                # Use intelligent extraction - analyze visible products on page
                products = await self.page.evaluate("""
                    () => {
                        // Find product containers using multiple strategies
                        const strategies = [
                            // Common class patterns
                            '[class*="product"]',
                            '[class*="offer"]', 
                            '[class*="item"]',
                            '[class*="card"]',
                            // Data attributes
                            '[data-product]',
                            '[data-offer]',
                            // List items in product grids
                            '.products li',
                            '.catalog li',
                            '.listing li',
                        ];
                        
                        let items = [];
                        for (const sel of strategies) {
                            const found = document.querySelectorAll(sel);
                            if (found.length > items.length) {
                                items = Array.from(found);
                            }
                        }
                        
                        // Score and filter: real products have price-like text
                        const priceRegex = /\\d+[,.]\\d{2}\\s*(zł|PLN|EUR|USD|€|\\$)/i;
                        
                        return items
                            .filter(el => el.offsetParent !== null)  // visible
                            .filter(el => priceRegex.test(el.innerText))  // has price
                            .slice(0, 20)
                            .map(el => ({
                                text: el.innerText.slice(0, 300).replace(/\\s+/g, ' '),
                                link: el.querySelector('a')?.href,
                                hasPrice: true
                            }));
                    }
                """)
                return {"products": products, "count": len(products), "method": "intelligent"}
            
            elif extract_type == "cart_items":
                cart = await self.page.evaluate("""
                    () => ({
                        items: document.querySelectorAll('[class*="cart-item"], [class*="basket-item"]').length,
                        total: document.querySelector('[class*="total"], [class*="sum"]')?.innerText
                    })
                """)
                return cart
            
            else:
                content = await self.page.evaluate("() => document.body.innerText.slice(0, 5000)")
                return {"content": content}
        
        elif step_type == StepType.VERIFY:
            expected = params.get("expected", "")
            # Simple verification - check page content
            content = await self.page.evaluate("() => document.body.innerText.toLowerCase()")
            
            success_indicators = ["dziękujemy", "thank", "sukces", "success", "wysłano", "sent"]
            is_success = any(ind in content for ind in success_indicators)
            
            return {"verified": is_success, "expected": expected}
        
        elif step_type == StepType.SCREENSHOT:
            name = params.get("name", "screenshot")
            path = await self._take_screenshot(name)
            return {"path": path}
        
        else:
            raise Exception(f"Unknown step type: {step_type}")
    
    async def _take_screenshot(self, name: str) -> str:
        """Take screenshot and return path"""
        os.makedirs(self.config.log_dir, exist_ok=True)
        path = os.path.join(self.config.log_dir, f"{self.run_id}-{name}.png")
        await self.page.screenshot(path=path)
        return path
    
    def _log(self, level: str, message: str):
        """Add entry to run log"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        if level == "header":
            self.run_log.append(f"\n{'='*60}")
            self.run_log.append(f"{message}")
            self.run_log.append(f"{'='*60}")
        elif level == "phase":
            self.run_log.append(f"\n## {message}")
        elif level == "step":
            self.run_log.append(f"[{timestamp}] {message}")
        elif level == "success":
            self.run_log.append(f"[{timestamp}] {message}")
        elif level == "error":
            self.run_log.append(f"[{timestamp}] ❌ {message}")
        else:
            self.run_log.append(f"[{timestamp}] {message}")
        
        # Also log to Python logger
        if level == "error":
            logger.error(message)
        else:
            logger.info(message)
    
    def _save_log(self, result: OrchestratorResult) -> str:
        """Save run log to markdown file"""
        os.makedirs(self.config.log_dir, exist_ok=True)
        log_path = os.path.join(self.config.log_dir, f"run-{self.run_id}.md")
        
        with open(log_path, "w") as f:
            f.write(f"# Orchestrator Run: {self.run_id}\n\n")
            f.write(f"**Status:** {'✅ SUCCESS' if result.success else '❌ FAILED'}\n")
            f.write(f"**Duration:** {result.duration_ms}ms\n\n")
            
            # Full CLI command
            f.write("## CLI Command\n")
            escaped_cmd = result.command.replace('"', '\\"')
            f.write(f"```bash\ncurllm \"{escaped_cmd}\"\n```\n\n")
            
            # Show equivalent traditional format
            if result.parsed and result.parsed.target_domain:
                url = result.parsed.get_url()
                f.write("## Equivalent Traditional Format\n")
                f.write(f"```bash\ncurllm \"{url}\" -d \"{escaped_cmd}\"\n```\n\n")
                f.write(f"- **URL**: {url}\n")
                f.write(f"- **Instruction**: {result.command}\n\n")
            
            if result.parsed:
                f.write("## Parsed\n")
                f.write(f"- **Domain:** {result.parsed.target_domain}\n")
                f.write(f"- **Goal:** {result.parsed.primary_goal.value}\n")
                f.write(f"- **Email:** {result.parsed.form_data.email}\n")
                f.write(f"- **Name:** {result.parsed.form_data.name}\n")
                f.write(f"- **Confidence:** {result.parsed.confidence:.0%}\n\n")
            
            if result.plan:
                f.write("## Plan\n")
                for i, step in enumerate(result.plan.steps):
                    status = "✅" if step.status == StepStatus.COMPLETED else "❌" if step.status == StepStatus.FAILED else "⏳"
                    f.write(f"{i+1}. {status} {step.step_type.value}: {step.description}\n")
                f.write("\n")
            
            # Step execution times
            if result.step_results:
                f.write("## Step Execution Times\n")
                f.write("| Step | Description | Duration | Status |\n")
                f.write("|------|-------------|----------|--------|\n")
                for sr in result.step_results:
                    status = "✅" if sr.success else "❌"
                    f.write(f"| {sr.step_index + 1} | {sr.step_type} | {sr.duration_ms}ms | {status} |\n")
                f.write("\n")
            
            # Final URL
            if result.final_url:
                f.write(f"## Final URL\n`{result.final_url}`\n\n")
            
            f.write("## Execution Log\n")
            f.write("```\n")
            f.write("\n".join(self.run_log))
            f.write("\n```\n")
            
            if result.error:
                f.write(f"\n## Error\n```\n{result.error}\n```\n")
            
            if result.extracted_data:
                f.write(f"\n## Extracted Data\n```json\n{json.dumps(result.extracted_data, indent=2, ensure_ascii=False)}\n```\n")
        
        logger.info(f"Log saved: {log_path}")
        return log_path


async def execute_command(
    command: str,
    config: Optional[OrchestratorConfig] = None
) -> OrchestratorResult:
    """Convenience function to execute a command"""
    orchestrator = Orchestrator(config)
    return await orchestrator.execute(command)
