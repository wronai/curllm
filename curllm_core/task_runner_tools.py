"""
Task Runner Tools - Tool execution handlers

Contains the _execute_tool function and related helpers
for executing individual tools during task execution.

Extracted from task_runner.py for better modularity.
"""

from typing import Any, Dict, Optional
import json
import time
import logging

logger = logging.getLogger(__name__)

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
from .page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies


async def execute_tool(
    executor,
    page,
    instruction: str,
    tool_name: str,
    args: Dict[str, Any],
    runtime: Dict[str, Any],
    run_logger,
    domain_dir: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Execute a tool by name with given arguments.
    
    This is the main tool dispatcher that handles all tool types:
    - extract.emails, extract.links, extract.phones
    - articles.extract
    - products.extract, products.heuristics
    - form.fill, form.detect
    - browser.click, browser.scroll, browser.wait
    - etc.
    
    Args:
        executor: CurllmExecutor instance
        page: Playwright page
        instruction: User instruction
        tool_name: Name of tool to execute
        args: Tool arguments
        runtime: Runtime configuration
        run_logger: Logger instance
        domain_dir: Domain screenshot directory
        
    Returns:
        Tool result dict or None
    """
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
        
        # === Simple extractors ===
        if tn == "extract.emails":
            return await _handle_extract_emails(page, run_logger, _t_tool)
        
        if tn == "extract.links":
            return await _handle_extract_links(page, args, run_logger, _t_tool)
        
        if tn == "extract.phones":
            return await _handle_extract_phones(page, run_logger, _t_tool)
        
        # === Articles ===
        if tn == "articles.extract":
            return await _handle_articles_extract(page, run_logger, _t_tool)
        
        # === Products ===
        if tn == "products.extract" or tn == "products.heuristics":
            return await _handle_products_extract(
                executor, page, instruction, tn, args, runtime, run_logger, domain_dir, _t_tool
            )
        
        # === Browser actions ===
        if tn == "browser.scroll":
            return await _handle_browser_scroll(page, args, run_logger, _t_tool)
        
        if tn == "browser.click":
            return await _handle_browser_click(page, args, run_logger, runtime, _t_tool)
        
        if tn == "browser.wait":
            return await _handle_browser_wait(page, args, run_logger, _t_tool)
        
        if tn == "browser.screenshot":
            return await _handle_browser_screenshot(executor, page, run_logger, domain_dir, _t_tool)
        
        if tn == "browser.navigate" or tn == "browser.goto":
            return await _handle_browser_navigate(page, args, run_logger, _t_tool)
        
        if tn == "browser.cookies":
            return await _handle_browser_cookies(page, run_logger, _t_tool)
        
        # === Form ===
        if tn == "form.fill":
            return await _handle_form_fill(executor, page, instruction, args, run_logger, domain_dir, _t_tool)
        
        if tn == "form.detect":
            return await _handle_form_detect(page, run_logger, _t_tool)
        
        # === Finish/Done ===
        if tn == "done" or tn == "finish":
            return {"done": True, "reason": args.get("reason") if isinstance(args, dict) else None}
        
        # Unknown tool
        logger.warning(f"Unknown tool: {tn}")
        return {"error": f"Unknown tool: {tn}"}
        
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {"error": str(e)}


# === Tool handlers ===

async def _handle_extract_emails(page, run_logger, start_time: float) -> Dict[str, Any]:
    """Handle extract.emails tool"""
    emails = await _tool_extract_emails(page)
    if run_logger:
        try:
            run_logger.log_kv("emails_count", str(len(emails or [])))
            run_logger.log_kv("fn:tool.extract.emails_ms", str(int((time.time() - start_time) * 1000)))
        except Exception:
            pass
    return {"emails": emails}


async def _handle_extract_phones(page, run_logger, start_time: float) -> Dict[str, Any]:
    """Handle extract.phones tool"""
    phones = await _tool_extract_phones(page)
    if run_logger:
        try:
            run_logger.log_kv("phones_count", str(len(phones or [])))
            run_logger.log_kv("fn:tool.extract.phones_ms", str(int((time.time() - start_time) * 1000)))
        except Exception:
            pass
    return {"phones": phones}


async def _handle_extract_links(page, args: Dict, run_logger, start_time: float) -> Dict[str, Any]:
    """Handle extract.links tool"""
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
            run_logger.log_kv("fn:tool.extract.links_ms", str(int((time.time() - start_time) * 1000)))
        except Exception:
            pass
    
    return {"links": links}


async def _handle_articles_extract(page, run_logger, start_time: float) -> Dict[str, Any]:
    """Handle articles.extract tool"""
    items = await extract_articles_eval(page)
    if run_logger:
        try:
            run_logger.log_kv("articles_count", str(len(items or [])))
            run_logger.log_kv("fn:tool.articles.extract_ms", str(int((time.time() - start_time) * 1000)))
        except Exception:
            pass
    return {"articles": items or []}


async def _handle_products_extract(
    executor, page, instruction: str, tool_name: str, args: Dict, 
    runtime: Dict, run_logger, domain_dir: Optional[str], start_time: float
) -> Dict[str, Any]:
    """Handle products.extract and products.heuristics tools"""
    if tool_name == "products.heuristics" and run_logger:
        try:
            run_logger.log_text("⚠️ products.heuristics is DEPRECATED - using products.extract with dynamic detection")
        except Exception:
            pass
    
    # Use dynamic extraction
    thr = None
    try:
        v = args.get("threshold") if isinstance(args, dict) else None
        thr = int(v) if v is not None else None
    except Exception:
        thr = None
    
    # Try product_heuristics (which uses iterative extraction)
    items = await product_heuristics(page, thr)
    
    if run_logger:
        try:
            run_logger.log_kv("products_count", str(len(items or [])))
            run_logger.log_kv("fn:tool.products.extract_ms", str(int((time.time() - start_time) * 1000)))
        except Exception:
            pass
    
    return {"items": items or [], "count": len(items or [])}


async def _handle_browser_scroll(page, args: Dict, run_logger, start_time: float) -> Dict[str, Any]:
    """Handle browser.scroll tool"""
    direction = args.get("direction", "down") if isinstance(args, dict) else "down"
    amount = args.get("amount", 500) if isinstance(args, dict) else 500
    
    try:
        if direction == "down":
            await page.evaluate(f"window.scrollBy(0, {amount})")
        elif direction == "up":
            await page.evaluate(f"window.scrollBy(0, -{amount})")
        elif direction == "bottom":
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif direction == "top":
            await page.evaluate("window.scrollTo(0, 0)")
        
        if run_logger:
            run_logger.log_kv("scroll", f"{direction} {amount}px")
            run_logger.log_kv("fn:tool.browser.scroll_ms", str(int((time.time() - start_time) * 1000)))
        
        return {"scrolled": True, "direction": direction}
    except Exception as e:
        return {"error": str(e)}


async def _handle_browser_click(page, args: Dict, run_logger, runtime: Dict, start_time: float) -> Dict[str, Any]:
    """Handle browser.click tool"""
    selector = args.get("selector") if isinstance(args, dict) else None
    text = args.get("text") if isinstance(args, dict) else None
    
    if not selector and not text:
        return {"error": "No selector or text provided"}
    
    try:
        if selector:
            await page.click(selector, timeout=runtime.get("action_timeout_ms", 10000))
        elif text:
            await page.get_by_text(text).first.click(timeout=runtime.get("action_timeout_ms", 10000))
        
        if run_logger:
            run_logger.log_kv("clicked", selector or f"text: {text}")
            run_logger.log_kv("fn:tool.browser.click_ms", str(int((time.time() - start_time) * 1000)))
        
        return {"clicked": True, "selector": selector, "text": text}
    except Exception as e:
        return {"error": str(e)}


async def _handle_browser_wait(page, args: Dict, run_logger, start_time: float) -> Dict[str, Any]:
    """Handle browser.wait tool"""
    ms = args.get("ms", 1000) if isinstance(args, dict) else 1000
    selector = args.get("selector") if isinstance(args, dict) else None
    
    try:
        if selector:
            await page.wait_for_selector(selector, timeout=ms)
        else:
            await page.wait_for_timeout(ms)
        
        if run_logger:
            run_logger.log_kv("waited", f"{ms}ms" + (f" for {selector}" if selector else ""))
            run_logger.log_kv("fn:tool.browser.wait_ms", str(int((time.time() - start_time) * 1000)))
        
        return {"waited": True, "ms": ms}
    except Exception as e:
        return {"error": str(e)}


async def _handle_browser_screenshot(executor, page, run_logger, domain_dir: Optional[str], start_time: float) -> Dict[str, Any]:
    """Handle browser.screenshot tool"""
    try:
        path = await executor._take_screenshot(page, 0, target_dir=domain_dir)
        if run_logger:
            run_logger.log_kv("screenshot", path)
            run_logger.log_kv("fn:tool.browser.screenshot_ms", str(int((time.time() - start_time) * 1000)))
        return {"screenshot": path}
    except Exception as e:
        return {"error": str(e)}


async def _handle_browser_navigate(page, args: Dict, run_logger, start_time: float) -> Dict[str, Any]:
    """Handle browser.navigate/browser.goto tool"""
    url = args.get("url") if isinstance(args, dict) else None
    if not url:
        return {"error": "No URL provided"}
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        if run_logger:
            run_logger.log_kv("navigated", url)
            run_logger.log_kv("fn:tool.browser.navigate_ms", str(int((time.time() - start_time) * 1000)))
        return {"navigated": True, "url": page.url}
    except Exception as e:
        return {"error": str(e)}


async def _handle_browser_cookies(page, run_logger, start_time: float) -> Dict[str, Any]:
    """Handle browser.cookies (accept cookies) tool"""
    try:
        await _accept_cookies(page)
        if run_logger:
            run_logger.log_kv("cookies", "accepted")
            run_logger.log_kv("fn:tool.browser.cookies_ms", str(int((time.time() - start_time) * 1000)))
        return {"cookies_accepted": True}
    except Exception as e:
        return {"error": str(e)}


async def _handle_form_fill(executor, page, instruction: str, args: Dict, run_logger, domain_dir: Optional[str], start_time: float) -> Dict[str, Any]:
    """Handle form.fill tool"""
    try:
        result = await executor._deterministic_form_fill(instruction, page, run_logger, domain_dir)
        if run_logger:
            run_logger.log_kv("form_fill", "attempted")
            run_logger.log_kv("fn:tool.form.fill_ms", str(int((time.time() - start_time) * 1000)))
        return {"form_fill": result}
    except Exception as e:
        return {"error": str(e)}


async def _handle_form_detect(page, run_logger, start_time: float) -> Dict[str, Any]:
    """Handle form.detect tool"""
    try:
        forms = await page.evaluate("""
            () => {
                const forms = document.querySelectorAll('form');
                return Array.from(forms).map((f, i) => ({
                    index: i,
                    action: f.action,
                    method: f.method,
                    fields: f.querySelectorAll('input, textarea, select').length
                }));
            }
        """)
        if run_logger:
            run_logger.log_kv("forms_found", str(len(forms or [])))
            run_logger.log_kv("fn:tool.form.detect_ms", str(int((time.time() - start_time) * 1000)))
        return {"forms": forms}
    except Exception as e:
        return {"error": str(e)}


# Export for backward compatibility
_execute_tool = execute_tool
