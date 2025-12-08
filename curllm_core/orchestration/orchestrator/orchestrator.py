import asyncio
import logging
import os
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path
from curllm_core.command_parser import CommandParser, ParsedCommand
from curllm_core.task_planner import TaskPlanner, TaskPlan, TaskStep, StepType, StepStatus
from curllm_core.url_resolver import UrlResolver
from curllm_core.url_types import TaskGoal
from curllm_core.stealth import StealthConfig
from curllm_core.llm_element_finder import LLMElementFinder
from curllm_core.orchestrator_steps import StepExecutor
from curllm_core.result_validator import ResultValidator, ValidationLevel, ValidationResult

from .step_result import StepResult
from .orchestrator_result import OrchestratorResult
from .orchestrator_config import OrchestratorConfig

try:
    # Optional structured logging package
    from curllm_logs import (
        LogEntry,
        LogLevel,
        StepLog,
        CommandInfo,
        EnvironmentInfo,
        ResultInfo,
        LogSession,
        create_session,
        MarkdownLogWriter,
        ScreenshotManager,
    )
    HAS_LOG_PACKAGE = True
except Exception:  # pragma: no cover - optional dependency
    HAS_LOG_PACKAGE = False
    LogEntry = LogLevel = StepLog = None
    CommandInfo = EnvironmentInfo = ResultInfo = None
    LogSession = create_session = None
    MarkdownLogWriter = None
    ScreenshotManager = None


