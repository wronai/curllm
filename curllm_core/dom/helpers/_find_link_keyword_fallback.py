"""
Keyword Fallback Link Finding - DEPRECATED

This module is a legacy fallback. Prefer:
1. _find_link_with_llm() - LLM semantic analysis
2. _find_link_statistical() - Word overlap scoring

This will be removed in a future version.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo
from .find_links_by_text import find_links_by_text
from .find_links_by_url_pattern import find_links_by_url_pattern
from .find_links_by_aria import find_links_by_aria

logger = logging.getLogger(__name__)

# Minimal translations for common goals (Polish <-> English)
# These are NOT hardcoded selectors - just language translations
GOAL_TRANSLATIONS = {
    'cart': ['koszyk', 'basket', 'bag'],
    'login': ['zaloguj', 'logowanie', 'loguj', 'signin', 'sign-in'],
    'register': ['rejestracja', 'zarejestruj', 'signup', 'sign-up', 'utworz'],
    'contact': ['kontakt', 'napisz', 'wiadomosc'],
    'shipping': ['dostawa', 'wysylka', 'delivery'],
    'returns': ['zwrot', 'reklamacja', 'oddaj'],
    'faq': ['pytania', 'pomoc', 'czesto'],
    'help': ['pomoc', 'wsparcie', 'support'],
    'warranty': ['gwarancja', 'serwis'],
    'terms': ['regulamin', 'warunki'],
    'privacy': ['prywatnosc', 'rodo', 'gdpr'],
    'careers': ['kariera', 'praca', 'rekrutacja', 'jobs'],
    'blog': ['artykuly', 'poradnik', 'news'],
    'account': ['zamowienia', 'profil', 'moje'],
    'stores': ['sklepy', 'salony', 'punkty'],
}


async def _find_link_keyword_fallback(page, goal: str) -> Optional[LinkInfo]:
    """
    DEPRECATED: Legacy fallback keyword-based link finding.
    
    Use _find_link_with_llm() or _find_link_statistical() instead.
    
    This function derives keywords dynamically from the goal string,
    with minimal translations for Polish/English coverage.
    """
    logger.debug(f"Using legacy keyword fallback for goal: {goal}")
    
    # Extract core keywords from goal string
    goal_clean = goal.replace('find_', '').replace('_', ' ')
    goal_words = goal_clean.split()
    
    # Add translations for better language coverage
    all_keywords = list(goal_words)
    for word in goal_words:
        translations = GOAL_TRANSLATIONS.get(word.lower(), [])
        all_keywords.extend(translations)
    
    # Derive URL patterns from keywords
    url_patterns = [f'/{kw}' for kw in all_keywords[:5]]
    
    candidates = []
    
    # Strategy 1: Text matching with derived keywords
    text_matches = await find_links_by_text(page, all_keywords[:10])
    for link in text_matches[:5]:
        link.score += 2.0
        candidates.append(link)
    
    # Strategy 2: URL pattern matching
    url_matches = await find_links_by_url_pattern(page, url_patterns)
    for link in url_matches[:5]:
        link.score += 3.0
        candidates.append(link)
    
    # Strategy 3: Aria label matching
    aria_matches = await find_links_by_aria(page, all_keywords[:5])
    for link in aria_matches[:3]:
        link.score += 1.5
        candidates.append(link)
    
    # Location bonus
    for link in candidates:
        if link.location in ['nav', 'header', 'footer']:
            link.score += 1.0
    
    # Deduplicate by URL
    seen_urls = set()
    unique_candidates = []
    for link in sorted(candidates, key=lambda x: x.score, reverse=True):
        if link.url not in seen_urls and link.score > 0:
            seen_urls.add(link.url)
            unique_candidates.append(link)
    
    # Minimum score threshold
    MIN_SCORE = 2.5
    unique_candidates = [c for c in unique_candidates if c.score >= MIN_SCORE]
    
    if unique_candidates:
        best = unique_candidates[0]
        best.method = 'keyword_fallback'
        logger.info(f"Found link for {goal}: {best.url} (score: {best.score:.1f})")
        return best
    
    return None
