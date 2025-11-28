from typing import Any, Dict, Optional
import json
import os
import logging
import time

logger = logging.getLogger(__name__)
LOG_PREVIEW_CHARS = int(os.getenv("CURLLM_LOG_PREVIEW_CHARS", "35000") or 35000)

from .config import config
from .extraction import (
    generic_fastpath,
    direct_fastpath,
    product_heuristics,
    fallback_extract,
    extract_articles_eval,
    validate_with_llm,
    extract_links_by_selectors,
    _extract_emails as _tool_extract_emails,
    _extract_phones as _tool_extract_phones,
    _extract_all_anchors as _tool_extract_all_anchors,
    _extract_anchors_filtered as _tool_extract_anchors_filtered,
    refine_instruction_llm,
)
from .human_verify import handle_human_verification, looks_like_human_verify_text
from .page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies
from .captcha_slider import attempt_slider_challenge
from .slider_plugin import try_external_slider_solver
from .result_store import previous_for_context as _previous_for_context
from .tool_retry import ToolRetryManager


async def _try_early_form_fill(executor, instruction: str, page, domain_dir, run_logger, result: Dict[str, Any], lower_instr: str) -> Optional[Dict[str, Any]]:
    try:
        if any(k in lower_instr for k in ["form", "formularz", "fill", "wypełnij", "wypelnij", "submit"]):
            det_form = await executor._deterministic_form_fill(instruction, page, run_logger, domain_dir)
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
                    if config.validation_enabled and executor and executor.llm:
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
    
    # Try orchestrator first if enabled
    if config.extraction_orchestrator_enabled:
        if run_logger:
            run_logger.log_text("🎭 Extraction Orchestrator enabled - trying orchestrated extraction")
        try:
            from .extraction_orchestrator import ExtractionOrchestrator
            from .page_context import extract_page_context
            
            page_context = await extract_page_context(page, max_chars=20000, include_dom_html=False)
            orchestrator = ExtractionOrchestrator(executor.llm, instruction, page, run_logger)
            
            import asyncio
            data_ms = await asyncio.wait_for(
                orchestrator.orchestrate(page_context),
                timeout=config.extraction_orchestrator_timeout
            )
            
            if data_ms is not None:
                if run_logger:
                    run_logger.log_text("✅ Orchestrator succeeded")
                result["data"] = data_ms
                return result
            else:
                if run_logger:
                    run_logger.log_text("⚠️ Orchestrator returned no data, falling back to multi-stage")
        except asyncio.TimeoutError:
            if run_logger:
                run_logger.log_text("⚠️ Orchestrator timeout, falling back to multi-stage")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ Orchestrator failed: {e}, falling back to multi-stage")
    
    # Fallback to original multi-stage extraction
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
    _t0 = time.time()
    screenshot_path = await executor._take_screenshot(page, step, target_dir=domain_dir)
    _ms = int((time.time() - _t0) * 1000)
    try:
        run_logger.log_kv("fn:_take_screenshot_ms", str(_ms))
    except Exception:
        pass
    result["screenshots"].append(screenshot_path)
    if run_logger:
        try:
            run_logger.log_image(screenshot_path, alt=f"Step {step+1} screenshot")
        except Exception:
            run_logger.log_text(f"Screenshot saved: {screenshot_path}")
    _t1 = time.time()
    visual_analysis = await executor.vision_analyzer.analyze(screenshot_path)
    _ms2 = int((time.time() - _t1) * 1000)
    try:
        run_logger.log_kv("fn:vision.analyze_ms", str(_ms2))
    except Exception:
        pass
    last_screenshot_path = screenshot_path
    last_visual_analysis = visual_analysis if isinstance(visual_analysis, dict) else {"raw": str(visual_analysis)}
    try:
        if isinstance(last_visual_analysis, dict):
            run_logger.log_kv("vision.has_captcha", str(bool(last_visual_analysis.get("has_captcha"))))
    except Exception:
        pass
    if captcha_solver and isinstance(last_visual_analysis, dict) and last_visual_analysis.get("has_captcha"):
        await executor._handle_human_verification(page, run_logger)
    return last_screenshot_path, last_visual_analysis


