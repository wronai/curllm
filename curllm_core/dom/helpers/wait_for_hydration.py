"""
SPA Hydration Wait Utilities

Provides functions to wait for Single Page Applications to fully hydrate
and render their dynamic content before DOM analysis.

This solves the CSR/SPA rendering problem where links loaded via JavaScript
are not visible immediately after page load.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def wait_for_spa_hydration(
    page,
    timeout_ms: int = 5000,
    check_interval_ms: int = 200,
    min_links: int = 5,
) -> bool:
    """
    Wait for SPA to hydrate by monitoring DOM changes.
    
    Strategy:
    1. Wait for initial DOM content
    2. Monitor link count - SPA typically adds navigation after hydration
    3. Wait for link count to stabilize
    4. Additional wait for lazy-loaded elements
    
    Args:
        page: Playwright page object
        timeout_ms: Maximum wait time in milliseconds
        check_interval_ms: Interval between checks
        min_links: Minimum expected links for a hydrated page
        
    Returns:
        True if hydration detected, False if timeout
    """
    start_time = asyncio.get_event_loop().time()
    timeout_sec = timeout_ms / 1000
    check_interval_sec = check_interval_ms / 1000
    
    prev_link_count = 0
    stable_count = 0
    required_stable_checks = 2
    
    while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
        try:
            # Count visible links
            link_count = await page.evaluate("""() => {
                return document.querySelectorAll('a[href]').length;
            }""")
            
            # Check if link count is stable
            if link_count == prev_link_count and link_count >= min_links:
                stable_count += 1
                if stable_count >= required_stable_checks:
                    logger.debug(f"SPA hydration complete: {link_count} links stable")
                    return True
            else:
                stable_count = 0
                prev_link_count = link_count
            
            await asyncio.sleep(check_interval_sec)
            
        except Exception as e:
            logger.debug(f"Hydration check error: {e}")
            await asyncio.sleep(check_interval_sec)
    
    logger.debug(f"SPA hydration timeout after {timeout_ms}ms, links: {prev_link_count}")
    return False


async def wait_for_interactive_elements(
    page,
    timeout_ms: int = 3000,
) -> bool:
    """
    Wait for interactive elements (buttons, inputs) to appear.
    
    Useful for pages where navigation is via buttons/icons not <a> tags.
    
    Args:
        page: Playwright page object
        timeout_ms: Maximum wait time
        
    Returns:
        True if interactive elements found
    """
    try:
        # Wait for common interactive elements
        await page.wait_for_selector(
            'button, input, [role="button"], [onclick], a[href]',
            state='attached',
            timeout=timeout_ms
        )
        return True
    except Exception:
        return False


async def wait_for_navigation_ready(
    page,
    timeout_ms: int = 5000,
) -> bool:
    """
    Combined wait for navigation elements to be ready.
    
    This is the main entry point for ensuring SPA content is loaded.
    
    Args:
        page: Playwright page object
        timeout_ms: Maximum wait time
        
    Returns:
        True if navigation elements are ready
    """
    # First wait for basic interactivity
    await wait_for_interactive_elements(page, min(timeout_ms, 2000))
    
    # Then wait for SPA hydration
    hydrated = await wait_for_spa_hydration(
        page,
        timeout_ms=timeout_ms,
        min_links=3,  # Lower threshold for faster response
    )
    
    # Additional small delay for any final renders
    if hydrated:
        await asyncio.sleep(0.2)
    
    return hydrated


async def ensure_page_ready(page, wait_ms: int = 3000) -> None:
    """
    Ensure page is ready for DOM analysis.
    
    Simple wrapper that handles common waiting patterns.
    Call this before extracting links or finding elements.
    
    Args:
        page: Playwright page object
        wait_ms: Maximum wait time in milliseconds
    """
    try:
        # Wait for DOM content loaded
        await page.wait_for_load_state('domcontentloaded', timeout=wait_ms)
    except Exception:
        pass
    
    # Wait for SPA hydration
    await wait_for_navigation_ready(page, timeout_ms=wait_ms)
