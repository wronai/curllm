from typing import Any, Dict, Optional
from .config import config
from .extraction import (
    generic_fastpath,
    direct_fastpath,
    product_heuristics,
    extract_articles_eval,
    validate_with_llm,
    extract_links_by_selectors,
)


async def try_early_form_fill(executor, instruction: str, page, domain_dir, run_logger, result: Dict[str, Any], lower_instr: str) -> Optional[Dict[str, Any]]:
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


async def try_early_articles(executor, instruction: str, page, run_logger, result: Dict[str, Any], lower_instr: str) -> Optional[Dict[str, Any]]:
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


async def try_selector_links(instruction: str, page, run_logger, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        sel_data = await extract_links_by_selectors(instruction, page, run_logger)
        if sel_data is not None:
            result["data"] = sel_data
            return result
    except Exception:
        return None
    return None


async def try_fastpaths(instruction: str, page, run_logger, result: Dict[str, Any], runtime: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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


async def try_product_extraction(executor, instruction: str, page, run_logger, result: Dict[str, Any], lower_instr: str) -> Optional[Dict[str, Any]]:
    if "product" not in lower_instr and "produkt" not in lower_instr:
        return None
    
    # Try orchestrator first if enabled
    if config.extraction_orchestrator_enabled:
        if run_logger:
            run_logger.log_text("🎭 Extraction Orchestrator enabled - trying orchestrated extraction")
        try:
            from .extraction_orchestrator import ExtractionOrchestrator
            from .page_context import extract_page_context
            
            page_context = await extract_page_context(page, dom_max_chars=20000, include_dom=False)
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


async def maybe_products_heuristics(instruction: str, page, run_logger, result: Dict[str, Any]) -> bool:
    try:
        res_products = await product_heuristics(instruction, page, run_logger)
        if res_products is not None:
            result["data"] = res_products
            return True
    except Exception:
        pass
    return False


async def maybe_articles_no_click(executor, instruction: str, page, run_logger, page_context: Dict[str, Any], runtime: Dict[str, Any], result: Dict[str, Any]) -> bool:
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