async def _step_page_context(executor, page, runtime: Dict[str, Any], last_screenshot_path: Optional[str], last_visual_analysis: Optional[Dict[str, Any]], form_focused: bool = False):
    page_context = await executor._extract_page_context(
        page,
        include_dom=bool(runtime.get("include_dom_html")),
        dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
        form_focused=form_focused,
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
            _t_hv2 = time.time()
            hv2 = await handle_human_verification(page, run_logger)
            try:
                run_logger.log_kv("fn:human.verify(remediate)_ms", str(int((time.time() - _t_hv2) * 1000)))
            except Exception:
                pass
            run_logger.log_kv("human_verify_remediation", str(bool(hv2)))
        except Exception as e:
            run_logger.log_kv("human_verify_remediation_error", str(e))
        try:
            _t_acc = time.time()
            await _accept_cookies(page)
            try:
                run_logger.log_kv("fn:accept_cookies_ms", str(int((time.time() - _t_acc) * 1000)))
            except Exception:
                pass
        except Exception:
            pass
        try:
            _t_scr = time.time()
            await _auto_scroll(page, steps=1, delay_ms=300)
            try:
                run_logger.log_kv("fn:auto_scroll_ms", str(int((time.time() - _t_scr) * 1000)))
            except Exception:
                pass
        except Exception:
            pass
        _t_pc2 = time.time()
        page_context = await executor._extract_page_context(
            page,
            include_dom=True,
            dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
        )
        try:
            run_logger.log_kv("fn:_extract_page_context(remediate)_ms", str(int((time.time() - _t_pc2) * 1000)))
        except Exception:
            pass
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


async def _progress_and_maybe_break(executor, page_context: Dict[str, Any], last_sig: Optional[str], no_progress: int, progressive_depth: int, runtime: Dict[str, Any], run_logger, result: Dict[str, Any], instruction: str, url: Optional[str], stall_limit: int):
    try:
        _t_prog = time.time()
        ret = executor._progress_tick(
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
        try:
            _ms = int((time.time() - _t_prog) * 1000)
            _ls, _np, _pd, _br = ret
            run_logger.log_code("json", json.dumps({"fn":"_progress_tick","ms":_ms,"no_progress":_np,"progressive_depth":_pd,"should_break":_br}))
        except Exception:
            pass
        return ret
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"Progress check error: {e}")
        return last_sig, no_progress, progressive_depth, False


async def _execute_tool(executor, page, instruction: str, tool_name: str, args: Dict[str, Any], runtime: Dict[str, Any], run_logger, domain_dir: Optional[str] = None):
    try:
        tn = str(tool_name or "").strip().lower()
        _t_tool = time.time()
        if run_logger:
            try:
                run_logger.log_text(f"Tool call: {tn}")
                if isinstance(args, dict) and args:
                    run_logger.log_code("json", json.dumps(args))
            except Exception:
                pass
        # Simple extractors
        if tn == "extract.emails":
            emails = await _tool_extract_emails(page)
            if run_logger:
                try:
                    run_logger.log_kv("emails_count", str(len(emails or [])))
                except Exception:
                    pass
            try:
                run_logger.log_kv(f"fn:tool.extract.emails_ms", str(int((time.time() - _t_tool) * 1000)))
            except Exception:
                pass
            return {"emails": emails}
        if tn == "extract.links":
            sel = None
            inc = None
            href_re = None
            text_re = None
            lim = None
            if isinstance(args, dict) and args:
                sel = args.get("selector") or args.get("css")
                inc = args.get("href_includes") or args.get("href_contains") or args.get("includes")
                href_re = args.get("href_regex")
                text_re = args.get("text_regex")
                try:
                    v = args.get("limit")
                    lim = int(v) if v is not None else None
                except Exception:
                    lim = None
            if sel or inc or href_re or text_re or lim:
                links = await _tool_extract_anchors_filtered(page, sel, inc, href_re, text_re, lim)
            else:
                links = await _tool_extract_all_anchors(page)
            if run_logger:
                try:
                    cnt = len(links or [])
                    sample = []
                    for e in (links or [])[:5]:
                        try:
                            sample.append(e.get("href") or e.get("url"))
                        except Exception:
                            continue
                    run_logger.log_text(f"extract.links -> {cnt} items")
                    run_logger.log_code("json", json.dumps({"sample": sample}))
                except Exception:
                    pass
            try:
                run_logger.log_kv(f"fn:tool.extract.links_ms", str(int((time.time() - _t_tool) * 1000)))
            except Exception:
                pass
            return {"links": links}
        if tn == "extract.phones":
            phones = await _tool_extract_phones(page)
            if run_logger:
                try:
                    run_logger.log_kv("phones_count", str(len(phones or [])))
                except Exception:
                    pass
            try:
                run_logger.log_kv(f"fn:tool.extract.phones_ms", str(int((time.time() - _t_tool) * 1000)))
            except Exception:
                pass
            return {"phones": phones}
        # Articles
        if tn == "articles.extract":
            items = await extract_articles_eval(page)
            if run_logger:
                try:
                    run_logger.log_kv("articles_count", str(len(items or [])))
                except Exception:
                    pass
            try:
                run_logger.log_kv(f"fn:tool.articles.extract_ms", str(int((time.time() - _t_tool) * 1000)))
            except Exception:
                pass
            return {"articles": items or []}
        # Products extraction - NEW DYNAMIC SYSTEM
        if tn == "products.extract" or tn == "products.heuristics":
            if tn == "products.heuristics" and run_logger:
                try:
                    run_logger.log_text("⚠️ products.heuristics is DEPRECATED - using products.extract with dynamic detection")
                except Exception:
                    pass
            
            # Use new dynamic extraction (redirects through product_heuristics which now uses iterative_extract)
            thr = None
            try:
                v = args.get("threshold") if isinstance(args, dict) else None
                thr = int(v) if v is not None else None
            except Exception:
                thr = None
            instr = instruction or ""
            if thr is not None:
                instr = f"{instr} under {thr}"
            
            # product_heuristics now redirects to iterative_extract (dynamic system)
            data = await product_heuristics(instr, page, run_logger)
            
            if run_logger:
                try:
                    cnt = len((data or {}).get("products") or []) if isinstance(data, dict) else 0
                    run_logger.log_kv("products_count", str(cnt))
                except Exception:
                    pass
            try:
                run_logger.log_kv(f"fn:tool.{tn}_ms", str(int((time.time() - _t_tool) * 1000)))
            except Exception:
                pass
            return data or {"products": []}
        # DOM snapshot
        if tn == "dom.snapshot":
            include_dom = bool(args.get("include_dom", runtime.get("include_dom_html", False))) if isinstance(args, dict) else bool(runtime.get("include_dom_html", False))
            max_chars = int(args.get("max_chars", runtime.get("dom_max_chars", 20000))) if isinstance(args, dict) else int(runtime.get("dom_max_chars", 20000))
            pc = await executor._extract_page_context(page, include_dom=include_dom, dom_max_chars=max_chars)
            if run_logger:
                try:
                    dom_len = len((pc or {}).get("dom_preview") or "")
                    inter_len = len((pc or {}).get("interactive") or [])
                    run_logger.log_code("json", json.dumps({"dom_preview_len": dom_len, "interactive_count": inter_len}))
                except Exception:
                    pass
            try:
                run_logger.log_kv(f"fn:tool.dom.snapshot_ms", str(int((time.time() - _t_tool) * 1000)))
            except Exception:
                pass
            return {"page_context": pc}
        # Cookies accept
        if tn == "cookies.accept":
            try:
                await _accept_cookies(page)
                if run_logger:
                    run_logger.log_kv("cookies.accept", "true")
                try:
                    run_logger.log_kv(f"fn:tool.cookies.accept_ms", str(int((time.time() - _t_tool) * 1000)))
                except Exception:
                    pass
                return {"accepted": True}
            except Exception as e:
                if run_logger:
                    run_logger.log_kv("cookies.accept", "false")
                try:
                    run_logger.log_kv(f"fn:tool.cookies.accept_ms", str(int((time.time() - _t_tool) * 1000)))
                except Exception:
                    pass
                return {"accepted": False, "error": str(e)}
        # Human verify
        if tn == "human.verify":
            ok = False
            try:
                hv = await handle_human_verification(page, run_logger)
                ok = bool(hv)
            except Exception:
                ok = False
            if run_logger:
                run_logger.log_kv("human.verify", str(ok))
            try:
                run_logger.log_kv(f"fn:tool.human.verify_ms", str(int((time.time() - _t_tool) * 1000)))
            except Exception:
                pass
            return {"ok": ok}
        
        # Atomic form tools (form.detect, form.fields, form.fill_field, etc.)
        if tn.startswith("form.") and tn != "form.fill":
            try:
                from curllm_core.streamware.components.form import execute_tool
                result = await execute_tool(page, tn, args or {}, run_logger)
                if run_logger:
                    run_logger.log_kv(f"fn:tool.{tn}_ms", str(int((time.time() - _t_tool) * 1000)))
                return result
            except Exception as e:
                return {"error": str(e)}
        
        # Form fill (full orchestration)
        if tn == "form.fill":
            try:
                # Check if LLM orchestrator should be used
                use_llm_orchestrator = runtime.get("llm_form_orchestrator", False) or \
                                      runtime.get("llm_orchestrator", False)
                
                # Merge values: instruction has priority over tool args
                merged_args = {}
                if isinstance(args, dict) and args:
                    merged_args.update(args)
                # Parse instruction and overwrite with instruction values
                try:
                    from curllm_core.form_fill import parse_form_pairs
                    raw_pairs = parse_form_pairs(instruction)
                    for k, v in raw_pairs.items():
                        lk = k.lower()
                        if any(x in lk for x in ["email", "e-mail", "mail"]):
                            merged_args["email"] = v
                        elif any(x in lk for x in ["name", "imi", "nazw", "full name", "fullname", "first name", "last name"]):
                            merged_args["name"] = v
                        elif any(x in lk for x in ["message", "wiadomo", "treść", "tresc", "content", "komentarz"]):
                            merged_args["message"] = v
                        elif any(x in lk for x in ["subject", "temat"]):
                            merged_args["subject"] = v
                        elif any(x in lk for x in ["phone", "telefon", "tel"]):
                            merged_args["phone"] = v
                except Exception:
                    pass
                if merged_args:
                    try:
                        await page.evaluate("(data) => { window.__curllm_canonical = Object.assign({}, window.__curllm_canonical||{}, data); }", merged_args)
                    except Exception:
                        pass
                
                det = None
                
                # TRY STREAMWARE ORCHESTRATOR FIRST (primary method)
                use_streamware = runtime.get("streamware_form", True)  # Default enabled
                if use_streamware:
                    try:
                        if run_logger:
                            run_logger.log_text("\n---\n# 🧩 Streamware Atomic Form Orchestrator\n")
                        
                        from curllm_core.streamware.components.form import form_fill_tool
                        streamware_result = await form_fill_tool(page, merged_args, run_logger)
                        
                        if streamware_result and streamware_result.get("form_fill", {}).get("submitted"):
                            det = streamware_result.get("form_fill")
                            if run_logger:
                                run_logger.log_text("\n## ✅ Streamware Result\n")
                                run_logger.log_text(f"**Status:** Form submitted successfully")
                        else:
                            if run_logger:
                                run_logger.log_text("⚠️ Streamware did not submit, trying legacy orchestrator")
                            det = None
                    except Exception as sw_err:
                        if run_logger:
                            run_logger.log_text(f"⚠️ Streamware failed: {sw_err}, trying legacy")
                        det = None
                
                # FALLBACK: TRY LLM ORCHESTRATOR MODE (if Streamware failed)
                if det is None and use_llm_orchestrator and hasattr(executor, 'llm') and executor.llm:
                    try:
                        # Check if transparent mode is enabled
                        use_transparent = runtime.get("llm_transparent_orchestrator", False)
                        
                        if use_transparent:
                            # TRANSPARENT ORCHESTRATOR - Multi-phase with full LLM control
                            if run_logger:
                                run_logger.log_text("🎭 TRANSPARENT LLM ORCHESTRATOR mode enabled")
                            
                            from curllm_core.llm_transparent_orchestrator import TransparentOrchestrator
                            from curllm_core.form_detector import detect_all_form_fields
                            from curllm_core.form_fill import parse_form_pairs
                            
                            # Detect fields
                            detection_result = await detect_all_form_fields(page)
                            detected_fields = detection_result.get('detected_fields', [])
                            
                            # Parse user data
                            user_data = parse_form_pairs(instruction)
                            
                            # Create transparent orchestrator
                            orchestrator = TransparentOrchestrator(executor.llm, run_logger)
                            
                            # Run multi-phase orchestration
                            det = await orchestrator.orchestrate_form_fill(
                                instruction, page, user_data, detected_fields
                            )
                            
                            if det and det.get("success"):
                                if run_logger:
                                    run_logger.log_text("✅ Transparent Orchestrator succeeded")
                                    run_logger.log_text(f"   Phases completed: {len(det.get('phases', []))}")
                                    run_logger.log_text(f"   Decisions logged: {len(det.get('decisions', []))}")
                                # Convert to standard format
                                det_standard = {
                                    "submitted": det.get("submitted", False),
                                    "filled": det.get("filled_fields", {}),
                                    "phases": det.get("phases", []),
                                    "decisions": det.get("decisions", [])
                                }
                                det = det_standard
                            else:
                                if run_logger:
                                    run_logger.log_text("⚠️  Transparent Orchestrator returned no result, falling back")
                                det = None
                        else:
                            # SIMPLE LLM ORCHESTRATOR (existing)
                            if run_logger:
                                run_logger.log_text("🤖 LLM Orchestrator mode enabled")
                            
                            from curllm_core.llm_form_orchestrator import llm_orchestrated_form_fill
                            det = await llm_orchestrated_form_fill(
                                instruction, page, executor.llm, run_logger, domain_dir
                            )
                            
                            if det and det.get("executed"):
                                if run_logger:
                                    run_logger.log_text("✅ LLM Orchestrator succeeded")
                                # Convert to standard format
                                det_standard = {
                                    "submitted": det.get("submitted", False),
                                    "filled": {op.get("field_id"): True for op in det.get("executed", [])},
                                    "errors": det.get("errors")
                                }
                                det = det_standard
                            else:
                                if run_logger:
                                    run_logger.log_text("⚠️  LLM Orchestrator returned no result, falling back to deterministic")
                                det = None
                    except Exception as llm_err:
                        if run_logger:
                            run_logger.log_text(f"⚠️  LLM Orchestrator failed: {str(llm_err)}, falling back to deterministic")
                        det = None
                
                # FALLBACK: DETERMINISTIC MODE (legacy)
                if det is None:
                    if run_logger:
                        run_logger.log_text("🔧 Using deterministic form fill (fallback)")
                    det = await executor._deterministic_form_fill(instruction, page, run_logger, domain_dir)
                
                if run_logger and isinstance(det, dict):
                    try:
                        run_logger.log_code("json", json.dumps({
                            "submitted": det.get("submitted"),
                            "errors": det.get("errors"),
                        }))
                    except Exception:
                        pass
                try:
                    run_logger.log_kv(f"fn:tool.form.fill_ms", str(int((time.time() - _t_tool) * 1000)))
                except Exception:
                    pass
                return {"form_fill": det}
            except Exception as e:
                try:
                    run_logger.log_kv(f"fn:tool.form.fill_ms", str(int((time.time() - _t_tool) * 1000)))
                except Exception:
                    pass
                return {"form_fill": {"submitted": False, "error": str(e)}}
    except Exception as e:
        return {"error": str(e)}


async def _planner_cycle(executor, instruction: str, page_context: Dict[str, Any], step: int, run_logger, runtime: Dict[str, Any], page, tool_history: list[Dict[str, Any]], domain_dir: Optional[str] = None, retry_manager=None):
    _t_gen = time.time()
    
    # Try hierarchical planner first (only for form-filling tasks)
    hierarchical_enabled = runtime.get("hierarchical_planner", True)
    if run_logger:
        run_logger.log_text(f"🔍 Checking hierarchical planner: enabled={hierarchical_enabled}, step={step}")
    
    if hierarchical_enabled and step == 1:  # Only on first step
        try:
            from .hierarchical_planner import hierarchical_plan, should_use_hierarchical
            
            # Smart bypass: check if hierarchical planner is worth the overhead
            if not should_use_hierarchical(instruction, page_context):
                if run_logger:
                    run_logger.log_text("✂️ Bypassing hierarchical planner (simple task detected)")
                # Fall through to standard planner
                action = await executor._generate_action(
                    instruction=instruction,
                    page_context=page_context,
                    step=step,
                    run_logger=run_logger,
                    runtime=runtime,
                )
            else:
                if run_logger:
                    run_logger.log_text("⚙️  Attempting hierarchical planner...")
                action = await hierarchical_plan(instruction, page_context, executor.llm, run_logger)
            if action is not None:
                # Hierarchical planner succeeded, use its action
                try:
                    run_logger.log_kv("fn:hierarchical_plan_ms", str(int((time.time() - _t_gen) * 1000)))
                except Exception:
                    pass
                if run_logger:
                    run_logger.log_text("✓ Hierarchical planner generated action")
            else:
                # Fall back to standard planner
                if run_logger:
                    run_logger.log_text("❌ Hierarchical planner returned None, falling back to standard planner")
                action = await executor._generate_action(
                    instruction=instruction,
                    page_context=page_context,
                    step=step,
                    run_logger=run_logger,
                    runtime=runtime,
                )
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"Hierarchical planner failed: {e}, falling back to standard")
            action = await executor._generate_action(
                instruction=instruction,
                page_context=page_context,
                step=step,
                run_logger=run_logger,
                runtime=runtime,
            )
    else:
        action = await executor._generate_action(
            instruction=instruction,
            page_context=page_context,
            step=step,
            run_logger=run_logger,
            runtime=runtime,
        )
    try:
        run_logger.log_kv("fn:generate_action_ms", str(int((time.time() - _t_gen) * 1000)))
    except Exception:
        pass
    # FALLBACK: Fix LLM mistake - type="fill" or type="form.fill" should be type="tool" + tool_name="form.fill"
    # Also handles hybrid case where LLM returns both type="fill" AND tool_name="form.fill"
    should_convert_to_tool = (
        (action.get("type") == "fill") or
        (action.get("type") == "form.fill") or
        (action.get("tool_name") == "form.fill" and action.get("type") != "tool")
    )
    
    if should_convert_to_tool:
        if run_logger:
            run_logger.log_text(f"⚠️  Auto-correcting: LLM returned type='{action.get('type')}' - converting to type='tool' + tool_name='form.fill'")
        
        # Extract form field values from action or args
        form_args = action.get("args", {}) if isinstance(action.get("args"), dict) else {}
        for key in ["name", "email", "subject", "phone", "message"]:
            if key in action and key not in form_args:
                form_args[key] = action[key]
        
        # Reconstruct as proper tool call
        action = {
            "type": "tool",
            "tool_name": "form.fill",
            "args": form_args,
            "reason": action.get("reason", "Filling contact form (auto-corrected)")
        }
        
        if run_logger:
            run_logger.log_text(f"   ✓ Corrected to: {{'type': 'tool', 'tool_name': 'form.fill', 'args': {form_args}}}")
    
    if run_logger:
        run_logger.log_text("Planned action:")
        run_logger.log_code("json", json.dumps(action))
        try:
            if action.get("type"):
                run_logger.log_kv("action_type", str(action.get("type")))
            if action.get("reason"):
                run_logger.log_kv("action_reason", str(action.get("reason")))
            if action.get("tool_name"):
                run_logger.log_kv("tool_name", str(action.get("tool_name")))
        except Exception:
            pass
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
    # Tool call branch
    if action.get("type") == "tool":
        tool_name = action.get("tool_name")
        args = action.get("args") or {}
        tool_res = await _execute_tool(executor, page, instruction, str(tool_name or ""), args if isinstance(args, dict) else {}, runtime, run_logger, domain_dir)
        if run_logger:
            try:
                run_logger.log_text(f"Tool executed: {tool_name}")
                run_logger.log_code("json", json.dumps(tool_res))
            except Exception:
                pass
        
        # AUTO-COMPLETE: If form was successfully submitted, end task immediately
        if str(tool_name).lower() == "form.fill" and isinstance(tool_res, dict):
            form_fill_result = tool_res.get("form_fill")
            if isinstance(form_fill_result, dict) and form_fill_result.get("submitted") is True:
                if run_logger:
                    run_logger.log_text("✅ Form successfully submitted - auto-completing task")
                try:
                    tool_history.append({"tool": tool_name, "args": args, "result": tool_res})
                except Exception:
                    pass
                # Return True to signal task completion
                return True, {
                    "form_submitted": True,
                    "message": "Contact form submitted successfully",
                    "fields_filled": form_fill_result.get("filled", {}),
                }
        
        # Check for tool failures and apply retry logic
        if retry_manager and isinstance(tool_res, dict) and "error" in tool_res:
            error_msg = str(tool_res.get("error", ""))
            if not retry_manager.should_retry(str(tool_name), error_msg):
                if run_logger:
                    run_logger.log_text(f"🛑 Tool {tool_name} failed repeatedly with same error - SKIPPING further retries")
                    summary = retry_manager.get_failure_summary(str(tool_name))
                    run_logger.log_code("json", json.dumps(summary, indent=2))
                
                # Try alternative approach
                alternative = retry_manager.get_alternative_approach(str(tool_name))
                if alternative:
                    if run_logger:
                        run_logger.log_text(f"🔄 Suggested alternative: {alternative}")
        
        try:
            tool_history.append({"tool": tool_name, "args": args, "result": tool_res})
        except Exception:
            pass
        return False, None
    # Respect no_click runtime flag
    if runtime.get("no_click") and str(action.get("type")) == "click":
        if run_logger:
            run_logger.log_text("Skipping click due to no_click=true")
    else:
        _t_exec = time.time()
        await executor._execute_action(page, action, runtime)
        try:
            run_logger.log_kv("fn:_execute_action_ms", str(int((time.time() - _t_exec) * 1000)))
        except Exception:
            pass
    if run_logger:
        run_logger.log_text(f"Executed action: {action.get('type')}")
        try:
            sel = action.get("selector")
            val = action.get("value") if isinstance(action.get("value"), (str, int, float)) else None
            timeout = action.get("timeoutMs") or runtime.get("action_timeout_ms")
            details = {k: v for k, v in {"selector": sel, "value": (str(val)[:80] if val is not None else None), "timeoutMs": timeout}.items() if v is not None}
            if details:
                run_logger.log_code("json", json.dumps(details))
        except Exception:
            pass
    return False, None


