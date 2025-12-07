"""
Task Runner Fallback - Fallback and finalization handlers

Contains functions for fallback extraction and result finalization:
- _maybe_products_heuristics - Fallback product extraction
- _maybe_articles_no_click - Fallback article extraction
- _finalize_fallback - Final fallback attempt

Extracted from task_runner.py for better modularity.
"""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

from .extraction import (
    product_heuristics,
    extract_articles_eval,
    fallback_extract,
)


async def maybe_products_heuristics(
    instruction: str,
    page,
    run_logger,
    result: Dict[str, Any]
) -> bool:
    """
    Try product heuristics as a fallback.
    
    Returns:
        True if products were found, False otherwise
    """
    lower_instr = instruction.lower()
    product_keywords = [
        "produkt", "product", "cen", "price", "sklep", "shop",
        "kupić", "buy", "zamów", "order", "ofert", "offer"
    ]
    
    if not any(k in lower_instr for k in product_keywords):
        return False
    
    try:
        items = await product_heuristics(page)
        if items and len(items) >= 2:
            result["data"] = {
                "items": items,
                "count": len(items),
                "method": "products_heuristics_fallback"
            }
            if run_logger:
                run_logger.log_text(f"✓ Fallback product heuristics: {len(items)} items")
            return True
    except Exception as e:
        logger.debug(f"Product heuristics fallback failed: {e}")
    
    return False


async def maybe_articles_no_click(
    executor,
    instruction: str,
    page,
    run_logger,
    page_context: Dict[str, Any],
    runtime: Dict[str, Any],
    result: Dict[str, Any]
) -> bool:
    """
    Try article extraction without clicking as a fallback.
    
    Returns:
        True if articles were found, False otherwise
    """
    lower_instr = instruction.lower()
    article_keywords = [
        "article", "artykuł", "artykul", "post", "news",
        "wiadomości", "wiadomosci", "blog"
    ]
    
    if not any(k in lower_instr for k in article_keywords):
        return False
    
    try:
        items = await extract_articles_eval(page)
        if items and len(items) >= 2:
            result["data"] = {
                "articles": items,
                "count": len(items),
                "method": "articles_no_click_fallback"
            }
            if run_logger:
                run_logger.log_text(f"✓ Fallback articles (no-click): {len(items)} items")
            return True
    except Exception as e:
        logger.debug(f"Articles no-click fallback failed: {e}")
    
    return False


async def finalize_fallback(
    executor,
    instruction: str,
    url: Optional[str],
    page,
    run_logger,
    result: Dict[str, Any],
    domain_dir: Optional[str] = None,
    runtime: Optional[Dict[str, Any]] = None
) -> None:
    """
    Final fallback attempt when all else fails.
    
    Tries:
    1. Product heuristics
    2. Article extraction
    3. Generic fallback extraction
    4. Page content dump
    """
    runtime = runtime or {}
    
    if run_logger:
        run_logger.log_text("🔄 Running finalize fallback...")
    
    # Already have data?
    if result.get("data") and isinstance(result["data"], dict):
        items = result["data"].get("items") or result["data"].get("articles") or result["data"].get("products")
        if items and len(items) >= 2:
            if run_logger:
                run_logger.log_text("  ✓ Already have data, skipping fallback")
            return
    
    # Try product heuristics
    if await maybe_products_heuristics(instruction, page, run_logger, result):
        return
    
    # Try articles
    if await maybe_articles_no_click(executor, instruction, page, run_logger, {}, runtime, result):
        return
    
    # Try generic fallback
    try:
        fallback_data = await fallback_extract(page, instruction)
        if fallback_data and (fallback_data.get("items") or fallback_data.get("data")):
            result["data"] = fallback_data
            if run_logger:
                run_logger.log_text("  ✓ Generic fallback extraction succeeded")
            return
    except Exception as e:
        logger.debug(f"Generic fallback failed: {e}")
    
    # Last resort: page content dump
    try:
        content = await page.evaluate("""
            () => ({
                url: window.location.href,
                title: document.title,
                text: document.body?.innerText?.slice(0, 5000) || '',
                links_count: document.querySelectorAll('a').length,
                images_count: document.querySelectorAll('img').length,
            })
        """)
        result["data"] = {
            "fallback": "page_content",
            "content": content,
            "method": "page_dump"
        }
        if run_logger:
            run_logger.log_text("  ⚠️ Using page content dump as last resort")
    except Exception as e:
        logger.debug(f"Page dump failed: {e}")
        result["data"] = {"error": "All extraction methods failed", "method": "none"}


# Backward compatibility aliases
_maybe_products_heuristics = maybe_products_heuristics
_maybe_articles_no_click = maybe_articles_no_click
_finalize_fallback = finalize_fallback
