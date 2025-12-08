import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo
from .extract_all_links import extract_all_links

async def find_links_by_aria(
    page,
    keywords: List[str]
) -> List[LinkInfo]:
    """
    Find links by aria-label content.
    
    Useful for icon-only links with accessibility labels.
    """
    all_links = await extract_all_links(page)
    results = []
    
    for link in all_links:
        if not link.aria_label:
            continue
        
        aria_lower = link.aria_label.lower()
        matches = sum(1 for kw in keywords if kw.lower() in aria_lower)
        if matches > 0:
            link.score = matches / len(keywords)
            link.method = 'aria_label'
            results.append(link)
    
    return sorted(results, key=lambda x: x.score, reverse=True)
