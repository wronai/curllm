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


async def _find_link_keyword_fallback(page, goal: str, llm=None) -> Optional[LinkInfo]:
    """
    DEPRECATED: Legacy fallback keyword-based link finding.
    
    Use _find_link_with_llm() or _find_link_statistical() instead.
    
    This function derives keywords dynamically from the goal string.
    If LLM is available, it generates semantic translations dynamically.
    Otherwise falls back to minimal static translations.
    """
    logger.debug(f"Using keyword fallback for goal: {goal}")
    
    # Extract core keywords from goal string
    goal_clean = goal.replace('find_', '').replace('_', ' ')
    goal_words = goal_clean.split()
    
    all_keywords = list(goal_words)
    
    # Try LLM for semantic keyword expansion
    if llm:
        try:
            prompt = f"""Generate 5-8 keywords/synonyms for finding "{goal_clean}" links on a Polish e-commerce website.
Include Polish and English terms. Return ONLY comma-separated words, no explanation.
Example for "cart": koszyk,basket,bag,shopping cart,zakupy"""
            
            response = await llm.aquery(prompt)
            llm_keywords = [kw.strip().lower() for kw in response.split(',') if kw.strip()]
            all_keywords.extend(llm_keywords[:8])
            logger.debug(f"LLM generated keywords: {llm_keywords[:8]}")
        except Exception as e:
            logger.debug(f"LLM keyword generation failed: {e}")
    
    # Fallback: Add minimal translations for language coverage (only if LLM not used)
    if len(all_keywords) == len(goal_words):
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
