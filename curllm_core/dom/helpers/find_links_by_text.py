import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo
from .extract_all_links import extract_all_links

async def find_links_by_text(
    page, 
    keywords: List[str],
    case_sensitive: bool = False
) -> List[LinkInfo]:
    """
    Find links containing specific text keywords.
    
    Args:
        page: Playwright page
        keywords: List of keywords to search for
        case_sensitive: Whether to match case
    """
    all_links = await extract_all_links(page)
    results = []
    
    for link in all_links:
        text_to_search = link.text + ' ' + (link.aria_label or '') + ' ' + (link.title or '')
        if not case_sensitive:
            text_to_search = text_to_search.lower()
            search_keywords = [k.lower() for k in keywords]
        else:
            search_keywords = keywords
        
        matches = sum(1 for kw in search_keywords if kw in text_to_search)
        if matches > 0:
            link.score = matches / len(keywords)
            link.method = 'text_match'
            results.append(link)
    
    return sorted(results, key=lambda x: x.score, reverse=True)
