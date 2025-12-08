"""
Dynamic URL Discovery - Find URLs without hardcoding

Uses sitemap, DOM analysis, and LLM to discover URLs dynamically.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredUrl:
    """A dynamically discovered URL"""
    url: str
    purpose: str  # login, contact, cart, etc.
    confidence: float
    source: str  # sitemap, dom, llm


async def find_url_for_intent(
    page,
    intent: str,
    llm=None,
    use_sitemap: bool = True
) -> Optional[DiscoveredUrl]:
    """
    Find URL matching user intent without hardcoding.
    
    Instead of hardcoded URLs like 'https://example.com/login',
    dynamically discovers the correct URL.
    
    Args:
        page: Playwright page (for current domain context)
        intent: What the URL is for (e.g., "login page", "contact form")
        llm: Optional LLM for intelligent URL matching
        use_sitemap: Whether to check sitemap
        
    Returns:
        Discovered URL or None
    """
    base_url = page.url if page else None
    
    # 1. Try sitemap first (most reliable)
    if use_sitemap and base_url:
        sitemap_urls = await discover_sitemap_urls(page)
        matched = _match_url_to_intent(sitemap_urls, intent)
        if matched:
            return DiscoveredUrl(
                url=matched,
                purpose=intent,
                confidence=0.9,
                source='sitemap',
            )
    
    # 2. Try DOM link analysis
    if page:
        from curllm_core.dom import find_link_for_goal, LinkInfo
        from curllm_core.url_types import TaskGoal
        
        # Map intent to goal
        goal_mapping = {
            'login': TaskGoal.FIND_LOGIN,
            'contact': TaskGoal.FIND_CONTACT_FORM,
            'cart': TaskGoal.FIND_CART,
            'register': TaskGoal.FIND_LOGIN,
            'signup': TaskGoal.FIND_LOGIN,
        }
        
        goal = None
        for key, value in goal_mapping.items():
            if key in intent.lower():
                goal = value
                break
        
        if goal:
            link = await find_link_for_goal(page, goal.value, base_url=base_url)
            if link:
                return DiscoveredUrl(
                    url=link.url,
                    purpose=intent,
                    confidence=link.score / 100,
                    source='dom',
                )
    
    # 3. Try LLM-based URL discovery
    if llm and page:
        from curllm_core.url_resolution import UrlResolver
        
        resolver = UrlResolver(page=page, llm=llm)
        result = await resolver.resolve_for_goal(TaskGoal.BROWSE, intent)
        if result and result.success:
            return DiscoveredUrl(
                url=result.url,
                purpose=intent,
                confidence=result.confidence,
                source='llm',
            )
    
    return None


async def find_login_url(page, llm=None) -> Optional[str]:
    """Find login URL dynamically"""
    result = await find_url_for_intent(page, "login page", llm=llm)
    return result.url if result else None


async def find_contact_url(page, llm=None) -> Optional[str]:
    """Find contact page URL dynamically"""
    result = await find_url_for_intent(page, "contact form page", llm=llm)
    return result.url if result else None


async def find_cart_url(page, llm=None) -> Optional[str]:
    """Find shopping cart URL dynamically"""
    result = await find_url_for_intent(page, "shopping cart", llm=llm)
    return result.url if result else None


async def discover_sitemap_urls(page, max_urls: int = 100) -> List[str]:
    """
    Discover URLs from sitemap.
    
    Args:
        page: Playwright page
        max_urls: Maximum URLs to return
        
    Returns:
        List of discovered URLs
    """
    urls = []
    base_url = page.url
    parsed = urlparse(base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    
    # Try common sitemap locations
    sitemap_paths = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap/',
        '/robots.txt',  # Often contains sitemap reference
    ]
    
    for path in sitemap_paths:
        try:
            sitemap_url = urljoin(domain, path)
            response = await page.context.request.get(sitemap_url, timeout=5000)
            
            if response.ok:
                content = await response.text()
                
                if path.endswith('.txt'):
                    # Parse robots.txt for sitemap
                    for line in content.split('\n'):
                        if line.lower().startswith('sitemap:'):
                            sitemap = line.split(':', 1)[1].strip()
                            urls.append(sitemap)
                else:
                    # Parse XML sitemap
                    import re
                    locs = re.findall(r'<loc>([^<]+)</loc>', content)
                    urls.extend(locs[:max_urls])
                
                if urls:
                    break
        except Exception as e:
            logger.debug(f"Failed to fetch {path}: {e}")
    
    return urls[:max_urls]


def _match_url_to_intent(urls: List[str], intent: str) -> Optional[str]:
    """Match URL from list to user intent"""
    intent_lower = intent.lower()
    
    # Intent-to-URL-pattern mapping (semantic, not hardcoded URLs)
    patterns = {
        'login': ['login', 'signin', 'sign-in', 'logowanie', 'zaloguj'],
        'contact': ['contact', 'kontakt', 'support', 'help'],
        'cart': ['cart', 'basket', 'koszyk', 'checkout'],
        'register': ['register', 'signup', 'sign-up', 'rejestracja'],
        'account': ['account', 'profile', 'konto', 'profil'],
    }
    
    # Find matching patterns for intent
    matching_patterns = []
    for key, pats in patterns.items():
        if key in intent_lower:
            matching_patterns.extend(pats)
    
    if not matching_patterns:
        # Use intent words directly
        matching_patterns = intent_lower.split()
    
    # Score URLs
    best_url = None
    best_score = 0
    
    for url in urls:
        url_lower = url.lower()
        score = sum(1 for p in matching_patterns if p in url_lower)
        if score > best_score:
            best_score = score
            best_url = url
    
    return best_url if best_score > 0 else None
