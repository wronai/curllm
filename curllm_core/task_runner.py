from typing import Any, Dict, Optional
import json
import os
import logging

logger = logging.getLogger(__name__)
LOG_PREVIEW_CHARS = int(os.getenv("CURLLM_LOG_PREVIEW_CHARS", "1500") or 1500)

from .config import config
from .extraction import (
    generic_fastpath,
    direct_fastpath,
    product_heuristics,
    fallback_extract,
    extract_articles_eval,
    validate_with_llm,
    extract_links_by_selectors,
)
from .human_verify import handle_human_verification, looks_like_human_verify_text
from .page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies
from .captcha_slider import attempt_slider_challenge
from .slider_plugin import try_external_slider_solver


async def _try_early_form_fill(executor, instruction: str, page, domain_dir, run_logger, result: Dict[str, Any], lower_instr: str) -> Optional[Dict[str, Any]]:
    try:
        if any(k in lower_instr for k in ["form", "formularz", "fill", "wypełnij", "wypelnij", "submit"]):
            det_form = await executor._deterministic_form_fill(instruction, page, run_logger)
            if isinstance(det_form, dict) and (det_form.get("submitted") is True):
                try:
                    shot_path = await executor._take_screenshot(page, 0, target_dir=domain_dir)
                    result["screenshots"].append(shot_path)
                except Exception:
                    shot_path = None
                result["data"] = {"form_fill": det_form, **({"screenshot_saved": shot_path} if shot_path else {})}
                return result
    except Exception:
        return None
    return None


async def _try_early_articles(executor, instruction: str, page, run_logger, result: Dict[str, Any], lower_instr: str) -> Optional[Dict[str, Any]]:
    try:
        if any(k in lower_instr for k in ["title", "titles", "article", "artyku", "wpis", "blog", "news", "headline", "articl"]):
            det_items = await extract_articles_eval(page)
            if det_items:
                data_det = {"articles": det_items}
                try:
                    if config.validation_enabled and executor and executor.llm and (executor._should_validate(instruction, data_det)):
                        try:
                            dom_html = await page.content()
                        except Exception:
                            dom_html = None
                        v = await validate_with_llm(executor.llm, instruction, data_det, run_logger, dom_html=dom_html)
                        if v is not None:
                            data_det = v
                except Exception:
                    pass
                result["data"] = data_det
                return result
    except Exception:
        return None
    return None