async def _maybe_products_heuristics(instruction: str, page, run_logger, result: Dict[str, Any]) -> bool:
    try:
        res_products = await product_heuristics(instruction, page, run_logger)
        if res_products is not None:
            data_ms = res_products
            try:
                if config.validation_enabled and getattr(executor, "llm", None):
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
                    if config.validation_enabled and getattr(executor, "llm", None):
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


async def _finalize_fallback(executor, instruction: str, url: Optional[str], page, run_logger, result: Dict[str, Any], domain_dir: Optional[str] = None) -> None:
    try:
        lower_instr2 = (instruction or "").lower()
        if any(k in lower_instr2 for k in ["form", "formularz", "fill", "wypełnij", "wypelnij", "submit"]):
            try:
                det2 = await executor._deterministic_form_fill(instruction, page, run_logger, domain_dir)
            except Exception:
                det2 = None
            if isinstance(det2, dict) and det2.get("submitted") is True:
                result["data"] = {"form_fill": det2}
                return
            result["data"] = {"error": {"type": "form_fill_failed", "message": "Could not locate or fill form fields within the allowed steps."}, **({"form_fill": det2} if det2 else {})}
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
                if any(k in lower_instr2 for k in ["link", "oferta", "oferty", "zlecenia", "zlecenie", "rfp"]) and "links" in data:
                    filtered["links"] = data["links"]
                result["data"] = filtered or data
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
    
    # Detect form-filling tasks to enable optimized context extraction
    is_form_task = any(k in lower_instr for k in ["form", "formularz", "fill", "wypełnij", "wypelnij", "submit", "wyślij", "wyslij", "contact"])
    if run_logger and is_form_task:
        run_logger.log_text("🎯 Form task detected - enabling form-focused context extraction")

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

    try:
        if bool(runtime.get("refine_instruction")) and getattr(executor, "llm", None):
            pc = await executor._extract_page_context(
                page,
                include_dom=bool(runtime.get("include_dom_html")),
                dom_max_chars=int(runtime.get("dom_max_chars", 20000) or 20000),
            )
            refined = await refine_instruction_llm(executor.llm, instruction, pc, run_logger)
            if isinstance(refined, str) and refined.strip():
                instruction = refined
                lower_instr = (instruction or "").lower()
                if run_logger:
                    run_logger.log_text("Instruction refined; continuing with refined instruction.")
    except Exception:
        pass

    prev_ctx: Optional[Dict[str, Any]] = None
    try:
        if bool(runtime.get("include_prev_results")):
            fields = runtime.get("diff_fields") or ["href", "title", "url"]
            prev_ctx = _previous_for_context(url, instruction, runtime.get("result_key"), fields)
    except Exception:
        prev_ctx = None

    # Try LLM-guided extractor first (LLM makes atomic decisions)
    if config.llm_guided_extractor_enabled and ("product" in lower_instr or "produkt" in lower_instr):
        if run_logger:
            run_logger.log_text("🤖 LLM-Guided Extractor enabled - LLM makes decisions at each atomic step")
        try:
            from .llm_guided_extractor import llm_guided_extract
            
            result_data = await llm_guided_extract(instruction, page, executor.llm, run_logger)
            
            if result_data and result_data.get("count", 0) > 0:
                if run_logger:
                    run_logger.log_text(f"✅ LLM-Guided Extractor succeeded - found {result_data['count']} items")
                result["data"] = result_data
                await page.close()
                return result
            else:
                reason = result_data.get("reason", "No items found") if result_data else "Extraction failed"
                if run_logger:
                    run_logger.log_text(f"⚠️ LLM-Guided Extractor returned no data: {reason}")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ LLM-Guided Extractor failed: {e}")
    
    # Try dynamic detector first (generic, adaptive)
    if config.iterative_extractor_enabled and ("product" in lower_instr or "produkt" in lower_instr):
        if run_logger:
            run_logger.log_text("🔍 Dynamic Detector enabled - adaptive pattern recognition")
        try:
            from .dynamic_detector import dynamic_extract
            
            result_data = await dynamic_extract(page, instruction, run_logger)
            
            if result_data and result_data.get("count", 0) > 0:
                if run_logger:
                    run_logger.log_text(f"✅ Dynamic Detector succeeded - found {result_data['count']} items")
                    run_logger.log_text(f"   Container: {result_data.get('container', {}).get('selector', 'unknown')}")
                    run_logger.log_text(f"   Confidence: {result_data.get('container', {}).get('confidence', 0):.2f}")
                result["data"] = result_data
                await page.close()
                return result
            else:
                reason = result_data.get("reason", "No items found") if result_data else "Detection failed"
                if run_logger:
                    run_logger.log_text(f"⚠️ Dynamic Detector returned no data: {reason}")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ Dynamic Detector failed: {e}")
    
    # Try iterative extractor second (pure JS, fast fallback)
    if config.iterative_extractor_enabled and ("product" in lower_instr or "produkt" in lower_instr):
        if run_logger:
            run_logger.log_text("🔄 Iterative Extractor enabled - trying atomic DOM queries")
        try:
            from .iterative_extractor import iterative_extract
            
            result_data = await iterative_extract(instruction, page, executor.llm, run_logger)
            
            if result_data and result_data.get("count", 0) > 0:
                if run_logger:
                    run_logger.log_text(f"✅ Iterative Extractor succeeded - found {result_data['count']} items")
                result["data"] = result_data
                await page.close()
                return result
            else:
                reason = result_data.get("reason", "No items found") if result_data else "Extraction failed"
                if run_logger:
                    run_logger.log_text(f"⚠️ Iterative Extractor returned no data: {reason}")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ Iterative Extractor failed: {e}")
    
    # Try BQL extraction orchestrator (second priority)
    if config.bql_extraction_orchestrator_enabled and ("product" in lower_instr or "produkt" in lower_instr or "extract" in lower_instr):
        if run_logger:
            run_logger.log_text("🔍 BQL Extraction Orchestrator enabled - trying BQL-based extraction")
        try:
            from .bql_extraction_orchestrator import BQLExtractionOrchestrator
            from .page_context import extract_page_context
            import asyncio
            
            page_context = await extract_page_context(page, dom_max_chars=30000, include_dom=False)
            
            if not page_context:
                if run_logger:
                    run_logger.log_text("⚠️ Failed to extract page context, skipping BQL orchestrator")
                raise ValueError("Page context extraction failed")
            
            orchestrator = BQLExtractionOrchestrator(executor.llm, instruction, page, run_logger)
            
            data_ms = await asyncio.wait_for(
                orchestrator.orchestrate(page_context),
                timeout=config.bql_extraction_orchestrator_timeout
            )
            
            if data_ms is not None:
                if run_logger:
                    run_logger.log_text("✅ BQL Orchestrator succeeded - returning result")
                result["data"] = data_ms
                await page.close()
                return result
            else:
                if run_logger:
                    run_logger.log_text("⚠️ BQL Orchestrator returned no data, trying standard extraction orchestrator")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ BQL Orchestrator failed: {e}, trying standard extraction orchestrator")
    
    # Try extraction orchestrator for product tasks (before planner loop)
    if config.extraction_orchestrator_enabled and ("product" in lower_instr or "produkt" in lower_instr):
        if run_logger:
            run_logger.log_text("🎭 Extraction Orchestrator enabled - trying orchestrated extraction")
        try:
            from .extraction_orchestrator import ExtractionOrchestrator
            from .page_context import extract_page_context
            import asyncio
            
            page_context = await extract_page_context(page, dom_max_chars=20000, include_dom=False)
            
            if not page_context:
                if run_logger:
                    run_logger.log_text("⚠️ Failed to extract page context, skipping extraction orchestrator")
                raise ValueError("Page context extraction failed")
            
            orchestrator = ExtractionOrchestrator(executor.llm, instruction, page, run_logger)
            
            data_ms = await asyncio.wait_for(
                orchestrator.orchestrate(page_context),
                timeout=config.extraction_orchestrator_timeout
            )
            
            if data_ms is not None:
                if run_logger:
                    run_logger.log_text("✅ Orchestrator succeeded - returning result")
                result["data"] = data_ms
                await page.close()
                return result
            else:
                if run_logger:
                    run_logger.log_text("⚠️ Orchestrator returned no data, continuing with standard planner")
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"⚠️ Orchestrator failed: {e}, continuing with standard planner")

    # Planner-only mode: skip all early shortcuts (form/articles/selector/direct/product)

    # Planner loop
    last_sig: Optional[str] = None
    no_progress = 0
    stall_limit = int(runtime.get("stall_limit", 5) or 5)
    progressive_depth = 1
    last_screenshot_path: Optional[str] = None
    last_visual_analysis: Optional[Dict[str, Any]] = None
    tool_history: list[Dict[str, Any]] = []
    
    # Initialize Tool Retry Manager to prevent infinite loops
    retry_manager = ToolRetryManager(max_same_error=2)
    
    for step in range(config.max_steps):
        result["steps"] = step + 1
        if run_logger:
            run_logger.log_heading(f"Step {step + 1}")
        if visual_mode:
            last_screenshot_path, last_visual_analysis = await _step_visual(executor, page, step, domain_dir, captcha_solver, run_logger, result)

        # Try handle human verification banners/buttons each step
        try:
            _t_hv = time.time()
            await handle_human_verification(page, run_logger)
            try:
                run_logger.log_kv("fn:human.verify_ms", str(int((time.time() - _t_hv) * 1000)))
            except Exception:
                pass
        except Exception:
            pass
        try:
            _t_acc_each = time.time()
            await _accept_cookies(page)
            try:
                run_logger.log_kv("fn:accept_cookies(per_step)_ms", str(int((time.time() - _t_acc_each) * 1000)))
            except Exception:
                pass
        except Exception:
            pass

        _t_pc = time.time()
        page_context = await _step_page_context(executor, page, runtime, last_screenshot_path, last_visual_analysis, form_focused=is_form_task)
        try:
            run_logger.log_kv("fn:_extract_page_context_ms", str(int((time.time() - _t_pc) * 1000)))
        except Exception:
            pass
        if prev_ctx:
            try:
                page_context["previous_results"] = prev_ctx
            except Exception:
                pass
        try:
            page_context["tool_history"] = list(tool_history)
        except Exception:
            pass
        page_context = await _remediate_if_empty(page, runtime, run_logger, page_context)

        # progress
        last_sig, no_progress, progressive_depth, should_break = await _progress_and_maybe_break(
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
                preview_len = LOG_PREVIEW_CHARS
                dom_chars = int(runtime.get("dom_max_chars", 20000) or 20000)
                dom_cap = int(runtime.get("dom_max_cap", 60000) or 60000)
                incl = bool(runtime.get("include_dom_html", False))
                def _prune_nulls(obj):
                    if isinstance(obj, dict):
                        pruned = {k: _prune_nulls(v) for k, v in obj.items()}
                        return {k: v for k, v in pruned.items() if v is not None and not (isinstance(v, (list, dict)) and len(v) == 0)}
                    if isinstance(obj, list):
                        pruned_list = [_prune_nulls(x) for x in obj]
                        pruned_list = [x for x in pruned_list if x is not None and not (isinstance(x, (list, dict)) and len(x) == 0)]
                        return pruned_list
                    return obj
                pc_json = json.dumps(_prune_nulls(page_context), indent=2)
                original_len = len(pc_json)
                logged_len = min(original_len, preview_len)
                truncated_by = max(0, original_len - logged_len)
                run_logger.log_text(
                    f"Page context snapshot (preview {preview_len} via CURLLM_LOG_PREVIEW_CHARS; "
                    f"original={original_len} chars; logged={logged_len}; truncated_by={truncated_by}; "
                    f"dom_max_chars={dom_chars} via CURLLM_DOM_MAX_CHARS; dom_max_cap={dom_cap} via CURLLM_DOM_MAX_CAP; "
                    f"include_dom_html={incl} via CURLLM_INCLUDE_DOM_HTML)"
                )
                run_logger.log_code("json", pc_json[:preview_len])
            except Exception:
                pass

        # Apply progressive context if enabled
        if config.progressive_context_enabled:
            from .progressive_context import build_progressive_context, get_context_stats
            
            progressive_ctx = build_progressive_context(
                page_context=page_context,
                step=step,
                instruction=instruction
            )
            
            ctx_stats = get_context_stats(progressive_ctx)
            if run_logger:
                run_logger.log_text(
                    f"📊 Progressive Context: step={step}, size={ctx_stats['size_chars']} chars "
                    f"(links:{ctx_stats['link_count']}, headings:{ctx_stats['heading_count']}, "
                    f"forms:{ctx_stats['form_count']}, has_dom:{ctx_stats['has_dom']})"
                )
            
            # Use progressive context for LLM
            page_context_for_planner = progressive_ctx
        else:
            page_context_for_planner = page_context

        # Planner step
        done, data = await _planner_cycle(executor, instruction, page_context_for_planner, step, run_logger, runtime, page, tool_history, domain_dir, retry_manager)
        if done:
            result["data"] = data
            break

        if await executor._detect_honeypot(page):
            logger.warning("Honeypot detected, skipping field")

    if result.get("data") is None:
        await _finalize_fallback(executor, instruction, url, page, run_logger, result, domain_dir)

    await page.close()
    return result
