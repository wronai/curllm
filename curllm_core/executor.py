#!/usr/bin/env python3
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


from .config import config
from .logger import RunLogger
from .llm_factory import setup_llm as setup_llm_factory
from .agent_factory import create_agent as create_agent_factory
from .vision import VisionAnalyzer
from .captcha import CaptchaSolver
from .stealth import StealthConfig
from .runtime import parse_runtime_from_instruction
from .headers import normalize_headers
from .browser_setup import setup_browser
from .wordpress import WordPressAutomation
from .proxy import resolve_proxy
from .page_context import extract_page_context
from .actions import execute_action
from .human_verify import handle_human_verification, looks_like_human_verify_text
from .captcha_widget import handle_captcha_image as _handle_captcha_image_widget, handle_widget_captcha as _handle_widget_captcha
from .page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies, is_block_page as _is_block_page
from .extraction import generic_fastpath, direct_fastpath, product_heuristics, fallback_extract, extract_articles_eval, validate_with_llm, extract_links_by_selectors
from .captcha_slider import attempt_slider_challenge
from .slider_plugin import try_external_slider_solver
from .bql import BQLExecutor
from .validation_utils import should_validate
from .screenshots import take_screenshot as _take_screenshot_func
from .form_fill import deterministic_form_fill as _deterministic_form_fill_func, parse_form_pairs as _parse_form_pairs_func
from .planner_progress import progress_tick as _progress_tick_func
from .product_extract import multi_stage_product_extract as _multi_stage_product_extract_func
from .bql_utils import parse_bql as _parse_bql_util
from .dom_utils import detect_honeypot as _detect_honeypot_func
from .diagnostics import diagnose_url_issue as _diagnose_url_issue_func
from .navigation import open_page_with_prechecks as _open_page_with_prechecks_func
from .rerun_cmd import build_rerun_curl as _build_rerun_curl_func
from .task_runner import run_task as _run_task

logger = logging.getLogger(__name__)

def _should_validate(instruction: Optional[str], data: Optional[Any]) -> bool:
    return should_validate(instruction, data)

