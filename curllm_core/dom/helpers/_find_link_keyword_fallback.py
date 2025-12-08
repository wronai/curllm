import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from .link_info import LinkInfo
from .find_links_by_text import find_links_by_text
from .find_links_by_url_pattern import find_links_by_url_pattern
from .find_links_by_aria import find_links_by_aria

async def _find_link_keyword_fallback(page, goal: str) -> Optional[LinkInfo]:
    """
    Fallback keyword-based link finding.
    Uses predefined keyword configs for common goals.
    """
    # Goal-specific configurations (fallback only)
    goal_config = {
        'find_contact_form': {
            'text_keywords': ['kontakt', 'contact', 'napisz', 'formularz', 'pomoc', 'support', 'help'],
            'url_patterns': [r'/kontakt', r'/contact', r'/help', r'/support', r'/pomoc'],
            'aria_keywords': ['kontakt', 'contact', 'help'],
            'preferred_locations': ['footer', 'nav', 'header'],
        },
        'find_cart': {
            'text_keywords': ['koszyk', 'cart', 'basket', 'bag'],
            'url_patterns': [r'/koszyk', r'/cart', r'/basket', r'/bag'],
            'aria_keywords': ['koszyk', 'cart', 'basket', 'shopping'],
            'preferred_locations': ['header', 'nav'],
        },
        'find_login': {
            'text_keywords': ['zaloguj', 'login', 'logowanie', 'sign in', 'konto', 'account'],
            'url_patterns': [r'/login', r'/logowanie', r'/signin', r'/account', r'/konto'],
            'aria_keywords': ['login', 'zaloguj', 'account', 'konto'],
            'preferred_locations': ['header', 'nav'],
        },
        'find_register': {
            'text_keywords': ['zarejestruj', 'register', 'rejestracja', 'załóż konto', 'sign up'],
            'url_patterns': [r'/register', r'/rejestracja', r'/signup', r'/zaloz-konto'],
            'aria_keywords': ['register', 'zarejestruj', 'sign up'],
            'preferred_locations': ['header', 'nav'],
        },
        'find_shipping': {
            'text_keywords': ['dostawa', 'shipping', 'wysyłka', 'delivery', 'transport'],
            'url_patterns': [r'/dostawa', r'/shipping', r'/delivery', r'/wysylka'],
            'aria_keywords': ['dostawa', 'shipping', 'delivery'],
            'preferred_locations': ['footer', 'nav'],
        },
        'find_returns': {
            'text_keywords': ['zwrot', 'return', 'reklamacja', 'wymiana', 'oddaj'],
            'url_patterns': [r'/zwrot', r'/return', r'/reklamacj', r'/wymian'],
            'aria_keywords': ['zwrot', 'return', 'reklamacja'],
            'preferred_locations': ['footer', 'nav'],
        },
        'find_faq': {
            'text_keywords': ['faq', 'pytania', 'pomoc', 'help', 'centrum pomocy'],
            'url_patterns': [r'/faq', r'/help', r'/pomoc', r'/pytania'],
            'aria_keywords': ['faq', 'help', 'pomoc'],
            'preferred_locations': ['footer', 'nav'],
        },
        'find_help': {
            'text_keywords': ['pomoc', 'help', 'support', 'wsparcie', 'centrum pomocy'],
            'url_patterns': [r'/pomoc', r'/help', r'/support', r'/wsparcie'],
            'aria_keywords': ['pomoc', 'help', 'support'],
            'preferred_locations': ['footer', 'nav', 'header'],
        },
        'find_blog': {
            'text_keywords': ['blog', 'artykuły', 'articles', 'poradnik', 'aktualności', 'news'],
            'url_patterns': [r'/blog', r'/artyku', r'/news', r'/aktualnosci', r'/poradnik'],
            'aria_keywords': ['blog', 'news', 'articles'],
            'preferred_locations': ['nav', 'footer'],
        },
        'find_careers': {
            'text_keywords': ['kariera', 'career', 'praca', 'jobs', 'rekrutacja', 'hiring'],
            'url_patterns': [r'/kariera', r'/career', r'/praca', r'/jobs', r'/rekrutacja'],
            'aria_keywords': ['kariera', 'careers', 'praca', 'jobs'],
            'preferred_locations': ['footer'],
        },
        'find_terms': {
            'text_keywords': ['regulamin', 'terms', 'warunki', 'zasady'],
            'url_patterns': [r'/regulamin', r'/terms', r'/warunki', r'/zasady'],
            'aria_keywords': ['regulamin', 'terms'],
            'preferred_locations': ['footer'],
        },
        'find_privacy': {
            'text_keywords': ['prywatność', 'privacy', 'rodo', 'gdpr', 'dane osobowe'],
            'url_patterns': [r'/prywatnosc', r'/privacy', r'/rodo', r'/polityka'],
            'aria_keywords': ['privacy', 'prywatność'],
            'preferred_locations': ['footer'],
        },
        'find_warranty': {
            'text_keywords': ['gwarancja', 'warranty', 'serwis', 'naprawa'],
            'url_patterns': [r'/gwarancja', r'/warranty', r'/serwis'],
            'aria_keywords': ['gwarancja', 'warranty'],
            'preferred_locations': ['footer', 'nav'],
        },
        'find_account': {
            'text_keywords': ['moje konto', 'my account', 'profil', 'panel', 'zamówienia'],
            'url_patterns': [r'/konto', r'/account', r'/profil', r'/panel', r'/zamowienia'],
            'aria_keywords': ['konto', 'account', 'profil'],
            'preferred_locations': ['header', 'nav'],
        },
        'find_stores': {
            'text_keywords': ['sklepy', 'stores', 'lokalizacje', 'salony', 'punkty'],
            'url_patterns': [r'/sklepy', r'/stores', r'/lokalizacj', r'/salony'],
            'aria_keywords': ['sklepy', 'stores', 'lokalizacje'],
            'preferred_locations': ['footer', 'nav'],
        },
    }
    
    config = goal_config.get(goal, {
        'text_keywords': [goal.replace('find_', '').replace('_', ' ')],
        'url_patterns': [f"/{goal.replace('find_', '')}"],
        'aria_keywords': [goal.replace('find_', '')],
        'preferred_locations': ['nav', 'footer', 'header'],
    })
    
    candidates = []
    
    # Strategy 1: Text matching
    text_matches = await find_links_by_text(page, config['text_keywords'])
    for link in text_matches[:5]:
        link.score += 2.0
        candidates.append(link)
    
    # Strategy 2: URL pattern matching
    url_matches = await find_links_by_url_pattern(page, config['url_patterns'])
    for link in url_matches[:5]:
        link.score += 3.0  # URL patterns are strong signals
        candidates.append(link)
    
    # Strategy 3: Aria label matching
    aria_matches = await find_links_by_aria(page, config['aria_keywords'])
    for link in aria_matches[:3]:
        link.score += 1.5
        candidates.append(link)
    
    # Boost scores for preferred locations
    for link in candidates:
        if link.location in config['preferred_locations']:
            link.score += 1.0
    
    # Deduplicate by URL
    seen_urls = set()
    unique_candidates = []
    for link in sorted(candidates, key=lambda x: x.score, reverse=True):
        if link.url not in seen_urls:
            seen_urls.add(link.url)
            unique_candidates.append(link)
    
    if unique_candidates:
        best = unique_candidates[0]
        best.method = 'keyword_fallback'
        logger.info(f"Found link for {goal}: {best.url} (score: {best.score:.1f})")
        return best
    
    return None