async def _try_selector_links(instruction: str, page, run_logger, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        sel_data = await extract_links_by_selectors(instruction, page, run_logger)
        if sel_data is not None:
            result["data"] = sel_data
            return result
    except Exception:
        return None
    return None


async def _try_fastpaths(instruction: str, page, run_logger, result: Dict[str, Any], runtime: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not bool(runtime.get("fastpath")):
        run_logger.log_text("Fastpath disabled; using DOM-aware LLM planner.")
        return None
    try:
        res_generic = await generic_fastpath(instruction, page, run_logger)
        if res_generic is not None:
            result["data"] = res_generic
            return result
    except Exception as e:
        run_logger.log_kv("generic_fastpath_error", str(e))
    try:
        res_direct = await direct_fastpath(instruction, page, run_logger)
        if res_direct is not None:
            result["data"] = res_direct
            return result
    except Exception as e:
        run_logger.log_kv("direct_fastpath_error", str(e))
    return None


async def _try_product_extraction(executor, instruction: str, page, run_logger, result: Dict[str, Any], lower_instr: str) -> Optional[Dict[str, Any]]:
    if "product" not in lower_instr and "produkt" not in lower_instr:
        return None
    ms = await executor._multi_stage_product_extract(instruction, page, run_logger)
    if ms is None:
        return None
    data_ms = ms
    try:
        if config.validation_enabled and data_ms is not None and executor._should_validate(instruction, data_ms):
            try:
                dom_html = await page.content()
            except Exception:
                dom_html = None
            v = await validate_with_llm(executor.llm, instruction, data_ms, run_logger, dom_html=dom_html)
            if v is not None:
                data_ms = v
    except Exception:
        pass
    result["data"] = data_ms
    return result


async def _step_visual(executor, page, step: int, domain_dir, captcha_solver: bool, run_logger, result: Dict[str, Any]) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    last_screenshot_path: Optional[str] = None
    last_visual_analysis: Optional[Dict[str, Any]] = None
    screenshot_path = await executor._take_screenshot(page, step, target_dir=domain_dir)
    result["screenshots"].append(screenshot_path)
    visual_analysis = await executor.vision_analyzer.analyze(screenshot_path)
    last_screenshot_path = screenshot_path
    last_visual_analysis = visual_analysis if isinstance(visual_analysis, dict) else {"raw": str(visual_analysis)}
    if captcha_solver and isinstance(last_visual_analysis, dict) and last_visual_analysis.get("has_captcha"):
        await executor._handle_human_verification(page, run_logger)
    return last_screenshot_path, last_visual_analysis


async def _step_page_context(executor, page, runtime: Dict[str, Any], last_screenshot_path: Optional[str], last_visual_analysis: Optional[Dict[str, Any]]):
    page_context = await executor._extract_page_context(
        page,
        include_dom=bool(runtime.get("include_dom_html")),
        dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
    )
    if last_screenshot_path:
        page_context.setdefault("status", {})
        page_context["status"]["screenshot_path"] = last_screenshot_path
    if last_visual_analysis:
        page_context["vision"] = last_visual_analysis
    return page_context


async def _remediate_if_empty(page, runtime: Dict[str, Any], run_logger, page_context: Dict[str, Any]) -> Dict[str, Any]:
    inter_len = len(page_context.get("interactive", []) or [])
    dom_len = len(page_context.get("dom_preview", "") or "")
    ifr_len = len(page_context.get("iframes", []) or [])
    head_len = len(page_context.get("headings", []) or [])
    artc_len = len(page_context.get("article_candidates", []) or [])
    try:
        hv_possible = looks_like_human_verify_text(page_context.get("text", ""))
    except Exception:
        hv_possible = False
    page_context.setdefault("status", {})
    page_context["status"].update({
        "interactive_count": inter_len,
        "dom_preview_len": dom_len,
        "iframes_count": ifr_len,
        "headings_count": head_len,
        "article_candidates_count": artc_len,
        "human_verify_possible": bool(hv_possible),
    })
    # remediation branch
    if inter_len == 0 and dom_len == 0 and bool(runtime.get("include_dom_html")):
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
        page_context = await executor._extract_page_context(
            page,
            include_dom=True,
            dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
        )
        inter_len2 = len(page_context.get("interactive", []) or [])
        dom_len2 = len(page_context.get("dom_preview", "") or "")
        ifr_len2 = len(page_context.get("iframes", []) or [])
        try:
            hv_possible2 = looks_like_human_verify_text(page_context.get("text", ""))
        except Exception:
            hv_possible2 = False
        page_context.setdefault("status", {})
        page_context["status"].update({
            "interactive_count": inter_len2,
            "dom_preview_len": dom_len2,
            "iframes_count": ifr_len2,
            "human_verify_possible": bool(hv_possible2),
            "remediated": True,
        })
        run_logger.log_kv("interactive_count_after_remediate", str(inter_len2))
        run_logger.log_kv("dom_preview_len_after_remediate", str(dom_len2))
        run_logger.log_kv("iframes_count_after_remediate", str(ifr_len2))
    return page_context


def _progress_and_maybe_break(executor, page_context: Dict[str, Any], last_sig: Optional[str], no_progress: int, progressive_depth: int, runtime: Dict[str, Any], run_logger, result: Dict[str, Any], instruction: str, url: Optional[str], stall_limit: int):
    try:
        return executor._progress_tick(
            page_context=page_context,
            last_sig=last_sig,
            no_progress=no_progress,
            progressive_depth=progressive_depth,
            runtime=runtime,
            run_logger=run_logger,
            result=result,
            instruction=instruction,
            url=url,
            stall_limit=stall_limit,
        )
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"Progress check error: {e}")
        return last_sig, no_progress, progressive_depth, False


async def _planner_cycle(executor, instruction: str, page_context: Dict[str, Any], step: int, run_logger, runtime: Dict[str, Any], page):
    action = await executor._generate_action(
        instruction=instruction,
        page_context=page_context,
        step=step,
        run_logger=run_logger,
        runtime=runtime,
    )
    if run_logger:
        run_logger.log_text("Planned action:")
        run_logger.log_code("json", json.dumps(action))
    if action.get("type") == "complete":
        data = action.get("extracted_data", page_context)
        try:
            is_empty = (data is None) or (isinstance(data, (list, dict)) and len(data) == 0)
        except Exception:
            is_empty = False
        if is_empty:
            try:
                items2 = await extract_articles_eval(page)
                if items2:
                    data = {"articles": items2}
                    if run_logger:
                        run_logger.log_text(f"Filled extracted_data from deterministic extractor: {len(items2)}")
            except Exception:
                pass
        return True, data
    # Respect no_click runtime flag
    if runtime.get("no_click") and str(action.get("type")) == "click":
        if run_logger:
            run_logger.log_text("Skipping click due to no_click=true")
    else:
        await executor._execute_action(page, action, runtime)
    if run_logger:
        run_logger.log_text(f"Executed action: {action.get('type')}")
    return False, None


async def _maybe_products_heuristics(instruction: str, page, run_logger, result: Dict[str, Any]) -> bool:
    try:
        res_products = await product_heuristics(instruction, page, run_logger)
        if res_products is not None:
            result["data"] = res_products
            return True
    except Exception:
        pass
    return False


async def _maybe_articles_no_click(executor, instruction: str, page, run_logger, page_context: Dict[str, Any], runtime: Dict[str, Any], result: Dict[str, Any]) -> bool:
    try:
        looks_articles = any(k in (instruction or "").lower() for k in ["article", "artyku", "wpis", "blog", "title"])  # noqa: E501
        if looks_articles and runtime.get("no_click") and (page_context.get("headings") or page_context.get("article_candidates")):
            det_items = await extract_articles_eval(page)
            if det_items:
                data_det = {"articles": det_items}
                try:
                    if config.validation_enabled and executor._should_validate(instruction, data_det):
                        try:
                            dom_html = await page.content()
                        except Exception:
                            dom_html = None
                        v = await validate_with_llm(executor.llm, instruction, data_det, run_logger, dom_html=dom_html)
                        if v is not None:
                            data_det = v
                except Exception:
                    pass
                result["data"] = data_det
                if run_logger:
                    run_logger.log_text(f"Deterministic articles extracted: {len(det_items)}")
                return True
    except Exception as e:
        if run_logger:
            run_logger.log_kv("deterministic_articles_error", str(e))
    return False


async def _finalize_fallback(executor, instruction: str, url: Optional[str], page, run_logger, result: Dict[str, Any]) -> None:
    try:
        lower_instr2 = (instruction or "").lower()
        if any(k in lower_instr2 for k in ["form", "formularz", "fill", "wypełnij", "wypelnij", "submit"]):
            result["data"] = {
                "error": {
                    "type": "form_fill_failed",
                    "message": "Could not locate or fill form fields within the allowed steps.",
                }
            }
            try:
                params = {"include_dom_html": True, "preset": "deep_scan", "action_timeout_ms": 20000}
                cmd = executor._build_rerun_curl(instruction, url or "", params, top_level={"visual_mode": True, "stealth_mode": True, "url": url or ""})
                if cmd:
                    result["meta"]["hints"].append("Form fill failed. Retry with visual+stealth and deep_scan, or increase timeouts.")
                    result["meta"]["suggested_commands"].append(cmd)
            except Exception:
                pass
        else:
            result["data"] = await fallback_extract(instruction, page, run_logger)
            data = result.get("data")
            if isinstance(data, dict):
                filtered: Dict[str, Any] = {}
                if ("email" in lower_instr2 or "mail" in lower_instr2) and "emails" in data:
                    filtered["emails"] = data["emails"]
                if ("phone" in lower_instr2 or "tel" in lower_instr2 or "telefon" in lower_instr2) and "phones" in data:
                    filtered["phones"] = data["phones"]
                result["data"] = filtered
    except Exception:
        pass


async def run_task(
    executor,
    agent,
    instruction: str,
    url: Optional[str],
    visual_mode: bool,
    stealth_mode: bool,
    captcha_solver: bool,
    run_logger,
    runtime: Dict[str, Any],
) -> Dict:
    result: Dict[str, Any] = {"data": None, "steps": 0, "screenshots": [], "meta": {"hints": [], "suggested_commands": []}}
    lower_instr = (instruction or "").lower()

    page, domain_dir, stealth_mode, early = await executor._open_page_with_prechecks(
        agent=agent,
        url=url,
        instruction=instruction,
        stealth_mode=stealth_mode,
        captcha_solver=captcha_solver,
        runtime=runtime,
        run_logger=run_logger,
        result=result,
        lower_instr=lower_instr,
    )
    if early is not None:
        await page.close()
        return early

    # Expose canonical pairs (name/email/subject/phone/message) from instruction to the page for fill fallbacks
    try:
        canonical_pairs = executor._parse_form_pairs(instruction)
        if isinstance(canonical_pairs, dict):
            try:
                await page.evaluate("(data) => { window.__curllm_canonical = data; }", canonical_pairs)  # type: ignore[arg-type]
            except Exception:
                pass
    except Exception:
        pass

    # Early exits
    early_res = await _try_early_form_fill(executor, instruction, page, domain_dir, run_logger, result, lower_instr)
    if early_res is not None:
        await page.close()
        return early_res
    early_res = await _try_early_articles(executor, instruction, page, run_logger, result, lower_instr)
    if early_res is not None:
        await page.close()
        return early_res
    early_res = await _try_selector_links(instruction, page, run_logger, result)
    if early_res is not None:
        await page.close()
        return early_res
    early_res = await _try_fastpaths(instruction, page, run_logger, result, runtime)
    if early_res is not None:
        await page.close()
        return early_res
    early_res = await _try_product_extraction(executor, instruction, page, run_logger, result, lower_instr)
    if early_res is not None:
        await page.close()
        return early_res

    # Planner loop
    last_sig: Optional[str] = None
    no_progress = 0
    stall_limit = int(runtime.get("stall_limit", 5) or 5)
    progressive_depth = 1
    last_screenshot_path: Optional[str] = None
    last_visual_analysis: Optional[Dict[str, Any]] = None
    for step in range(config.max_steps):
        result["steps"] = step + 1
        if run_logger:
            run_logger.log_heading(f"Step {step + 1}")
        if visual_mode:
            last_screenshot_path, last_visual_analysis = await _step_visual(executor, page, step, domain_dir, captcha_solver, run_logger, result)

        # Try handle human verification banners/buttons each step
        try:
            await handle_human_verification(page, run_logger)
        except Exception:
            pass

        page_context = await _step_page_context(executor, page, runtime, last_screenshot_path, last_visual_analysis)
        page_context = await _remediate_if_empty(page, runtime, run_logger, page_context)

        # progress
        last_sig, no_progress, progressive_depth, should_break = _progress_and_maybe_break(
            executor,
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
        if should_break:
            break

        if run_logger:
            try:
                run_logger.log_text("Page context snapshot (truncated):")
                run_logger.log_code("json", json.dumps(page_context, indent=2)[:LOG_PREVIEW_CHARS])
            except Exception:
                pass

        # Product heuristics shortcut
        if await _maybe_products_heuristics(instruction, page, run_logger, result):
            break

        # Deterministic articles shortcut
        if await _maybe_articles_no_click(executor, instruction, page, run_logger, page_context, runtime, result):
            break

        # Planner step
        done, data = await _planner_cycle(executor, instruction, page_context, step, run_logger, runtime, page)
        if done:
            result["data"] = data
            break

        if await executor._detect_honeypot(page):
            logger.warning("Honeypot detected, skipping field")

    if result.get("data") is None:
        await _finalize_fallback(executor, instruction, url, page, run_logger, result)

    await page.close()
    return result