logger = logging.getLogger(__name__)

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
        self.screenshot_manager = None  # ScreenshotManager from curllm_logs
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
                # Check verification step result if it exists
                verification_passed = True
                verification_reason = None
                for sr in step_results:
                    if sr.step_type == "verify" and sr.data:
                        verified = sr.data.get("verified", True)
                        has_error = sr.data.get("has_error_indicator", False)
                        has_security = sr.data.get("has_security_block", False)
                        verification_reason = sr.data.get("reason", "unknown")
                        
                        if not verified:
                            verification_passed = False
                            self._log("warning", f"⚠️ Verification failed: {verification_reason}")
                            break
                
                if verification_passed:
                    result.success = True
                elif verification_reason == "security_block" and self.config.auto_captcha_visible and self.config.headless:
                    # CAPTCHA detected - retry with visible browser
                    self._log("warning", "🔒 CAPTCHA detected! Switching to visible mode for manual solving...")
                    
                    await self._cleanup()
                    
                    # Re-run with visible browser
                    original_headless = self.config.headless
                    self.config.headless = False
                    
                    try:
                        result = await self._execute_with_captcha_handling(command, parsed, plan)
                    finally:
                        self.config.headless = original_headless
                else:
                    result.success = False
                    # Provide specific error messages
                    error_messages = {
                        "security_block": "Form blocked by CAPTCHA/security check",
                        "form_error": "Form validation error (missing required fields)",
                        "no_confirmation": "No success confirmation found on page",
                    }
                    result.error = error_messages.get(verification_reason, f"Verification failed: {verification_reason}")
            
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
        
        # Initialize step executor for modular step handling
        self.step_executor = StepExecutor(
            page=self.page,
            resolver=self.resolver,
            element_finder=self.element_finder,
            llm=self.llm,
            log_fn=self._log
        )
        
        # Initialize result validator
        self.result_validator = ResultValidator(ValidationLevel.NORMAL)
        
        # Initialize screenshot manager from curllm_logs
        if HAS_LOG_PACKAGE and ScreenshotManager:
            self.screenshot_manager = ScreenshotManager(
                base_dir=self.config.screenshot_dir,
                session_id=self.run_id,
                domain="unknown"  # Will be updated after parsing
            )
        
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
    
    async def _execute_with_captcha_handling(
        self,
        command: str,
        parsed: ParsedCommand,
        plan: TaskPlan
    ) -> OrchestratorResult:
        """
        Execute plan in visible mode with CAPTCHA handling.
        
        Opens visible browser, navigates to form, and waits for user
        to solve CAPTCHA before continuing.
        """
        result = OrchestratorResult(success=False, command=command)
        result.parsed = parsed
        result.plan = plan
        
        try:
            self._log("phase", "Phase 5: Retry with visible browser (CAPTCHA mode)")
            await self._setup_browser()
            
            # Execute navigation and resolve steps first
            for i, step in enumerate(plan.steps):
                if step.step_type.value in ["navigate", "resolve", "analyze"]:
                    self._log("step", f"Executing step {i+1}/{len(plan.steps)}: {step.step_type.value}")
                    await self.step_executor.execute(step, parsed)
                    self._log("success", f"  ✅ {step.description}")
            
            # Now wait for user to solve CAPTCHA
            self._log("warning", "")
            self._log("warning", "=" * 60)
            self._log("warning", "🔒 CAPTCHA DETECTED - MANUAL ACTION REQUIRED")
            self._log("warning", "=" * 60)
            self._log("warning", f"Please solve the CAPTCHA in the browser window.")
            self._log("warning", f"You have {self.config.captcha_wait_seconds} seconds.")
            self._log("warning", "The form will be re-submitted after CAPTCHA is solved.")
            self._log("warning", "=" * 60)
            
            print("\n" + "=" * 60)
            print("🔒 CAPTCHA DETECTED - MANUAL ACTION REQUIRED")
            print("=" * 60)
            print(f"1. A browser window should be visible")
            print(f"2. Solve the CAPTCHA/verification challenge")
            print(f"3. Wait - the script will continue automatically")
            print(f"   (timeout: {self.config.captcha_wait_seconds}s)")
            print("=" * 60 + "\n")
            
            # Wait for page changes (CAPTCHA solved indicator)
            captcha_solved = False
            wait_interval = 2
            waited = 0
            
            while waited < self.config.captcha_wait_seconds:
                await asyncio.sleep(wait_interval)
                waited += wait_interval
                
                # Check if CAPTCHA indicators disappeared
                content = await self.page.evaluate("() => document.body.innerText.toLowerCase()")
                security_indicators = [
                    "captcha", "recaptcha", "kod jednorazowy", "nonce",
                    "robot", "weryfikacja", "verification code",
                    "nieprawidłowy kod", "nieprawidlowy kod"
                ]
                
                still_has_captcha = any(ind in content for ind in security_indicators)
                
                if not still_has_captcha:
                    self._log("success", "✅ CAPTCHA appears to be solved!")
                    captcha_solved = True
                    break
                
                # Show progress
                remaining = self.config.captcha_wait_seconds - waited
                if remaining > 0 and remaining % 10 == 0:
                    print(f"   Waiting... {remaining}s remaining")
            
            if not captcha_solved:
                self._log("warning", "⏰ CAPTCHA timeout - continuing anyway...")
            
            # Re-fill and submit form
            self._log("phase", "Phase 6: Re-submitting form after CAPTCHA")
            
            for i, step in enumerate(plan.steps):
                if step.step_type.value in ["fill_field", "fill_form", "submit"]:
                    self._log("step", f"Executing step: {step.step_type.value}")
                    try:
                        await self.step_executor.execute(step, parsed)
                        self._log("success", f"  ✅ {step.description}")
                    except Exception as e:
                        self._log("error", f"  ❌ {step.description}: {e}")
            
            # Verify again
            await asyncio.sleep(2)  # Wait for form submission
            
            for step in plan.steps:
                if step.step_type.value == "verify":
                    verify_result = await self.step_executor.execute(step, parsed)
                    if verify_result.get("verified"):
                        result.success = True
                        self._log("success", "✅ Form submitted successfully after CAPTCHA!")
                    else:
                        result.success = False
                        result.error = f"Verification failed after CAPTCHA: {verify_result.get('reason')}"
                    break
            
            result.final_url = self.page.url
            
        except Exception as e:
            logger.exception(f"CAPTCHA handling failed: {e}")
            result.error = f"CAPTCHA handling failed: {e}"
        
        finally:
            await self._cleanup()
        
        return result
    
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

                # If this was an explicit SCREENSHOT step, capture path in StepResult
                if step.step_type == StepType.SCREENSHOT and isinstance(data, dict):
                    path = data.get("path") or data.get("screenshot")
                    if path:
                        step_result.screenshot_path = path
                
                # Capture screenshot if configured
                if self.config.screenshot_each_step and self.screenshot_manager:
                    try:
                        ss = await self.screenshot_manager.capture(
                            self.page, i, step.step_type.value,
                            description=step.description
                        )
                        if ss:
                            step_result.screenshot_path = ss.path
                    except Exception:
                        pass
                
                self._log("success", f"  ✅ {step.description}")
                
            except Exception as e:
                step_result.error = str(e)
                step.status = StepStatus.FAILED
                step.error = str(e)
                
                self._log("error", f"  ❌ {step.description}: {e}")
                
                # Capture error screenshot
                if self.config.screenshot_on_error and self.screenshot_manager:
                    try:
                        ss = await self.screenshot_manager.capture_error(self.page, i, str(e))
                        if ss:
                            step_result.screenshot_path = ss.path
                    except Exception:
                        pass
                
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
        """
        Execute a single step.
        
        Delegates to StepExecutor for most steps, but handles
        screenshot specially to use the orchestrator's screenshot path.
        """
        step_type = step.step_type
        params = step.params
        
        # Handle screenshot specially (needs orchestrator's path)
        if step_type == StepType.SCREENSHOT:
            name = params.get("name", "screenshot")
            path = await self._take_screenshot(name)
            return {"path": path}
        
        # Delegate to StepExecutor for all other steps
        return await self.step_executor.execute(step, parsed)
    
    async def _take_screenshot(self, name: str) -> str:
        """Take screenshot and return path"""
        os.makedirs(self.config.log_dir, exist_ok=True)
        path = os.path.join(self.config.log_dir, f"{self.run_id}-{name}.png")
        await self.page.screenshot(path=path)
        
        # Add to screenshot manager for log tracking
        if self.screenshot_manager:
            from curllm_logs import ScreenshotInfo
            ss_info = ScreenshotInfo(
                path=path,
                name=name,
                description=f"Screenshot: {name}",
            )
            self.screenshot_manager.screenshots.append(ss_info)
        
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
        """Save run log using the curllm_logs package"""
        os.makedirs(self.config.log_dir, exist_ok=True)
        log_path = os.path.join(self.config.log_dir, f"run-{self.run_id}.md")
        
        if HAS_LOG_PACKAGE:
            return self._save_log_with_package(result, log_path)
        else:
            return self._save_log_legacy(result, log_path)
    
    def _save_log_with_package(self, result: OrchestratorResult, log_path: str) -> str:
        """Save using curllm_logs package"""
        try:
            from curllm_logs import LogSession, create_session
            
            # Create session
            session = create_session(session_type="orchestrator", log_dir=self.config.log_dir)
            session.session_id = self.run_id
            
            # Command info
            escaped_cmd = result.command.replace('"', '\\"')
            url = result.parsed.get_url() if result.parsed else None
            
            session.command = CommandInfo(
                raw_command=result.command,
                cli_format=f'curllm "{escaped_cmd}"',
                traditional_format=f'curllm "{url}" -d "{escaped_cmd}"' if url else None,
                target_url=url,
                target_domain=result.parsed.target_domain if result.parsed else None,
                instruction=result.command,
                goal=result.parsed.primary_goal.value if result.parsed else None,
                email=result.parsed.form_data.email if result.parsed else None,
                name=result.parsed.form_data.name if result.parsed else None,
                phone=result.parsed.form_data.phone if result.parsed else None,
                message=result.parsed.form_data.message if result.parsed else None,
                parse_confidence=result.parsed.confidence if result.parsed else 0,
            )
            
            # Environment info
            session.environment = EnvironmentInfo(
                headless=self.config.headless,
                stealth_mode=self.config.stealth_mode,
            )
            
            # Plan steps
            if result.plan:
                session.plan_steps = [f"{s.step_type.value}: {s.description}" for s in result.plan.steps]
            
            # Step results
            for sr in result.step_results:
                # Extract metadata from step data (LLM-DSL returns method, selector, etc.)
                selector_used = sr.data.get("selector") if sr.data else None
                selector_confidence = sr.data.get("confidence", 0.0) if sr.data else 0.0
                method_used = sr.data.get("method", "unknown") if sr.data else "unknown"
                
                step_log = StepLog(
                    index=sr.step_index,
                    step_type=sr.step_type,
                    description=sr.step_type,
                    status="completed" if sr.success else "failed",
                    duration_ms=sr.duration_ms,
                    selector_used=selector_used,
                    selector_confidence=selector_confidence,
                    method=method_used,
                    result_data=sr.data,
                    error_message=sr.error,
                    screenshot_after=sr.screenshot_path,
                )
                session.add_step(step_log)
            
            # Add screenshots from manager
            if self.screenshot_manager:
                for ss in self.screenshot_manager.screenshots:
                    session.screenshots.append(ss)
            
            # Add visited URLs
            if result.final_url:
                session.add_url(result.final_url)
            
            # Raw log entries
            from curllm_logs.log_entry import LogEntry as LogEntryClass
            for log_line in self.run_log:
                session.entries.append(LogEntryClass(
                    timestamp=datetime.now(),
                    level=LogLevel.INFO,
                    message=log_line
                ))
            
            # Result
            session.result = ResultInfo(
                success=result.success,
                final_url=result.final_url,
                duration_ms=result.duration_ms,
                steps_total=len(result.step_results),
                steps_completed=sum(1 for sr in result.step_results if sr.success),
                steps_failed=sum(1 for sr in result.step_results if not sr.success),
                extracted_data=result.extracted_data,
                error_message=result.error,
            )
            
            session.finish(result.success, result.error)
            
            # Write using MarkdownLogWriter
            writer = MarkdownLogWriter(include_raw_log=True, include_images=True)
            writer.write(session, log_path)
            
            logger.info(f"Log saved: {log_path}")
            return log_path
            
        except Exception as e:
            logger.error(f"Failed to save log with package: {e}")
            # Fall back to legacy
            return self._save_log_legacy(result, log_path)
    
    def _save_log_legacy(self, result: OrchestratorResult, log_path: str) -> str:
        """Legacy log saving (fallback when package not available)"""
        with open(log_path, "w") as f:
            f.write(f"# curllm Run Log ({self.run_id})\n\n")
            f.write(f"**Type:** orchestrator\n")
            f.write(f"**Status:** {'✅ SUCCESS' if result.success else '❌ FAILED'}\n")
            f.write(f"**Duration:** {result.duration_ms}ms\n\n")
            f.write("---\n\n")
            
            # CLI command
            escaped_cmd = result.command.replace('"', '\\"')
            f.write("## Command\n\n")
            f.write("### CLI Command\n")
            f.write(f"```bash\ncurllm \"{escaped_cmd}\"\n```\n\n")
            
            # Traditional format
            if result.parsed and result.parsed.target_domain:
                url = result.parsed.get_url()
                f.write("### Traditional Format\n")
                f.write(f"```bash\ncurllm \"{url}\" -d \"{escaped_cmd}\"\n```\n\n")
                f.write(f"- **URL:** {url}\n")
                f.write(f"- **Instruction:** {result.command}\n\n")
            
            # Parsed info
            if result.parsed:
                f.write("## Parsed\n\n")
                f.write(f"- **Domain:** {result.parsed.target_domain}\n")
                f.write(f"- **Goal:** {result.parsed.primary_goal.value}\n")
                f.write(f"- **Confidence:** {result.parsed.confidence:.0%}\n")
                if result.parsed.form_data.email:
                    f.write(f"\n### Form Data\n")
                    f.write(f"- **Email:** {result.parsed.form_data.email}\n")
                if result.parsed.form_data.name:
                    f.write(f"- **Name:** {result.parsed.form_data.name}\n")
                f.write("\n")
            
            # Plan
            if result.plan:
                f.write("## Plan\n\n")
                for i, step in enumerate(result.plan.steps):
                    status = "✅" if step.status == StepStatus.COMPLETED else "❌" if step.status == StepStatus.FAILED else "⏳"
                    f.write(f"{i+1}. {status} {step.step_type.value}: {step.description}\n")
                f.write("\n")
            
            # Step execution table
            if result.step_results:
                f.write("## Step Execution\n\n")
                f.write("| # | Step | Duration | Method | Confidence | Status |\n")
                f.write("|---|------|----------|--------|------------|--------|\n")
                for sr in result.step_results:
                    status = "✅" if sr.success else "❌"
                    f.write(f"| {sr.step_index + 1} | {sr.step_type} | {sr.duration_ms}ms | - | - | {status} |\n")
                f.write("\n")
            
            # Final URL
            if result.final_url:
                f.write("## Navigation\n\n")
                f.write(f"**Final URL:** `{result.final_url}`\n\n")
            
            # Result
            f.write("## Result\n\n")
            f.write(f"**Status:** {'✅ SUCCESS' if result.success else '❌ FAILED'}\n")
            f.write(f"**Duration:** {result.duration_ms}ms\n")
            completed = sum(1 for sr in result.step_results if sr.success)
            f.write(f"**Steps:** {completed}/{len(result.step_results)} completed\n\n")
            
            if result.error:
                f.write("### Error\n")
                f.write(f"```\n{result.error}\n```\n\n")
            
            if result.extracted_data:
                f.write("### Extracted Data\n")
                f.write(f"```json\n{json.dumps(result.extracted_data, indent=2, ensure_ascii=False)}\n```\n\n")
            
            # Raw execution log
            f.write("## Execution Log\n\n")
            f.write("```\n")
            f.write("\n".join(self.run_log))
            f.write("\n```\n")
        
        logger.info(f"Log saved: {log_path}")
        return log_path
