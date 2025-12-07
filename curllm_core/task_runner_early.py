"""
Task Runner Early Extraction - Early extraction attempt handlers

Contains functions for trying various extraction methods early in the task:
- _smart_intent_check - Intent detection
- _try_early_form_fill - Early form filling
- _try_early_articles - Early article extraction
- _try_selector_links - Link extraction by selectors
- _try_fastpaths - Fast path extraction
- _try_product_extraction - Product extraction attempts

Extracted from task_runner.py for better modularity.
"""

from typing import Any, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)

from .extraction import (
    generic_fastpath,
    direct_fastpath,
    product_heuristics,
    extract_articles_eval,
    extract_links_by_selectors,
)


async def smart_intent_check(
    instruction: str,
    page_context: Optional[Dict[str, Any]],
    url: Optional[str],
    runtime: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Use smart intent detector to determine true user intent.
    Returns recommended runtime params based on intent.
    """
    try:
        from .intent_detector import detect_intent, TaskIntent
        
        intent_result = await detect_intent(instruction, page_context, url)
        
        # If extraction intent detected with high confidence, set no_form_fill
        if intent_result.intent in [
            TaskIntent.EXTRACT_PRODUCTS,
            TaskIntent.EXTRACT_ARTICLES,
            TaskIntent.EXTRACT_LINKS,
            TaskIntent.EXTRACT_TABLE,
            TaskIntent.EXTRACT_GENERIC,
            TaskIntent.COMPARE_DATA
        ] and intent_result.confidence >= 0.6:
            return {
                'intent': intent_result.intent.value,
                'confidence': intent_result.confidence,
                'reasoning': intent_result.reasoning,
                'recommended_params': intent_result.recommended_params,
                'should_skip_form_fill': True
            }
        
        return {
            'intent': intent_result.intent.value,
            'confidence': intent_result.confidence,
            'reasoning': intent_result.reasoning,
            'recommended_params': intent_result.recommended_params,
            'should_skip_form_fill': runtime.get('no_form_fill', False)
        }
    except Exception as e:
        logger.debug(f"Smart intent check failed: {e}")
        return {
            'intent': 'unknown',
            'confidence': 0,
            'reasoning': f'Intent detection failed: {e}',
            'recommended_params': {},
            'should_skip_form_fill': runtime.get('no_form_fill', False)
        }


async def try_early_form_fill(
    executor,
    instruction: str,
    page,
    domain_dir,
    run_logger,
    result: Dict[str, Any],
    lower_instr: str,
    runtime: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Try early form fill if instruction mentions forms.
    Returns result dict if successful, None otherwise.
    """
    runtime = runtime or {}
    
    # Check if form fill should be skipped based on smart intent detection
    if runtime.get('no_form_fill', False):
        if run_logger:
            run_logger.log_text("⏭️ Skipping early form fill (no_form_fill=True)")
        return None
    
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


async def try_early_articles(
    executor,
    instruction: str,
    page,
    run_logger,
    result: Dict[str, Any],
    lower_instr: str
) -> Optional[Dict[str, Any]]:
    """
    Try early article extraction if instruction mentions articles.
    Returns result dict if successful, None otherwise.
    """
    try:
        if any(k in lower_instr for k in ["article", "artykuł", "artykul", "post", "news", "wiadomości", "wiadomosci"]):
            items = await extract_articles_eval(page)
            if items and len(items) >= 3:
                result["data"] = {"articles": items}
                if run_logger:
                    run_logger.log_text(f"Early articles extraction: {len(items)} items")
                return result
    except Exception:
        return None
    return None


async def try_selector_links(
    instruction: str,
    page,
    run_logger,
    result: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Try to extract links using CSS selectors mentioned in instruction.
    Returns result dict if successful, None otherwise.
    """
    try:
        links = await extract_links_by_selectors(page, instruction)
        if links and len(links) > 0:
            result["data"] = {"links": links}
            if run_logger:
                run_logger.log_text(f"Selector links extraction: {len(links)} items")
            return result
    except Exception:
        return None
    return None


async def try_fastpaths(
    instruction: str,
    page,
    run_logger,
    result: Dict[str, Any],
    runtime: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Try fast path extraction methods.
    Returns result dict if successful, None otherwise.
    """
    if not runtime.get("fastpath", True):
        return None
    
    try:
        # Try direct fastpath first
        direct_result = await direct_fastpath(page, instruction)
        if direct_result and direct_result.get("items"):
            result["data"] = direct_result
            if run_logger:
                run_logger.log_text(f"Direct fastpath: {len(direct_result.get('items', []))} items")
            return result
        
        # Try generic fastpath
        generic_result = await generic_fastpath(page, instruction)
        if generic_result and generic_result.get("items"):
            result["data"] = generic_result
            if run_logger:
                run_logger.log_text(f"Generic fastpath: {len(generic_result.get('items', []))} items")
            return result
    except Exception:
        return None
    return None


async def try_product_extraction(
    executor,
    instruction: str,
    page,
    run_logger,
    result: Dict[str, Any],
    lower_instr: str
) -> Optional[Dict[str, Any]]:
    """
    Try product extraction if instruction mentions products.
    Returns result dict if successful, None otherwise.
    """
    product_keywords = [
        "produkt", "product", "cen", "price", "sklep", "shop", "store",
        "kupić", "buy", "zamów", "order", "ofert", "offer"
    ]
    
    if not any(k in lower_instr for k in product_keywords):
        return None
    
    try:
        items = await product_heuristics(page)
        if items and len(items) >= 2:
            result["data"] = {"items": items, "count": len(items), "method": "product_heuristics"}
            if run_logger:
                run_logger.log_text(f"Product extraction: {len(items)} items")
            return result
    except Exception as e:
        logger.debug(f"Product extraction failed: {e}")
    
    return None


# Backward compatibility aliases
_smart_intent_check = smart_intent_check
_try_early_form_fill = try_early_form_fill
_try_early_articles = try_early_articles
_try_selector_links = try_selector_links
_try_fastpaths = try_fastpaths
_try_product_extraction = try_product_extraction
