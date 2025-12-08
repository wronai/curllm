import re
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .find_search_input import find_search_input

logger = logging.getLogger(__name__)

async def execute_search(
    page,
    query: str,
    wait_ms: int = 2000,
    llm=None
) -> bool:
    """
    Execute a search on the current page.
    
    Returns True if search was executed successfully.
    """
    search_input = await find_search_input(page, llm=llm)
    
    if search_input:
        try:
            el = await page.query_selector(search_input.selector)
            if el:
                # Store current URL to detect navigation
                url_before = page.url
                
                await el.click()
                await asyncio.sleep(0.2)  # Wait for focus
                await el.fill('')
                await el.type(query, delay=50)  # Slower typing to seem human
                await asyncio.sleep(0.3)  # Wait before submit
                await page.keyboard.press('Enter')
                
                # Wait for navigation or AJAX results
                try:
                    # First wait for any navigation
                    await page.wait_for_load_state('domcontentloaded', timeout=10000)
                    
                    # If URL changed, wait for networkidle (full load)
                    if page.url != url_before:
                        try:
                            await page.wait_for_load_state('networkidle', timeout=5000)
                        except Exception:
                            pass  # networkidle can timeout on some sites
                    
                    # Extra wait for AJAX/JS rendering
                    await asyncio.sleep(1.0)
                    
                    logger.debug(f"Search completed: {url_before} -> {page.url}")
                    return True
                    
                except Exception as nav_err:
                    logger.debug(f"Wait after search failed: {nav_err}")
                    # Still return True if search was submitted
                    await asyncio.sleep(1.0)
                    return True
                    
        except Exception as e:
            logger.debug(f"Search execution failed: {e}")
    
    return False
