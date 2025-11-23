#!/usr/bin/env python3
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse



# optional browser_use agent
try:
    from browser_use import Agent as BrowserUseAgent  # type: ignore
except Exception:
    BrowserUseAgent = None

class LocalAgent:
    def __init__(self, browser, llm, max_steps, visual_mode, task=None):
        self.browser = browser
        self.llm = llm
        self.max_steps = max_steps
        self.visual_mode = visual_mode

from .config import config
from .logger import RunLogger
from .llm import SimpleOllama
from .vision import VisionAnalyzer
from .captcha import CaptchaSolver
from .stealth import StealthConfig
from .runtime import parse_runtime_from_instruction
from .headers import normalize_headers
from .browser_setup import setup_browser
from .page_context import extract_page_context
from .actions import execute_action
from .human_verify import handle_human_verification, looks_like_human_verify_text
from .captcha_widget import handle_captcha_image as _handle_captcha_image_widget, handle_widget_captcha as _handle_widget_captcha
from .page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies, is_block_page as _is_block_page
from .extraction import generic_fastpath, direct_fastpath, product_heuristics, fallback_extract

logger = logging.getLogger(__name__)

class CurllmExecutor:
    """Main browser automation executor with LLM support"""
    def __init__(self):
        self.llm = self._setup_llm()
        self.vision_analyzer = VisionAnalyzer()
        self.captcha_solver = CaptchaSolver()
        self.stealth_config = StealthConfig()

    def _setup_llm(self) -> Any:
        backend = os.getenv("CURLLM_LLM_BACKEND", "simple").lower()
        if backend == "langchain":
            try:
                from langchain_ollama import OllamaLLM  # type: ignore
                return OllamaLLM(
                    base_url=config.ollama_host,
                    model=config.ollama_model,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    num_ctx=config.num_ctx,
                    num_predict=config.num_predict,
                )
            except Exception as e:
                logger.warning(f"langchain_ollama requested but unavailable, falling back to SimpleOllama: {e}")
        return SimpleOllama(
            base_url=config.ollama_host,
            model=config.ollama_model,
            num_ctx=config.num_ctx,
            num_predict=config.num_predict,
            temperature=config.temperature,
            top_p=config.top_p,
        )

    async def execute_workflow(
        self,
        instruction: str,
        url: Optional[str] = None,
        visual_mode: bool = False,
        stealth_mode: bool = False,
        captcha_solver: bool = False,
        use_bql: bool = False,
        headers: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        # Parse optional runtime params embedded in JSON instruction
        instruction, runtime = parse_runtime_from_instruction(instruction)
        run_logger = RunLogger(instruction=instruction, url=url)
        run_logger.log_heading(f"curllm run: {datetime.now().isoformat()}")
        run_logger.log_kv("Model", config.ollama_model)
        run_logger.log_kv("Ollama Host", config.ollama_host)
        run_logger.log_kv("Visual Mode", str(visual_mode))
        run_logger.log_kv("Stealth Mode", str(stealth_mode))
        run_logger.log_kv("Use BQL", str(use_bql))
        # Auto-enable DOM snapshot if task looks like extraction and user didn't force it
        try:
            low = (instruction or "").lower()
            looks_extractive = any(k in low for k in ["extract", "title", "product", "produkt", "price", "lista", "list"])  # noqa: E501
            if looks_extractive and not bool(runtime.get("include_dom_html")):
                runtime["include_dom_html"] = True
                run_logger.log_kv("Auto include_dom_html", "True")
        except Exception:
            pass

        browser_context = None
        try:
            if use_bql:
                instruction = self._parse_bql(instruction)
                run_logger.log_text("BQL parsed instruction:")
                run_logger.log_code("text", instruction)

            host = urlparse(url).hostname if url else None
            if host and any(h in host for h in ["allegro.pl", "allegro.com"]):
                stealth_mode = True
            # Normalize headers for Playwright context
            norm_headers = normalize_headers(headers)
            browser_context = await self._setup_browser(stealth_mode, storage_key=host, headers=norm_headers)
            run_logger.log_text("Browser context initialized.")

            agent = self._create_agent(
                browser_context=browser_context,
                instruction=instruction,
                visual_mode=visual_mode,
            )

            result = await self._execute_task(
                agent=agent,
                instruction=instruction,
                url=url,
                visual_mode=visual_mode,
                stealth_mode=stealth_mode,
                captcha_solver=captcha_solver,
                run_logger=run_logger,
                runtime=runtime,
            )

            if browser_context is not None:
                try:
                    try:
                        storage_path = getattr(browser_context, "_curllm_storage_path", None)
                        if storage_path:
                            await browser_context.storage_state(path=storage_path)
                    except Exception:
                        logger.warning("Unable to persist storage state", exc_info=True)
                    await browser_context.close()
                except Exception as e:
                    logger.warning(f"Error during browser close: {e}")
                try:
                    br = getattr(browser_context, "_curllm_browser", None)
                    if br is not None:
                        await br.close()
                    pw = getattr(browser_context, "_curllm_playwright", None)
                    if pw is not None:
                        await pw.stop()
                except Exception as e:
                    logger.warning(f"Error closing Playwright resources: {e}")

            res = {
                "success": True,
                "result": result.get("data"),
                "steps_taken": result.get("steps", 0),
                "screenshots": result.get("screenshots", []),
                "timestamp": datetime.now().isoformat(),
                "run_log": str(run_logger.path),
            }
            run_logger.log_text("Run finished successfully.")
            return res

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}", exc_info=True)
            run_logger.log_text("Error occurred:")
            run_logger.log_code("text", str(e))
            if browser_context is not None:
                try:
                    try:
                        storage_path = getattr(browser_context, "_curllm_storage_path", None)
                        if storage_path:
                            await browser_context.storage_state(path=storage_path)
                    except Exception:
                        pass
                    await browser_context.close()
                except Exception as ce:
                    logger.warning(f"Error during browser close after failure: {ce}")
                try:
                    br = getattr(browser_context, "_curllm_browser", None)
                    if br is not None:
                        await br.close()
                    pw = getattr(browser_context, "_curllm_playwright", None)
                    if pw is not None:
                        await pw.stop()
                except Exception as e2:
                    logger.warning(f"Error closing Playwright resources after failure: {e2}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "run_log": str(run_logger.path),
            }

    def _create_agent(self, browser_context, instruction: str, visual_mode: bool):
        if BrowserUseAgent is not None:
            try:
                import inspect
                params = inspect.signature(BrowserUseAgent.__init__).parameters
                kwargs = {
                    "browser": browser_context,
                    "llm": self.llm,
                    "max_steps": config.max_steps,
                    "visual_mode": visual_mode,
                }
                if "task" in params:
                    kwargs["task"] = instruction
                return BrowserUseAgent(**kwargs)
            except Exception as e:
                logger.warning(f"browser_use.Agent init failed: {e}. Falling back to LocalAgent.")
        return LocalAgent(browser_context, self.llm, config.max_steps, visual_mode, task=instruction)

    async def _setup_browser(self, stealth_mode: bool, storage_key: Optional[str] = None, headers: Optional[Dict[str, str]] = None):
        return await setup_browser(
            use_browserless=config.use_browserless,
            browserless_url=config.browserless_url,
            stealth_mode=stealth_mode,
            storage_key=storage_key,
            headers=headers,
            stealth_config=self.stealth_config,
            config=config,
        )

    # browserless setup handled in browser_setup.setup_browser

    async def _execute_task(
        self,
        agent,
        instruction: str,
        url: Optional[str],
        visual_mode: bool,
        stealth_mode: bool,
        captcha_solver: bool,
        run_logger: RunLogger,
        runtime: Dict[str, Any],
    ) -> Dict:
        result: Dict[str, Any] = {"data": None, "steps": 0, "screenshots": []}
        lower_instr = (instruction or "").lower()
        if url:
            page = await agent.browser.new_page()
            await page.goto(url)
            try:
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_load_state("networkidle")
            except Exception:
                pass
            try:
                hv = await handle_human_verification(page, run_logger)
                run_logger.log_kv("human_verify_clicked_on_nav", str(bool(hv)))
            except Exception as e:
                run_logger.log_kv("human_verify_on_nav_error", str(e))
            # Optional initial scroll to load content
            if runtime.get("scroll_load"):
                try:
                    await _auto_scroll(page, steps=4, delay_ms=600)
                except Exception:
                    pass
            # Attempt widget CAPTCHA solving right after navigation if enabled
            if captcha_solver:
                try:
                    solved = await _handle_widget_captcha(page, current_url=url, solver=self.captcha_solver, run_logger=run_logger)
                    run_logger.log_kv("widget_captcha_on_nav", str(bool(solved)))
                except Exception as e:
                    run_logger.log_kv("widget_captcha_on_nav_error", str(e))
        else:
            page = await agent.browser.new_page()
        try:
            if await _is_block_page(page) and not stealth_mode:
                if run_logger:
                    run_logger.log_text("Block page detected; retrying with stealth mode...")
                try:
                    await page.close()
                except Exception:
                    pass
                host = None
                try:
                    host = await page.evaluate("() => window.location.hostname")
                except Exception:
                    try:
                        if url:
                            host = urlparse(url).hostname
                    except Exception:
                        pass
                new_ctx = await self._setup_browser(True, host, headers=None)
                agent.browser = new_ctx
                page = await agent.browser.new_page()
                await page.goto(url)
                try:
                    await page.wait_for_load_state("domcontentloaded")
                    await page.wait_for_load_state("networkidle")
                except Exception:
                    pass
                stealth_mode = True
        except Exception:
            pass
        domain_dir = config.screenshot_dir
        try:
            host = await page.evaluate("() => window.location.hostname")
            if host:
                domain_dir = config.screenshot_dir / host
                domain_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            try:
                if url:
                    host = urlparse(url).hostname
                    if host:
                        domain_dir = config.screenshot_dir / host
                        domain_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        try:
            if ("screenshot" in lower_instr) or ("zrzut" in lower_instr):
                shot_path = await self._take_screenshot(page, 0, target_dir=domain_dir)
                result["screenshots"].append(shot_path)
                if run_logger:
                    run_logger.log_text(f"Initial screenshot saved: {shot_path}")
                result["data"] = {"screenshot_saved": shot_path}
                if not ("extract" in lower_instr or "product" in lower_instr or "produkt" in lower_instr):
                    await page.close()
                    return result
        except Exception:
            pass
        try:
            await _accept_cookies(page)
            run_logger.log_kv("accept_cookies", "attempted")
        except Exception as e:
            run_logger.log_kv("accept_cookies_error", str(e))
        if bool(runtime.get("fastpath")):
            try:
                res_generic = await generic_fastpath(instruction, page, run_logger)
                if res_generic is not None:
                    result["data"] = res_generic
                    await page.close()
                    return result
            except Exception as e:
                run_logger.log_kv("generic_fastpath_error", str(e))
        else:
            run_logger.log_text("Fastpath disabled; using DOM-aware LLM planner.")
        if bool(runtime.get("fastpath")):
            try:
                res_direct = await direct_fastpath(instruction, page, run_logger)
                if res_direct is not None:
                    result["data"] = res_direct
                    await page.close()
                    return result
            except Exception as e:
                run_logger.log_kv("direct_fastpath_error", str(e))
        last_sig = None
        no_progress = 0
        stall_limit = 3
        for step in range(config.max_steps):
            result["steps"] = step + 1
            if run_logger:
                run_logger.log_heading(f"Step {step + 1}")
            if visual_mode:
                screenshot_path = await self._take_screenshot(page, step, target_dir=domain_dir)
                result["screenshots"].append(screenshot_path)
                visual_analysis = await self.vision_analyzer.analyze(screenshot_path)
                if captcha_solver and visual_analysis.get("has_captcha"):
                    await _handle_captcha_image_widget(page, screenshot_path, self.captcha_solver, run_logger)
            # Try handle human verification banners/buttons each step
            try:
                await handle_human_verification(page, run_logger)
            except Exception:
                pass
            # Try widget CAPTCHA solving per step if enabled
            if captcha_solver:
                try:
                    # Try to obtain current URL from page if available
                    cur_url = None
                    try:
                        cur_url = await page.evaluate("() => window.location.href")
                    except Exception:
                        cur_url = url
                    await _handle_widget_captcha(page, current_url=cur_url, solver=self.captcha_solver, run_logger=run_logger)
                except Exception:
                    pass
            page_context = await self._extract_page_context(
                page,
                include_dom=bool(runtime.get("include_dom_html")),
                dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
            )
            # Decision logging and remediation when DOM looks empty
            try:
                inter_len = len(page_context.get("interactive", []) or [])
                dom_len = len(page_context.get("dom_preview", "") or "")
                ifr_len = len(page_context.get("iframes", []) or [])
                run_logger.log_kv("interactive_count", str(inter_len))
                run_logger.log_kv("dom_preview_len", str(dom_len))
                run_logger.log_kv("iframes_count", str(ifr_len))
                if (inter_len == 0 and dom_len == 0 and bool(runtime.get("include_dom_html"))):
                    run_logger.log_text("DOM snapshot empty; running remediation: human_verify -> accept_cookies -> small scroll -> re-extract")
                    try:
                        hv2 = await handle_human_verification(page, run_logger)
                        run_logger.log_kv("human_verify_remediation", str(bool(hv2)))
                    except Exception as e:
                        run_logger.log_kv("human_verify_remediation_error", str(e))
                    try:
                        await _accept_cookies(page)
                    except Exception:
                        pass
                    try:
                        await _auto_scroll(page, steps=1, delay_ms=300)
                    except Exception:
                        pass
                    page_context = await self._extract_page_context(
                        page,
                        include_dom=True,
                        dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
                    )
                    inter_len2 = len(page_context.get("interactive", []) or [])
                    dom_len2 = len(page_context.get("dom_preview", "") or "")
                    ifr_len2 = len(page_context.get("iframes", []) or [])
                    run_logger.log_kv("interactive_count_after_remediate", str(inter_len2))
                    run_logger.log_kv("dom_preview_len_after_remediate", str(dom_len2))
                    run_logger.log_kv("iframes_count_after_remediate", str(ifr_len2))
            except Exception:
                pass
            try:
                sig = f"{page_context.get('url','')}|{page_context.get('title','')}|{(page_context.get('text','') or '')[:500]}"
                if last_sig is None:
                    last_sig = sig
                    no_progress = 0
                elif sig == last_sig:
                    no_progress += 1
                else:
                    last_sig = sig
                    no_progress = 0
                if no_progress >= stall_limit:
                    if run_logger:
                        run_logger.log_text(f"No progress detected for {stall_limit} consecutive steps. Stopping early.")
                    break
            except Exception:
                pass
            if run_logger:
                try:
                    run_logger.log_text("Page context snapshot (truncated):")
                    run_logger.log_code("json", json.dumps(page_context, indent=2)[:1500])
                except Exception:
                    pass
            try:
                res_products = await product_heuristics(instruction, page, run_logger)
                if res_products is not None:
                    result["data"] = res_products
                    break
            except Exception:
                pass
            action = await self._generate_action(
                instruction=instruction,
                page_context=page_context,
                step=step,
                run_logger=run_logger,
            )
            if run_logger:
                run_logger.log_text("Planned action:")
                run_logger.log_code("json", json.dumps(action))
            if action.get("type") == "complete":
                result["data"] = action.get("extracted_data", page_context)
                break
            # Respect no_click runtime flag
            if runtime.get("no_click") and str(action.get("type")) == "click":
                if run_logger:
                    run_logger.log_text("Skipping click due to no_click=true")
            else:
                await self._execute_action(page, action, runtime)
            if run_logger:
                run_logger.log_text(f"Executed action: {action.get('type')}")
            if await self._detect_honeypot(page):
                logger.warning("Honeypot detected, skipping field")
        if result.get("data") is None:
            try:
                lower_instr = (instruction or "").lower()
                result["data"] = await fallback_extract(instruction, page, run_logger)
                # ... (rest of the code remains the same)
                data = result.get("data")
                if isinstance(data, dict):
                    filtered = {}
                    if ("email" in lower_instr or "mail" in lower_instr) and "emails" in data:
                        filtered["emails"] = data["emails"]
                    if ("phone" in lower_instr or "tel" in lower_instr or "telefon" in lower_instr) and "phones" in data:
                        filtered["phones"] = data["phones"]
                    result["data"] = filtered
            except Exception:
                pass
        await page.close()
        return result

    async def _take_screenshot(self, page, step: int, target_dir: Optional[Path] = None) -> str:
        tdir = Path(target_dir) if target_dir else config.screenshot_dir
        tdir.mkdir(parents=True, exist_ok=True)
        filename = tdir / f"step_{step}_{datetime.now().timestamp()}.png"
        await page.screenshot(path=str(filename))
        return str(filename)

    async def _extract_page_context(self, page, include_dom: bool = False, dom_max_chars: int = 20000) -> Dict:
        return await extract_page_context(page, include_dom=include_dom, dom_max_chars=dom_max_chars)

    async def _generate_action(self, instruction: str, page_context: Dict, step: int, run_logger: RunLogger | None = None) -> Dict:
        from .llm_planner import generate_action
        return await generate_action(self.llm, instruction, page_context, step, run_logger)

    async def _execute_action(self, page, action: Dict, runtime: Dict[str, Any]):
        return await execute_action(page, action, runtime)

    # Backward-compat wrappers for tests
    def _looks_like_human_verify_text(self, txt: str) -> bool:  # noqa: N802
        return looks_like_human_verify_text(txt)

    async def _handle_human_verification(self, page, run_logger: RunLogger | None = None):  # noqa: N802
        return await handle_human_verification(page, run_logger)

    async def _detect_honeypot(self, page) -> bool:
        honeypots = await page.evaluate(
            """
            () => {
                const suspicious = [];
                const inputs = document.querySelectorAll('input, textarea');
                inputs.forEach(input => {
                    const style = window.getComputedStyle(input);
                    if (style.display === 'none' || 
                        style.visibility === 'hidden' ||
                        input.type === 'hidden' ||
                        style.opacity === '0' ||
                        input.offsetHeight === 0) {
                        suspicious.push(input.name || input.id);
                    }
                });
                return suspicious.length > 0;
            }
            """
        )
        return bool(honeypots)

    def _parse_bql(self, query: str) -> str:
        if "query" in query and "{" in query:
            return f"Extract the following fields from the page: {query}"
        return query
