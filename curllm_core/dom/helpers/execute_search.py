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
                await el.click()
                await asyncio.sleep(0.2)  # Wait for focus
                await el.fill('')
                await el.type(query, delay=30)
                await asyncio.sleep(0.3)  # Wait before submit
                await page.keyboard.press('Enter')
                await page.wait_for_load_state('domcontentloaded', timeout=15000)
                await asyncio.sleep(0.5)  # Wait for results
                return True
        except Exception as e:
            logger.debug(f"Search execution failed: {e}")
    
    return False
