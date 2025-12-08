"""
DOM Helpers - Atomic, reusable DOM manipulation functions

These functions are designed to be:
1. Atomic - single responsibility
2. Composable - can be combined for complex operations
3. Resilient - multiple fallback strategies
4. LLM-friendly - can be used with or without LLM guidance
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


@dataclass
class LinkInfo:
    """Information about a found link"""
    url: str
    text: str
    aria_label: Optional[str]
    title: Optional[str]
    location: str  # header, footer, nav, main, sidebar
    context: str  # surrounding text
    score: float
    method: str  # how it was found


@dataclass 
class ElementInfo:
    """Information about a DOM element"""
    selector: str
    tag: str
    text: str
    attributes: Dict[str, str]
    visible: bool
    location: str


# =============================================================================
# ATOMIC LINK EXTRACTION FUNCTIONS
# =============================================================================

async def extract_all_links(page) -> List[LinkInfo]:
    """
    Extract all links from page with context information.
    
    This is the foundational function - other functions filter these results.
    """
    links = await page.evaluate("""
        () => {
            const getLocation = (el) => {
                let node = el;
                while (node && node !== document.body) {
                    const tag = node.tagName?.toLowerCase();
                    const role = node.getAttribute('role');
                    const cls = node.className?.toLowerCase() || '';
                    
                    if (tag === 'header' || role === 'banner' || cls.includes('header')) return 'header';
                    if (tag === 'footer' || role === 'contentinfo' || cls.includes('footer')) return 'footer';
                    if (tag === 'nav' || role === 'navigation' || cls.includes('nav')) return 'nav';
                    if (tag === 'aside' || cls.includes('sidebar')) return 'sidebar';
                    if (tag === 'main' || role === 'main') return 'main';
                    
                    node = node.parentElement;
                }
                return 'main';
            };
            
            const getContext = (el, maxLen = 100) => {
                const parent = el.closest('li, div, p, section, article') || el.parentElement;
                if (!parent) return '';
                return parent.innerText?.slice(0, maxLen).replace(/\\s+/g, ' ').trim() || '';
            };
            
            return Array.from(document.querySelectorAll('a[href]'))
                .filter(a => a.offsetParent !== null)  // visible
                .map(a => ({
                    url: a.href,
                    text: a.innerText?.trim().slice(0, 100) || '',
                    ariaLabel: a.getAttribute('aria-label') || '',
                    title: a.title || '',
                    location: getLocation(a),
                    context: getContext(a),
                    tagName: a.tagName
                }))
                .filter(l => l.url && !l.url.startsWith('javascript:'));
        }
    """)
    
    return [
        LinkInfo(
            url=l['url'],
            text=l['text'],
            aria_label=l.get('ariaLabel'),
            title=l.get('title'),
            location=l['location'],
            context=l['context'],
            score=0.0,
            method='extract'
        )
        for l in links
    ]


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


async def find_links_by_location(
    page,
    locations: List[str]
) -> List[LinkInfo]:
    """
    Find links in specific page locations (header, footer, nav, etc).
    """
    all_links = await extract_all_links(page)
    return [l for l in all_links if l.location in locations]


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


# =============================================================================
# ATOMIC ELEMENT FINDING FUNCTIONS
# =============================================================================

async def find_elements_by_role(
    page,
    role: str,
    name_contains: Optional[str] = None
) -> List[ElementInfo]:
    """
    Find elements by ARIA role.
    """
    elements = await page.evaluate(f"""
        () => {{
            const els = document.querySelectorAll('[role="{role}"]');
            return Array.from(els).map(el => ({{
                selector: el.id ? '#' + el.id : el.tagName.toLowerCase(),
                tag: el.tagName.toLowerCase(),
                text: el.innerText?.slice(0, 100) || '',
                attributes: Object.fromEntries(
                    Array.from(el.attributes).map(a => [a.name, a.value])
                ),
                visible: el.offsetParent !== null
            }}));
        }}
    """)
    
    results = [
        ElementInfo(
            selector=e['selector'],
            tag=e['tag'],
            text=e['text'],
            attributes=e['attributes'],
            visible=e['visible'],
            location='unknown'
        )
        for e in elements
    ]
    
    if name_contains:
        results = [e for e in results if name_contains.lower() in e.text.lower()]
    
    return results


async def find_buttons(
    page,
    text_contains: Optional[str] = None
) -> List[ElementInfo]:
    """
    Find all button elements.
    """
    elements = await page.evaluate("""
        () => {
            const buttons = document.querySelectorAll(
                'button, input[type="submit"], input[type="button"], [role="button"]'
            );
            return Array.from(buttons)
                .filter(el => el.offsetParent !== null)
                .map(el => ({
                    selector: el.id ? '#' + el.id : 
                              el.className ? '.' + el.className.split(' ')[0] :
                              el.tagName.toLowerCase(),
                    tag: el.tagName.toLowerCase(),
                    text: el.innerText?.trim() || el.value || '',
                    attributes: Object.fromEntries(
                        Array.from(el.attributes).map(a => [a.name, a.value])
                    ),
                    visible: true
                }));
        }
    """)
    
    results = [
        ElementInfo(
            selector=e['selector'],
            tag=e['tag'],
            text=e['text'],
            attributes=e['attributes'],
            visible=e['visible'],
            location='unknown'
        )
        for e in elements
    ]
    
    if text_contains:
        results = [e for e in results if text_contains.lower() in e.text.lower()]
    
    return results


async def find_inputs(
    page,
    input_type: Optional[str] = None,
    purpose: Optional[str] = None
) -> List[ElementInfo]:
    """
    Find input elements, optionally filtered by type or purpose.
    
    Purpose detection uses name, id, placeholder, aria-label.
    """
    elements = await page.evaluate("""
        () => {
            const inputs = document.querySelectorAll('input, textarea, select');
            return Array.from(inputs)
                .filter(el => el.offsetParent !== null)
                .map(el => ({
                    selector: el.id ? '#' + el.id : 
                              el.name ? `[name="${el.name}"]` :
                              el.tagName.toLowerCase(),
                    tag: el.tagName.toLowerCase(),
                    text: el.placeholder || el.value || '',
                    type: el.type || 'text',
                    attributes: Object.fromEntries(
                        Array.from(el.attributes).map(a => [a.name, a.value])
                    ),
                    visible: true
                }));
        }
    """)
    
    results = [
        ElementInfo(
            selector=e['selector'],
            tag=e['tag'],
            text=e['text'],
            attributes=e['attributes'],
            visible=e['visible'],
            location='unknown'
        )
        for e in elements
    ]
    
    if input_type:
        results = [e for e in results if e.attributes.get('type') == input_type]
    
    if purpose:
        purpose_lower = purpose.lower()
        purpose_keywords = {
            'email': ['email', 'mail', 'e-mail'],
            'password': ['password', 'haslo', 'hasło'],
            'name': ['name', 'imie', 'imię', 'nazwisko'],
            'phone': ['phone', 'tel', 'telefon', 'mobile'],
            'search': ['search', 'szukaj', 'query', 'q'],
            'message': ['message', 'wiadomosc', 'wiadomość', 'text', 'comment'],
        }
        
        keywords = purpose_keywords.get(purpose_lower, [purpose_lower])
        
        filtered = []
        for e in results:
            attrs_text = ' '.join([
                e.attributes.get('id', ''),
                e.attributes.get('name', ''),
                e.attributes.get('placeholder', ''),
                e.attributes.get('aria-label', ''),
                e.text
            ]).lower()
            
            if any(kw in attrs_text for kw in keywords):
                filtered.append(e)
        
        results = filtered
    
    return results


# =============================================================================
# COMPOSITE LINK FINDING FUNCTIONS
# =============================================================================

async def find_link_for_goal(
    page,
    goal: str,
    base_url: Optional[str] = None
) -> Optional[LinkInfo]:
    """
    Find best link for a specific goal using multiple strategies.
    
    Combines text matching, URL patterns, aria labels, and location hints.
    """
    # Goal-specific configurations
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
        logger.info(f"Found link for {goal}: {best.url} (score: {best.score:.1f})")
        return best
    
    return None


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


# =============================================================================
# SEARCH FUNCTIONS
# =============================================================================

async def find_search_input(page) -> Optional[ElementInfo]:
    """
    Find the main search input on the page.
    """
    inputs = await find_inputs(page, purpose='search')
    if inputs:
        return inputs[0]
    
    # Fallback: look for common search selectors
    fallback_selectors = [
        'input[type="search"]',
        'input[name="q"]',
        'input[name="query"]',
        'input[name="search"]',
        'input[placeholder*="szukaj"]',
        'input[placeholder*="search"]',
        '#search',
        '.search-input',
        '[role="search"] input',
    ]
    
    for selector in fallback_selectors:
        try:
            el = await page.query_selector(selector)
            if el and await el.is_visible():
                return ElementInfo(
                    selector=selector,
                    tag='input',
                    text='',
                    attributes={},
                    visible=True,
                    location='header'
                )
        except Exception:
            continue
    
    return None


async def execute_search(
    page,
    query: str,
    wait_ms: int = 2000
) -> bool:
    """
    Execute a search on the current page.
    
    Returns True if search was executed successfully.
    """
    search_input = await find_search_input(page)
    
    if search_input:
        try:
            el = await page.query_selector(search_input.selector)
            if el:
                await el.click()
                await el.fill('')
                await el.type(query, delay=50)
                await page.keyboard.press('Enter')
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                return True
        except Exception as e:
            logger.debug(f"Search execution failed: {e}")
    
    return False


# =============================================================================
# PAGE ANALYSIS FUNCTIONS
# =============================================================================

async def analyze_page_type(page) -> Dict[str, Any]:
    """
    Analyze the current page to determine its type.
    """
    return await page.evaluate("""
        () => {
            const url = location.href.toLowerCase();
            const title = document.title.toLowerCase();
            const body = document.body.innerText.toLowerCase().slice(0, 5000);
            
            // Count various elements
            const products = document.querySelectorAll('[class*="product"], [class*="offer"], [class*="item"]').length;
            const forms = document.querySelectorAll('form').length;
            const inputs = document.querySelectorAll('input, textarea').length;
            const prices = (body.match(/\\d+[,.]\\d{2}\\s*(zł|pln|eur|usd|€|\\$)/gi) || []).length;
            
            // Determine page type
            let pageType = 'other';
            let confidence = 0.3;
            
            if (url.includes('/koszyk') || url.includes('/cart')) {
                pageType = 'cart';
                confidence = 0.9;
            } else if (url.includes('/login') || url.includes('/logowanie')) {
                pageType = 'login';
                confidence = 0.9;
            } else if (url.includes('/kontakt') || url.includes('/contact')) {
                pageType = 'contact';
                confidence = 0.9;
            } else if (products > 10 || prices > 5) {
                pageType = 'product_listing';
                confidence = Math.min(0.9, 0.5 + products * 0.02);
            } else if (url.includes('/search') || url.includes('/szukaj') || url.includes('q=')) {
                pageType = 'search_results';
                confidence = 0.8;
            } else if (forms > 0 && inputs > 3) {
                pageType = 'form';
                confidence = 0.7;
            } else if (url === location.origin + '/' || url === location.origin) {
                pageType = 'home';
                confidence = 0.9;
            }
            
            return {
                type: pageType,
                confidence: confidence,
                url: location.href,
                title: document.title,
                stats: {
                    products: products,
                    forms: forms,
                    inputs: inputs,
                    prices: prices
                }
            };
        }
    """)


async def has_content_type(page, content_type: str) -> bool:
    """
    Check if page contains specific type of content.
    """
    analysis = await analyze_page_type(page)
    return analysis['type'] == content_type
