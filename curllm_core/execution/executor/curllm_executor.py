import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from curllm_core.config import config
from curllm_core.logger import RunLogger
from curllm_core.llm_factory import setup_llm as setup_llm_factory
from curllm_core.llm_config import LLMConfig
from curllm_core.agent_factory import create_agent as create_agent_factory
from curllm_core.vision import VisionAnalyzer
from curllm_core.captcha import CaptchaSolver
from curllm_core.stealth import StealthConfig
from curllm_core.runtime import parse_runtime_from_instruction
from curllm_core.headers import normalize_headers
from curllm_core.browser_setup import setup_browser
from curllm_core.wordpress import WordPressAutomation
from curllm_core.proxy import resolve_proxy
from curllm_core.page_context import extract_page_context
from curllm_core.actions import execute_action
from curllm_core.result_evaluator import evaluate_run_success
from curllm_core.human_verify import handle_human_verification, looks_like_human_verify_text
from curllm_core.extraction import generic_fastpath, direct_fastpath, product_heuristics, fallback_extract, extract_articles_eval, validate_with_llm, extract_links_by_selectors
from curllm_core.bql import BQLExecutor
from curllm_core.screenshots import take_screenshot as _take_screenshot_func
from curllm_core.form_fill import deterministic_form_fill as _deterministic_form_fill_func, parse_form_pairs as _parse_form_pairs_func
from curllm_core.llm_field_filler import llm_guided_field_fill as _llm_guided_field_fill_func
from curllm_core.config_logger import log_all_config
from curllm_core.planner_progress import progress_tick as _progress_tick_func
from curllm_core.product_extract import multi_stage_product_extract as _multi_stage_product_extract_func
from curllm_core.bql_utils import parse_bql as _parse_bql_util
from curllm_core.dom_utils import detect_honeypot as _detect_honeypot_func
from curllm_core.diagnostics import diagnose_url_issue as _diagnose_url_issue_func
from curllm_core.navigation import open_page_with_prechecks as _open_page_with_prechecks_func
from curllm_core.rerun_cmd import build_rerun_curl as _build_rerun_curl_func
from curllm_core.task_runner import run_task as _run_task
from curllm_core.result_store import apply_diff_and_store as _apply_diff_and_store


