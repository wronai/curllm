import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo
from .extract_all_links import extract_all_links

async def find_links_by_url_pattern(
    page,
    patterns: List[str]
) -> List[LinkInfo]:
    """
    Find links matching URL patterns (regex).
    
    Args:
        page: Playwright page
        patterns: List of regex patterns for URL matching
    """
    all_links = await extract_all_links(page)
    results = []
    
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    
    for link in all_links:
        for i, pattern in enumerate(compiled):
            if pattern.search(link.url):
                link.score = 1.0 - (i * 0.1)  # Earlier patterns score higher
                link.method = 'url_pattern'
                results.append(link)
                break
    
    return sorted(results, key=lambda x: x.score, reverse=True)