class CurllmExecutor:
    """Main browser automation executor with LLM support"""
    def __init__(self):
        self.llm = self._setup_llm()
        self.vision_analyzer = VisionAnalyzer()
        self.captcha_solver = CaptchaSolver()
        self.stealth_config = StealthConfig()

    def _setup_llm(self) -> Any:
        return setup_llm_factory()

    async def execute_workflow(
        self,
        instruction: str,
        url: Optional[str] = None,
        visual_mode: bool = False,
        stealth_mode: bool = False,
        captcha_solver: bool = False,
        use_bql: bool = False,
        headers: Optional[Dict] = None,
        proxy: Optional[Dict] = None,
        session_id: Optional[str] = None,
        wordpress_config: Optional[Dict] = None,
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
        # Log runtime flags
        try:
            for k in [
                "include_dom_html","dom_max_chars","smart_click","action_timeout_ms",
                "wait_after_click_ms","no_click","scroll_load","fastpath"]:
                if k in runtime:
                    run_logger.log_kv(f"runtime.{k}", str(runtime.get(k)))
        except Exception:
            pass
        # Auto-enable DOM snapshot if task looks like extraction and user didn't force it
        try:
            low = (instruction or "").lower()
            looks_extractive = any(k in low for k in ["extract", "title", "product", "produkt", "price", "lista", "list"])  # noqa: E501
            if looks_extractive and not bool(runtime.get("include_dom_html")):
                runtime["include_dom_html"] = True
                run_logger.log_kv("Auto include_dom_html", "True")
            # Remove simplified fastpaths for content-extraction tasks
            if any(k in low for k in ["product", "produkt", "price", "zł", "pln", "title", "titles", "article", "articles", "news", "headline", "wpis", "artyku"]):
                if runtime.get("fastpath"):
                    run_logger.log_kv("runtime.fastpath_forced", "False")
                runtime["fastpath"] = False
            # Also disable fastpaths for form-filling tasks
            if any(k in low for k in [
                "form", "formularz", "fill", "wypełnij", "wypelnij", "submit",
                "contact", "kontakt", "send", "sent", "message", "wiadomość", "wiadomosc", "wyślij", "wyslij"
            ]):
                if runtime.get("fastpath"):
                    run_logger.log_kv("runtime.fastpath_forced_form", "False")
                runtime["fastpath"] = False
        except Exception:
            pass

        browser_context = None
        try:
            bql_query_raw: Optional[str] = None
            if use_bql:
                bql_query_raw = instruction
                instruction = self._parse_bql(instruction)
                run_logger.log_text("BQL parsed instruction:")
                run_logger.log_code("text", instruction)

            host = urlparse(url).hostname if url else None
            if host and any(h in host for h in ["allegro.pl", "allegro.com", "ceneo.pl", "ceneo.com"]):
                stealth_mode = True
            # Normalize headers for Playwright context
            norm_headers = normalize_headers(headers)
            # Resolve proxy rotation (per-host key) if provided
            resolved_proxy = resolve_proxy(proxy, rotation_key=host) if proxy else None
            browser_context = await self._setup_browser(
                stealth_mode,
                storage_key=host,
                headers=norm_headers,
                proxy_config=resolved_proxy,
                session_id=session_id,
            )
            run_logger.log_text("Browser context initialized.")

            # If BQL mode, execute BQL directly and short-circuit
            if use_bql and bql_query_raw:
                try:
                    bql_exec = BQLExecutor(browser_context)
                    bql_result = await bql_exec.execute(bql_query_raw)
                    if run_logger:
                        run_logger.log_text("BQL execution finished.")
                        try:
                            run_logger.log_code("json", json.dumps(bql_result, indent=2))
                        except Exception:
                            pass
                    # Normalize to a convenient top-level shape when possible
                    result_data: Any = None
                    try:
                        data = bql_result.get("data") if isinstance(bql_result, dict) else None
                        if isinstance(data, dict) and "page" in data:
                            page_obj = data.get("page") or {}
                            items = page_obj.get("items") or []
                            if isinstance(items, list):
                                articles = []
                                for it in items:
                                    if isinstance(it, dict):
                                        title = it.get("title") or it.get("text")
                                        url2 = it.get("url") or it.get("href")
                                        articles.append({"title": title or "", "url": url2 or ""})
                                result_data = {"articles": articles}
                    except Exception:
                        pass
                    if result_data is None:
                        result_data = bql_result.get("data", bql_result)

                    # Validation pass (LLM) if enabled
                    try:
                        if config.validation_enabled and result_data is not None and _should_validate(instruction, result_data):
                            v = await validate_with_llm(self.llm, instruction, result_data, run_logger)
                            if v is not None:
                                result_data = v
                    except Exception:
                        pass

                    # Close browser resources before returning
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
                        "result": result_data,
                        "steps_taken": 1,
                        "screenshots": [],
                        "timestamp": datetime.now().isoformat(),
                        "run_log": str(run_logger.path),
                    }
                    run_logger.log_text("Run finished successfully.")
                    return res
                except Exception as e:
                    run_logger.log_text("BQL execution error:")
                    run_logger.log_code("text", str(e))

            # Optional WordPress automation short-circuit
            if wordpress_config:
                try:
                    page = await browser_context.new_page()
                    wp = WordPressAutomation(page, run_logger)
                    logged = await wp.login(
                        wordpress_config.get("url", url or ""),
                        wordpress_config.get("username", ""),
                        wordpress_config.get("password", ""),
                    )
                    if logged:
                        if wordpress_config.get("action") == "create_post":
                            post_url = await wp.create_post(
                                title=wordpress_config.get("title", "New Post"),
                                content=wordpress_config.get("content", ""),
                                status=wordpress_config.get("status", "draft"),
                                categories=wordpress_config.get("categories"),
                                tags=wordpress_config.get("tags"),
                                featured_image_path=wordpress_config.get("featured_image_path"),
                            )
                            out_res = {
                                "success": True,
                                "result": {"post_url": post_url, "success": bool(post_url)},
                                "steps_taken": 0,
                                "screenshots": [],
                                "timestamp": datetime.now().isoformat(),
                                "run_log": str(run_logger.path),
                            }
                            # Persist session if configured
                            try:
                                storage_path = getattr(browser_context, "_curllm_storage_path", None)
                                if storage_path:
                                    await browser_context.storage_state(path=storage_path)
                                session_mgr = getattr(browser_context, "_curllm_session_manager", None)
                                if session_mgr and session_id:
                                    session_mgr.save_session_metadata(session_id, {
                                        "type": "wordpress",
                                        "url": wordpress_config.get("url", url or ""),
                                        "username": wordpress_config.get("username", "")
                                    })
                            except Exception:
                                pass
                            try:
                                await page.close()
                            except Exception:
                                pass
                            run_logger.log_text("WordPress automation finished.")
                            return out_res
                except Exception as e:
                    run_logger.log_text(f"WordPress automation error: {e}")

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

            # Validation pass (LLM) before finalizing
            try:
                final_data = result.get("data")
                if config.validation_enabled and final_data is not None and _should_validate(instruction, final_data):
                    v = await validate_with_llm(self.llm, instruction, final_data, run_logger)
                    if v is not None:
                        result["data"] = v
            except Exception:
                pass

            res = {
                "success": True,
                "result": result.get("data"),
                "steps_taken": result.get("steps", 0),
                "screenshots": result.get("screenshots", []),
                "timestamp": datetime.now().isoformat(),
                "run_log": str(run_logger.path),
                "hints": (result.get("meta", {}) or {}).get("hints", []),
                "suggested_commands": (result.get("meta", {}) or {}).get("suggested_commands", []),
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
            # Provide interactive hints and ready commands on failure
            try:
                params = {
                    "include_dom_html": True,
                    "scroll_load": True,
                    "dom_max_chars": 60000,
                    "stall_limit": int(os.getenv("CURLLM_STALL_LIMIT", "7")),
                    "planner_growth_per_step": int(os.getenv("CURLLM_PLANNER_GROWTH", "3000")),
                    "planner_max_cap": int(os.getenv("CURLLM_PLANNER_MAX", "30000")),
                    "preset": "deep_scan",
                }
                cmd = self._build_rerun_curl(instruction, url or "", params)
                run_logger.log_text("Suggested retry command:")
                run_logger.log_code("bash", cmd)
                hints = [
                    "Enable DOM snapshot and deeper analysis, increase stall limit, and retry.",
                    "If blocked, set stealth_mode=true or use a proxy.",
                ]
                suggested = [cmd]
            except Exception:
                hints, suggested = [], []
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "run_log": str(run_logger.path),
                "hints": hints,
                "suggested_commands": suggested,
            }

    def _create_agent(self, browser_context, instruction: str, visual_mode: bool):
        return create_agent_factory(browser_context, self.llm, instruction, config.max_steps, visual_mode)

    async def _setup_browser(self, stealth_mode: bool, storage_key: Optional[str] = None, headers: Optional[Dict[str, str]] = None, proxy_config: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None):
        return await setup_browser(
            use_browserless=config.use_browserless,
            browserless_url=config.browserless_url,
            stealth_mode=stealth_mode,
            storage_key=storage_key,
            headers=headers,
            stealth_config=self.stealth_config,
            config=config,
            proxy_config=proxy_config,
            session_id=session_id,
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
        return await _run_task(
            self,
            agent,
            instruction,
            url,
            visual_mode,
            stealth_mode,
            captcha_solver,
            run_logger,
            runtime,
        )

    async def _take_screenshot(self, page, step: int, target_dir: Optional[Path] = None) -> str:
        return await _take_screenshot_func(page, step, target_dir)

    async def _extract_page_context(self, page, include_dom: bool = False, dom_max_chars: int = 20000) -> Dict:
        return await extract_page_context(page, include_dom=include_dom, dom_max_chars=dom_max_chars)

    async def _generate_action(self, instruction: str, page_context: Dict, step: int, run_logger: RunLogger | None = None, runtime: Dict[str, Any] | None = None) -> Dict:
        from .llm_planner import generate_action
        rt = runtime or {}
        max_chars = int(rt.get("planner_max_cap", 20000) or 20000)
        growth = int(rt.get("planner_growth_per_step", 2000) or 2000)
        max_cap = int(rt.get("planner_max_cap", 20000) or 20000)
        return await generate_action(self.llm, instruction, page_context, step, run_logger, max_chars=max_chars, growth_per_step=growth, max_cap=max_cap)

    async def _execute_action(self, page, action: Dict, runtime: Dict[str, Any]):
        return await execute_action(page, action, runtime)

    # Backward-compat wrappers for tests
    def _looks_like_human_verify_text(self, txt: str) -> bool:  # noqa: N802
        return looks_like_human_verify_text(txt)

    async def _handle_human_verification(self, page, run_logger: RunLogger | None = None):  # noqa: N802
        return await handle_human_verification(page, run_logger)

    async def _detect_honeypot(self, page) -> bool:
        return await _detect_honeypot_func(page)

    def _parse_bql(self, query: str) -> str:
        return _parse_bql_util(query)

    def _build_rerun_curl(self, instruction: str | None, url: str, params: Dict[str, Any], top_level: Dict[str, Any] | None = None) -> str:
        return _build_rerun_curl_func(instruction, url, params, top_level)

    def _diagnose_url_issue(self, url: str) -> Dict[str, Any]:
        return _diagnose_url_issue_func(url)

    def _parse_form_pairs(self, instruction: str | None) -> Dict[str, str]:
        return _parse_form_pairs_func(instruction)

    async def _deterministic_form_fill(self, instruction: str, page, run_logger: RunLogger | None = None) -> Optional[Dict[str, Any]]:
        return await _deterministic_form_fill_func(instruction, page, run_logger)

    async def _open_page_with_prechecks(
        self,
        agent,
        url: Optional[str],
        instruction: str,
        stealth_mode: bool,
        captcha_solver: bool,
        runtime: Dict[str, Any],
        run_logger: RunLogger,
        result: Dict[str, Any],
        lower_instr: str,
    ):
        return await _open_page_with_prechecks_func(
            agent,
            url,
            instruction,
            stealth_mode,
            captcha_solver,
            runtime,
            run_logger,
            result,
            lower_instr,
            self._setup_browser,
            self.captcha_solver,
            self._build_rerun_curl,
        )

    async def _multi_stage_product_extract(self, instruction: str, page, run_logger: RunLogger | None):
        return await _multi_stage_product_extract_func(instruction, page, run_logger)

    def _progress_tick(
        self,
        page_context: Dict[str, Any],
        last_sig: Optional[str],
        no_progress: int,
        progressive_depth: int,
        runtime: Dict[str, Any],
        run_logger: RunLogger | None,
        result: Dict[str, Any],
        instruction: str,
        url: Optional[str],
        stall_limit: int,
    ) -> tuple[Optional[str], int, int, bool]:
        return _progress_tick_func(
            page_context,
            last_sig,
            no_progress,
            progressive_depth,
            runtime,
            run_logger,
            result,
            instruction,
            url,
            stall_limit,
        )
