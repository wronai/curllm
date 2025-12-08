import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo
from .extract_all_links import extract_all_links

logger = logging.getLogger(__name__)

async def _find_link_statistical(page, goal: str) -> Optional[LinkInfo]:
    """Use statistical analysis to find best link"""
    # Extract goal keywords from the goal string
    goal_words = goal.replace('find_', '').replace('_', ' ').split()
    
    all_links = await extract_all_links(page)
    
    if not all_links:
        return None
    
    # Score each link based on word overlap
    for link in all_links:
        link_text = f"{link.text} {link.url} {link.aria_label or ''} {link.title or ''}".lower()
        
        score = 0.0
        for word in goal_words:
            if word.lower() in link_text:
                score += 2.0
        
        # Location bonus
        if link.location in ['nav', 'header', 'footer']:
            score += 0.5
        
        link.score = score
    
    # Get best match
    best_links = sorted(all_links, key=lambda x: x.score, reverse=True)
    
    if best_links and best_links[0].score > 1.5:
        best = best_links[0]
        best.method = 'statistical'
        logger.info(f"Statistical analysis found link for {goal}: {best.url} (score: {best.score:.1f})")
        return best
    
    return None
