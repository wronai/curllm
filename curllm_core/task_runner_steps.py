"""
Task Runner Steps - Step execution handlers

Contains functions for executing individual steps during task execution:
- _step_visual - Visual analysis step
- _step_page_context - Page context gathering step
- _remediate_if_empty - Remediation when page context is empty
- _progress_and_maybe_break - Progress tracking and break detection

Extracted from task_runner.py for better modularity.
"""

from typing import Any, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

from .page_utils import auto_scroll as _auto_scroll, accept_cookies as _accept_cookies


async def step_visual(
    executor,
    page,
    step: int,
    domain_dir,
    captcha_solver: bool,
    run_logger,
    result: Dict[str, Any]
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Execute visual analysis step.
    
    Takes screenshot and optionally performs visual analysis.
    
    Returns:
        Tuple of (screenshot_path, visual_analysis_dict)
    """
    screenshot_path = None
    visual_analysis = None
    
    try:
        screenshot_path = await executor._take_screenshot(page, step, target_dir=domain_dir)
        if screenshot_path:
            result["screenshots"].append(screenshot_path)
            
            # Try visual analysis if available
            if hasattr(executor, '_analyze_screenshot'):
                try:
                    visual_analysis = await executor._analyze_screenshot(
                        screenshot_path, 
                        captcha_solver=captcha_solver
                    )
                    if run_logger and visual_analysis:
                        run_logger.log_text(f"Visual analysis: {visual_analysis.get('summary', 'done')}")
                except Exception as e:
                    logger.debug(f"Visual analysis failed: {e}")
    except Exception as e:
        logger.debug(f"Screenshot failed: {e}")
    
    return screenshot_path, visual_analysis


async def step_page_context(
    executor,
    page,
    runtime: Dict[str, Any],
    last_screenshot_path: Optional[str],
    last_visual_analysis: Optional[Dict[str, Any]],
    form_focused: bool = False
) -> Dict[str, Any]:
    """
    Gather page context for LLM planning.
    
    Returns:
        Dict with page context information
    """
    try:
        context = await executor._get_page_context(
            page,
            runtime=runtime,
            screenshot_path=last_screenshot_path,
            visual_analysis=last_visual_analysis,
            form_focused=form_focused
        )
        return context or {}
    except Exception as e:
        logger.debug(f"Page context failed: {e}")
        return {}


async def remediate_if_empty(
    page,
    runtime: Dict[str, Any],
    run_logger,
    page_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Try to remediate when page context is empty.
    
    Attempts:
    - Accept cookies
    - Scroll down
    - Wait for content
    
    Returns:
        Updated page context
    """
    # Check if context is empty
    dom_text = page_context.get("dom_text", "") or ""
    if len(dom_text.strip()) > 100:
        return page_context
    
    if run_logger:
        run_logger.log_text("⚠️ Page context empty, attempting remediation...")
    
    # Try accepting cookies
    try:
        await _accept_cookies(page)
        if run_logger:
            run_logger.log_text("  → Attempted cookie acceptance")
    except Exception:
        pass
    
    # Try scrolling
    try:
        await _auto_scroll(page, max_scrolls=2)
        if run_logger:
            run_logger.log_text("  → Scrolled page")
    except Exception:
        pass
    
    # Wait for dynamic content
    try:
        await page.wait_for_timeout(1000)
    except Exception:
        pass
    
    # Re-gather context
    try:
        new_context = await page.evaluate("""
            () => ({
                url: window.location.href,
                title: document.title,
                dom_text: document.body?.innerText?.slice(0, 10000) || '',
                links_count: document.querySelectorAll('a').length,
                forms_count: document.querySelectorAll('form').length,
            })
        """)
        page_context.update(new_context)
        
        if run_logger and len(new_context.get("dom_text", "")) > len(dom_text):
            run_logger.log_text(f"  ✓ Remediation successful, got {len(new_context.get('dom_text', ''))} chars")
    except Exception:
        pass
    
    return page_context


async def progress_and_maybe_break(
    executor,
    page_context: Dict[str, Any],
    last_sig: Optional[str],
    no_progress: int,
    progressive_depth: int,
    runtime: Dict[str, Any],
    run_logger,
    result: Dict[str, Any],
    instruction: str,
    url: Optional[str],
    stall_limit: int
) -> Tuple[Optional[str], int, int, bool]:
    """
    Track progress and determine if we should break the loop.
    
    Returns:
        Tuple of (new_signature, no_progress_count, progressive_depth, should_break)
    """
    # Calculate page signature for progress detection
    sig = _compute_page_signature(page_context)
    
    if sig == last_sig:
        no_progress += 1
        if run_logger:
            run_logger.log_text(f"⚠️ No progress detected ({no_progress}/{stall_limit})")
    else:
        no_progress = 0
        progressive_depth += 1
    
    # Check if we should break
    should_break = no_progress >= stall_limit
    
    if should_break and run_logger:
        run_logger.log_text(f"❌ Stall limit reached ({stall_limit}), breaking loop")
    
    return sig, no_progress, progressive_depth, should_break


def _compute_page_signature(page_context: Dict[str, Any]) -> str:
    """Compute a signature for the current page state for progress detection."""
    url = page_context.get("url", "")
    title = page_context.get("title", "")
    dom_text = page_context.get("dom_text", "")
    
    # Use hash of key elements
    import hashlib
    content = f"{url}|{title}|{dom_text[:1000]}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


# Backward compatibility aliases
_step_visual = step_visual
_step_page_context = step_page_context
_remediate_if_empty = remediate_if_empty
_progress_and_maybe_break = progress_and_maybe_break
