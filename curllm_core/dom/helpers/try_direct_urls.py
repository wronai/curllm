import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


async def try_direct_urls(
    page,
    base_url: str,
    patterns: List[str]
) -> Optional[str]:
    """
    Try navigating to direct URL patterns.
    
    Useful when links aren't visible in DOM (JS-rendered or behind login).
    """
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    
    for pattern in patterns:
        test_url = base.rstrip('/') + pattern
        try:
            response = await page.goto(test_url, timeout=5000, wait_until="domcontentloaded")
            if response and response.status < 400:
                logger.info(f"Direct URL worked: {test_url}")
                return test_url
        except Exception:
            continue
    
    return None