class CurllmExecutor:
    """Main browser automation executor with LLM support"""
    def __init__(self, llm_config: Optional[LLMConfig] = None):
        """
        Initialize executor.
        
        Args:
            llm_config: Optional LLMConfig for multi-provider LLM support.
                       If not provided, uses environment/config defaults.
                       
        Example:
            # Local Ollama (default)
            executor = CurllmExecutor()
            
            # OpenAI
            executor = CurllmExecutor(LLMConfig(provider="openai/gpt-4o-mini"))
            
            # Anthropic
            executor = CurllmExecutor(LLMConfig(provider="anthropic/claude-3-haiku-20240307"))
            
            # Gemini
            executor = CurllmExecutor(LLMConfig(provider="gemini/gemini-2.0-flash"))
            
            # Groq (fast cloud Llama)
            executor = CurllmExecutor(LLMConfig(provider="groq/llama3-70b-8192"))
        """
        self._llm_config = llm_config
        self.llm = self._setup_llm(llm_config)
        self.vision_analyzer = VisionAnalyzer()
        self.captcha_solver = CaptchaSolver()
        self.stealth_config = StealthConfig()

    def _setup_llm(self, llm_config: Optional[LLMConfig] = None) -> Any:
        return setup_llm_factory(llm_config)

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
        use_v2: bool = True,  # v2 LLM-driven API is now default
    ) -> Dict[str, Any]:
        # Parse optional runtime params embedded in JSON instruction
        instruction, runtime = parse_runtime_from_instruction(instruction)
        
        # Reconstruct bash command for logging
        cmd_parts = ["curllm"]
        if visual_mode:
            cmd_parts.append("--visual")
        if stealth_mode:
            cmd_parts.append("--stealth")
        if use_bql:
            cmd_parts.append("--bql")
        if headers:
            for key, val in headers.items():
                cmd_parts.append(f'-H "{key}: {val}"')
        if url:
            cmd_parts.append(f'"{url}"')
        if instruction:
            # Escape quotes in instruction
            escaped_instr = instruction.replace('"', '\\"')
            cmd_parts.append(f'-d "{escaped_instr}"')
        command_line = " ".join(cmd_parts)
        
        run_logger = RunLogger(instruction=instruction, url=url, command_line=command_line)
        run_logger.log_heading(f"curllm run: {datetime.now().isoformat()}")
        
        # Log all configuration using centralized config_logger
        log_all_config(run_logger, visual_mode, stealth_mode, use_bql, runtime)
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
                            items = page_obj.get("items") or page_obj.get("select") or []
                            if isinstance(items, list):
                                articles = []
                                for it in items:
                                    if isinstance(it, dict):
                                        title = it.get("title") or it.get("text")
                                        url2 = it.get("url") or it.get("href") or it.get("attr")
                                        articles.append({"title": title or "", "url": url2 or ""})
                                result_data = {"articles": articles}
                    except Exception:
                        pass
                    if result_data is None:
                        result_data = bql_result.get("data", bql_result)

                    # Validation pass (LLM) if enabled
                    try:
                        if config.validation_enabled and result_data is not None:
                            v = await validate_with_llm(self.llm, instruction, result_data, run_logger)
                            if v is not None:
                                result_data = v
                    except Exception:
                        pass

                    # Store and diff (if configured)
                    try:
                        mode = str((runtime.get("diff_mode") or "none")).strip().lower()
                        store = bool(runtime.get("store_results")) or (mode in ("new", "changed", "delta", "all"))
                        if store:
                            fields = runtime.get("diff_fields") or ["href", "title", "url"]
                            keep = int(runtime.get("keep_history", 10) or 10)
                            result_key = runtime.get("result_key")
                            out_data, meta = _apply_diff_and_store(url, instruction, result_key, result_data, fields, keep, mode)
                            result_data = out_data
                            try:
                                run_logger.log_kv("diff.prev_count", str(meta.get("prev_count")))
                                run_logger.log_kv("diff.curr_count", str(meta.get("curr_count")))
                                run_logger.log_kv("diff.new_count", str(meta.get("new_count")))
                                run_logger.log_kv("diff.changed_count", str(meta.get("changed_count")))
                                run_logger.log_kv("diff.removed_count", str(meta.get("removed_count")))
                                run_logger.log_kv("diff.store_key", str(meta.get("store_key")))
                            except Exception:
                                pass
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
                        "reason": "BQL query executed successfully",
                        "result": result_data,
                        "steps_taken": 1,
                        "screenshots": [],
                        "timestamp": datetime.now().isoformat(),
                        "run_log": str(run_logger.path),
                    }
                    run_logger.log_text("✅ BQL execution finished successfully.")
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
                                "success": bool(post_url),
                                "reason": "WordPress post published successfully" if post_url else "WordPress post publication failed",
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
                            if out_res["success"]:
                                run_logger.log_text("✅ WordPress automation finished successfully.")
                            else:
                                run_logger.log_text("❌ WordPress automation failed.")
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

            # Validation pass (LLM) before finalizing (always when enabled)
            # Skip for specs data (dict with non-product keys like 'specifications')
            try:
                final_data = result.get("data")
                if config.validation_enabled and final_data is not None:
                    # Skip LLM validation for specs - it's already validated by DSL
                    is_specs_data = (
                        isinstance(final_data, dict) and 
                        ('specifications' in final_data or 
                         (not any(k in final_data for k in ['items', 'products', 'links'])))
                    )
                    if not is_specs_data:
                        v = await validate_with_llm(self.llm, instruction, final_data, run_logger)
                        if v is not None:
                            result["data"] = v
            except Exception:
                pass

            # Store and diff (if configured)
            try:
                final_data2 = result.get("data")
                mode = str((runtime.get("diff_mode") or "none")).strip().lower()
                store = bool(runtime.get("store_results")) or (mode in ("new", "changed", "delta", "all"))
                diff_meta = None
                if store and final_data2 is not None:
                    fields = runtime.get("diff_fields") or ["href", "title", "url"]
                    keep = int(runtime.get("keep_history", 10) or 10)
                    result_key = runtime.get("result_key")
                    out_data, meta = _apply_diff_and_store(url, instruction, result_key, final_data2, fields, keep, mode)
                    result["data"] = out_data
                    diff_meta = meta
            except Exception:
                diff_meta = None

            # Intelligent success evaluation
            success, reason, eval_metadata = evaluate_run_success(result, instruction, run_logger)
            
            # Validate results against instruction (check for missing fields)
            try:
                from .result_corrector import analyze_and_report, detect_required_fields
                
                correction = analyze_and_report(instruction, result.get("data"), run_logger)
                
                if correction.missing_fields:
                    eval_metadata["missing_fields"] = correction.missing_fields
                    eval_metadata["warnings"].append(
                        f"Missing requested fields: {', '.join(correction.missing_fields)}"
                    )
                    
                    # Add suggestions to hints
                    if correction.suggestions:
                        hints = (result.get("meta", {}) or {}).get("hints", [])
                        hints.extend(correction.suggestions)
                        if "meta" not in result:
                            result["meta"] = {}
                        result["meta"]["hints"] = hints
                        
            except Exception as e:
                logger.debug(f"Result correction failed: {e}")
            
            res = {
                "success": success,
                "reason": reason,
                "result": result.get("data"),
                "steps_taken": result.get("steps", 0),
                "screenshots": result.get("screenshots", []),
                "timestamp": datetime.now().isoformat(),
                "run_log": str(run_logger.path),
                "hints": (result.get("meta", {}) or {}).get("hints", []),
                "suggested_commands": (result.get("meta", {}) or {}).get("suggested_commands", []),
                "evaluation": eval_metadata
            }
            try:
                if diff_meta:
                    res["diff"] = diff_meta
            except Exception:
                pass
            
            # Log the final result to the run log
            run_logger.log_text("\n## Final Result\n")
            
            # Log extracted data summary
            final_data = result.get("data")
            if final_data:
                if isinstance(final_data, dict):
                    if "specifications" in final_data:
                        run_logger.log_text(f"**Extracted Specifications:** {final_data.get('count', 0)} parameters")
                        run_logger.log_code("json", json.dumps(final_data.get("specifications", {}), indent=2, ensure_ascii=False))
                    elif "items" in final_data:
                        run_logger.log_text(f"**Extracted Items:** {final_data.get('count', 0)} items")
                        run_logger.log_code("json", json.dumps(final_data.get("items", [])[:5], indent=2, ensure_ascii=False))
                        if final_data.get("count", 0) > 5:
                            run_logger.log_text(f"... and {final_data.get('count', 0) - 5} more items")
                    else:
                        run_logger.log_code("json", json.dumps(final_data, indent=2, ensure_ascii=False)[:2000])
                elif isinstance(final_data, list):
                    run_logger.log_text(f"**Extracted Items:** {len(final_data)} items")
                    run_logger.log_code("json", json.dumps(final_data[:5], indent=2, ensure_ascii=False))
            
            # Log full result JSON
            run_logger.log_text("\n### Full Response JSON\n")
            run_logger.log_code("json", json.dumps(res, indent=2, ensure_ascii=False, default=str))
            
            if success:
                run_logger.log_text(f"\n✅ Run finished successfully: {reason}")
            else:
                run_logger.log_text(f"\n❌ Run finished with failure: {reason}")
            
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

    async def _extract_page_context(self, page, include_dom: bool = False, dom_max_chars: int = 20000, form_focused: bool = False) -> Dict:
        return await extract_page_context(page, include_dom=include_dom, dom_max_chars=dom_max_chars, form_focused=form_focused)

    async def _generate_action(self, instruction: str, page_context: Dict, step: int, run_logger: RunLogger | None = None, runtime: Dict[str, Any] | None = None) -> Dict:
        from .llm_planner import generate_action
        rt = runtime or {}
        max_chars = int(rt.get("planner_base_chars", rt.get("planner_max_cap", 20000)) or 20000)
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

    async def _deterministic_form_fill(self, instruction: str, page, run_logger: RunLogger | None = None, domain_dir: Optional[str] = None, use_v2: bool = True) -> Optional[Dict[str, Any]]:
        """
        Fill form using deterministic approach, with optional LLM-guided fallback.
        
        Hybrid approach:
        1. Try deterministic first (fast) - or v2 LLM-driven if use_v2=True
        2. If failed and LLM filler enabled, try LLM-guided per-field (smart)
        
        Args:
            use_v2: Use LLM-driven v2 form filling (no hardcoded selectors)
        """
        # Use v2 LLM-driven form filling if enabled
        if use_v2:
            try:
                from curllm_core.v2 import llm_form_fill
                result = await llm_form_fill(instruction, page, self.llm, run_logger)
                return {
                    'filled': result.filled_fields,
                    'submitted': result.submitted,
                    'success': result.success,
                }
            except Exception as e:
                if run_logger:
                    run_logger.log_text(f"⚠️  V2 form fill failed: {e}, falling back to v1")
        
        # Try deterministic approach first (v1)
        result = await _deterministic_form_fill_func(instruction, page, run_logger, domain_dir)
        
        # If failed and LLM filler is enabled, try LLM-guided approach
        if config.llm_field_filler_enabled:
            # Check if deterministic ACTUALLY succeeded
            is_success = (
                result and 
                isinstance(result, dict) and 
                result.get("submitted") is True and
                "error" not in result
            )
            
            if not is_success:
                if run_logger:
                    run_logger.log_text("⚠️  Deterministic form fill failed or incomplete")
                    run_logger.log_text("🤖 Attempting LLM-guided per-field filling...")
                
                try:
                    # Get form fields from page context
                    form_fields = await page.evaluate("""
                        () => {
                            const forms = [];
                            document.querySelectorAll('form').forEach(form => {
                                const fields = [];
                                form.querySelectorAll('input, textarea, select').forEach(el => {
                                    if (el.offsetParent !== null) {  // visible
                                        fields.push({
                                            name: el.name || el.id,
                                            id: el.id,
                                            type: el.type || 'text',
                                            required: el.required,
                                            placeholder: el.placeholder,
                                            label: (el.labels && el.labels[0]) ? el.labels[0].innerText : ''
                                        });
                                    }
                                });
                                if (fields.length > 0) {
                                    forms.push({id: form.id, fields: fields});
                                }
                            });
                            return forms;
                        }
                    """)
                    
                    if form_fields and len(form_fields) > 0:
                        # Use first form's fields
                        fields = form_fields[0].get("fields", [])
                        if fields:
                            # Call LLM-guided filler
                            llm_result = await _llm_guided_field_fill_func(
                                page=page,
                                instruction=instruction,
                                form_fields=fields,
                                llm_client=self.llm,
                                run_logger=run_logger
                            )
                            
                            if llm_result and llm_result.get("submitted"):
                                if run_logger:
                                    run_logger.log_text("✅ LLM-guided form fill succeeded!")
                                return {
                                    "form_fill": llm_result,
                                    "submitted": True,
                                    "method": "llm_guided"
                                }
                            else:
                                if run_logger:
                                    run_logger.log_text("⚠️  LLM-guided form fill also failed")
                        else:
                            if run_logger:
                                run_logger.log_text("⚠️  No form fields detected for LLM-guided approach")
                    else:
                        if run_logger:
                            run_logger.log_text("⚠️  No forms detected on page")
                            
                except Exception as e:
                    if run_logger:
                        run_logger.log_text(f"❌ LLM-guided form fill error: {e}")
        
        return result

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
