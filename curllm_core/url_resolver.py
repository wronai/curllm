"""
URL Resolver - Smart URL validation and navigation

This component validates URLs against user intent and automatically
navigates to the correct page when:
- The provided URL doesn't contain the expected content
- User lands on a general page but needs a specific category
- Products/data need to be found via search or category navigation

Strategies:
1. Page Content Analysis - Check if current page matches intent
2. Search Navigation - Use site search to find relevant content
3. Category Navigation - Find and navigate to relevant category
4. Sitemap Analysis - Parse sitemap for relevant URLs
"""

import re
import json
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, quote_plus

logger = logging.getLogger(__name__)


class TaskGoal(Enum):
    """What the user wants to achieve"""
    # Shopping
    EXTRACT_PRODUCTS = "extract_products"
    FIND_CART = "find_cart"
    FIND_CHECKOUT = "find_checkout"
    FIND_WISHLIST = "find_wishlist"
    TRACK_ORDER = "track_order"
    
    # Account
    FIND_LOGIN = "find_login"
    FIND_REGISTER = "find_register"
    FIND_ACCOUNT = "find_account"
    
    # Communication
    FIND_CONTACT_FORM = "find_contact_form"
    FIND_NEWSLETTER = "find_newsletter"
    FIND_CHAT = "find_chat"
    
    # Information
    FIND_FAQ = "find_faq"
    FIND_HELP = "find_help"
    FIND_ABOUT = "find_about"
    FIND_SHIPPING = "find_shipping"
    FIND_RETURNS = "find_returns"
    FIND_WARRANTY = "find_warranty"
    FIND_PRICING = "find_pricing"
    FIND_TERMS = "find_terms"
    FIND_PRIVACY = "find_privacy"
    
    # Content
    FIND_BLOG = "find_blog"
    FIND_NEWS = "find_news"
    FIND_DOWNLOADS = "find_downloads"
    FIND_RESOURCES = "find_resources"
    
    # Other
    FIND_CAREERS = "find_careers"
    FIND_STORES = "find_stores"
    FIND_SOCIAL = "find_social"
    FIND_COMPARE = "find_compare"
    
    GENERIC = "generic"


@dataclass
class PageMatchResult:
    """Result of page content analysis"""
    matches_intent: bool
    confidence: float
    found_items: int = 0
    page_type: str = "unknown"  # category, product, search_results, home, cart, contact, login, other
    search_available: bool = False
    search_selector: Optional[str] = None
    categories_found: List[Dict[str, str]] = field(default_factory=list)
    suggested_search_term: Optional[str] = None
    reasoning: str = ""
    # New fields for forms and cart
    has_cart: bool = False
    has_contact_form: bool = False
    has_login_form: bool = False
    cart_url: Optional[str] = None
    contact_url: Optional[str] = None
    checkout_url: Optional[str] = None


@dataclass
class ResolvedUrl:
    """Result of URL resolution"""
    original_url: str
    resolved_url: str
    resolution_method: str  # none, search, category, sitemap, direct
    success: bool
    steps_taken: List[str] = field(default_factory=list)
    page_match: Optional[PageMatchResult] = None


class UrlResolver:
    """
    Smart URL resolver that validates and corrects URLs based on user intent.
    
    Usage:
        resolver = UrlResolver(page, llm, run_logger)
        result = await resolver.resolve(url, user_instruction)
        
        if result.success:
            # Use result.resolved_url for extraction
    """
    
    # Common search input selectors
    SEARCH_SELECTORS = [
        'input[type="search"]',
        'input[name="q"]',
        'input[name="search"]',
        'input[name="query"]',
        'input[name="s"]',
        'input[placeholder*="szukaj" i]',
        'input[placeholder*="search" i]',
        'input[placeholder*="wyszukaj" i]',
        '#search',
        '#searchbox',
        '.search-input',
        '.search-field',
        '[data-testid="search-input"]',
    ]
    
    # Common search button/submit selectors
    SEARCH_SUBMIT_SELECTORS = [
        'button[type="submit"]',
        'input[type="submit"]',
        '.search-button',
        '.search-submit',
        '[data-testid="search-button"]',
        'button[aria-label*="search" i]',
        'button[aria-label*="szukaj" i]',
    ]
    
    # Category link patterns
    CATEGORY_PATTERNS = [
        r'/kategori[ae]/[\w-]+',
        r'/category/[\w-]+',
        r'/cat/[\w-]+',
        r'/c/[\w-]+',
        r'/products?/[\w-]+',
        r'/produkty?/[\w-]+',
    ]
    
    # Cart/checkout URL patterns
    CART_URL_PATTERNS = [
        r'/cart', r'/koszyk', r'/basket', r'/bag', r'/shopping-cart',
        r'/checkout', r'/zamowienie', r'/order', r'/kasa',
    ]
    
    # Contact page URL patterns  
    CONTACT_URL_PATTERNS = [
        r'/contact', r'/kontakt', r'/contact-us', r'/napisz-do-nas',
        r'/support', r'/help', r'/pomoc', r'/wsparcie',
    ]
    
    # Login page URL patterns
    LOGIN_URL_PATTERNS = [
        r'/login', r'/logowanie', r'/sign-in', r'/signin', r'/zaloguj',
        r'/account', r'/konto', r'/my-account', r'/moje-konto',
    ]
    
    # Goal detection keywords
    GOAL_KEYWORDS = {
        # Shopping
        TaskGoal.FIND_CART: [
            'koszyk', 'cart', 'basket', 'bag', 'dodaj do koszyka', 'add to cart',
            'zakup', 'buy', 'purchase', 'kup'
        ],
        TaskGoal.FIND_CHECKOUT: [
            'checkout', 'zamówienie', 'kasa', 'płatność', 'payment',
            'finalizuj', 'złóż zamówienie', 'place order', 'zapłać'
        ],
        TaskGoal.FIND_WISHLIST: [
            'wishlist', 'ulubione', 'favorites', 'schowek', 'zapisane',
            'lista życzeń', 'save for later', 'polubione'
        ],
        TaskGoal.TRACK_ORDER: [
            'śledzenie', 'tracking', 'status zamówienia', 'order status',
            'gdzie jest', 'where is my', 'track order', 'sprawdź zamówienie'
        ],
        
        # Account
        TaskGoal.FIND_LOGIN: [
            'zaloguj', 'login', 'sign in', 'logowanie'
        ],
        TaskGoal.FIND_REGISTER: [
            'zarejestruj', 'register', 'sign up', 'rejestracja', 'załóż konto',
            'create account', 'nowe konto'
        ],
        TaskGoal.FIND_ACCOUNT: [
            'moje konto', 'my account', 'profil', 'profile', 'ustawienia konta',
            'account settings', 'panel klienta'
        ],
        
        # Communication
        TaskGoal.FIND_CONTACT_FORM: [
            'kontakt', 'contact', 'napisz do nas', 'write to us',
            'formularz kontaktowy', 'contact form', 'zapytanie', 'inquiry'
        ],
        TaskGoal.FIND_NEWSLETTER: [
            'newsletter', 'zapisz się', 'subscribe', 'subskrypcja',
            'biuletyn', 'mailing', 'powiadomienia email'
        ],
        TaskGoal.FIND_CHAT: [
            'chat', 'czat', 'live chat', 'rozmowa', 'konsultant',
            'pomoc online', 'support chat'
        ],
        
        # Information
        TaskGoal.FIND_FAQ: [
            'faq', 'pytania', 'questions', 'często zadawane',
            'frequently asked', 'q&a', 'odpowiedzi'
        ],
        TaskGoal.FIND_HELP: [
            'pomoc', 'help', 'support', 'wsparcie', 'centrum pomocy',
            'help center', 'jak', 'how to'
        ],
        TaskGoal.FIND_ABOUT: [
            'o nas', 'about', 'about us', 'kim jesteśmy', 'who we are',
            'nasza historia', 'our story', 'o firmie'
        ],
        TaskGoal.FIND_SHIPPING: [
            'dostawa', 'shipping', 'delivery', 'wysyłka', 'czas dostawy',
            'koszty dostawy', 'shipping cost', 'metody dostawy'
        ],
        TaskGoal.FIND_RETURNS: [
            'zwrot', 'return', 'returns', 'zwroty', 'reklamacja',
            'wymiana', 'exchange', 'polityka zwrotów', 'return policy'
        ],
        TaskGoal.FIND_WARRANTY: [
            'gwarancja', 'warranty', 'guarantee', 'rękojmia',
            'warunki gwarancji', 'warranty terms', 'serwis'
        ],
        TaskGoal.FIND_PRICING: [
            'cennik', 'pricing', 'prices', 'ceny', 'plany', 'plans',
            'pakiety', 'packages', 'subscription', 'subskrypcja'
        ],
        TaskGoal.FIND_TERMS: [
            'regulamin', 'terms', 'terms of service', 'warunki',
            'terms and conditions', 'zasady', 'rules'
        ],
        TaskGoal.FIND_PRIVACY: [
            'prywatność', 'privacy', 'privacy policy', 'polityka prywatności',
            'rodo', 'gdpr', 'dane osobowe', 'cookies'
        ],
        
        # Content
        TaskGoal.FIND_BLOG: [
            'blog', 'artykuły', 'articles', 'wpisy', 'posts',
            'poradnik', 'guide', 'tips'
        ],
        TaskGoal.FIND_NEWS: [
            'aktualności', 'news', 'nowości', 'what\'s new',
            'ogłoszenia', 'announcements', 'wydarzenia'
        ],
        TaskGoal.FIND_DOWNLOADS: [
            'pobierz', 'download', 'downloads', 'pliki', 'files',
            'dokumenty', 'documents', 'materiały', 'resources'
        ],
        TaskGoal.FIND_RESOURCES: [
            'zasoby', 'resources', 'materiały', 'dokumentacja',
            'documentation', 'instrukcja', 'manual', 'tutorial'
        ],
        
        # Other
        TaskGoal.FIND_CAREERS: [
            'kariera', 'careers', 'praca', 'jobs', 'oferty pracy',
            'job openings', 'rekrutacja', 'hiring', 'dołącz do nas'
        ],
        TaskGoal.FIND_STORES: [
            'sklepy', 'stores', 'lokalizacje', 'locations', 'znajdź sklep',
            'store locator', 'punkty sprzedaży', 'gdzie kupić', 'salony'
        ],
        TaskGoal.FIND_SOCIAL: [
            'social', 'facebook', 'instagram', 'twitter', 'linkedin',
            'youtube', 'tiktok', 'społeczność', 'obserwuj nas', 'follow us'
        ],
        TaskGoal.FIND_COMPARE: [
            'porównaj', 'compare', 'porównanie', 'comparison',
            'zestawienie', 'versus', 'vs', 'różnice'
        ],
    }
    
    def __init__(self, page=None, llm=None, run_logger=None):
        """
        Initialize URL resolver.
        
        Args:
            page: Playwright page object
            llm: LLM client for intelligent analysis
            run_logger: Logger for documentation
        """
        self.page = page
        self.llm = llm
        self.run_logger = run_logger
    
    def detect_goal(self, instruction: str) -> TaskGoal:
        """Detect user's goal from instruction"""
        instr_lower = instruction.lower()
        
        scores = {}
        for goal, keywords in self.GOAL_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in instr_lower)
            if score > 0:
                scores[goal] = score
        
        if scores:
            best_goal = max(scores, key=scores.get)
            return best_goal
        
        return TaskGoal.GENERIC
    
    async def find_cart_url(self) -> Optional[str]:
        """Find cart/checkout URL on current page"""
        if not self.page:
            return None
        
        try:
            cart_url = await self.page.evaluate("""
                () => {
                    const patterns = [
                        'a[href*="cart"]', 'a[href*="koszyk"]', 'a[href*="basket"]',
                        'a[href*="checkout"]', 'a[href*="zamow"]',
                        '.cart-link', '.cart-icon', '#cart', '#mini-cart',
                        '[data-testid="cart"]', '[aria-label*="cart" i]',
                        '[aria-label*="koszyk" i]', '.icon-cart', '.shopping-cart'
                    ];
                    
                    for (const sel of patterns) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const href = el.getAttribute('href') || el.closest('a')?.getAttribute('href');
                            if (href) return href;
                        }
                    }
                    return null;
                }
            """)
            
            if cart_url:
                if cart_url.startswith('/'):
                    cart_url = urljoin(self.page.url, cart_url)
                return cart_url
                
        except Exception as e:
            logger.debug(f"Cart URL search failed: {e}")
        
        return None
    
    async def find_contact_url(self) -> Optional[str]:
        """Find contact page URL on current page"""
        if not self.page:
            return None
        
        try:
            contact_url = await self.page.evaluate("""
                () => {
                    const patterns = [
                        'a[href*="contact"]', 'a[href*="kontakt"]',
                        'a[href*="napisz"]', 'a[href*="support"]',
                        'a[href*="help"]', 'a[href*="pomoc"]',
                        'footer a[href*="kontakt"]', 'nav a[href*="kontakt"]'
                    ];
                    
                    for (const sel of patterns) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const href = el.getAttribute('href');
                            if (href) return href;
                        }
                    }
                    
                    // Try by link text
                    const links = Array.from(document.querySelectorAll('a'));
                    const contactLink = links.find(a => {
                        const text = a.innerText.toLowerCase();
                        return text.includes('kontakt') || text.includes('contact') || 
                               text.includes('napisz') || text.includes('pomoc');
                    });
                    if (contactLink) return contactLink.getAttribute('href');
                    
                    return null;
                }
            """)
            
            if contact_url:
                if contact_url.startswith('/'):
                    contact_url = urljoin(self.page.url, contact_url)
                return contact_url
                
        except Exception as e:
            logger.debug(f"Contact URL search failed: {e}")
        
        return None
    
    async def find_login_url(self) -> Optional[str]:
        """Find login page URL on current page"""
        return await self.find_generic_url([
            'a[href*="login"]', 'a[href*="logowanie"]', 'a[href*="signin"]',
            'a[href*="zaloguj"]', 'a[href*="account"]', 'a[href*="konto"]',
        ], ['zaloguj', 'login', 'moje konto', 'sign in', 'logowanie'])
    
    async def find_generic_url(
        self,
        href_patterns: List[str],
        text_keywords: List[str]
    ) -> Optional[str]:
        """
        Generic URL finder using href patterns and text keywords.
        
        Args:
            href_patterns: CSS selectors with href patterns
            text_keywords: Keywords to search in link text
        """
        if not self.page:
            return None
        
        try:
            # Convert to JSON-safe format
            patterns_json = json.dumps(href_patterns)
            keywords_json = json.dumps(text_keywords)
            
            found_url = await self.page.evaluate(f"""
                () => {{
                    const patterns = {patterns_json};
                    const keywords = {keywords_json};
                    
                    // Try href patterns first
                    for (const sel of patterns) {{
                        try {{
                            const el = document.querySelector(sel);
                            if (el) {{
                                const href = el.getAttribute('href') || el.closest('a')?.getAttribute('href');
                                if (href && !href.startsWith('javascript:') && !href.startsWith('#')) {{
                                    return href;
                                }}
                            }}
                        }} catch (e) {{}}
                    }}
                    
                    // Try by link text
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    for (const kw of keywords) {{
                        const found = links.find(a => {{
                            const text = (a.innerText || '').toLowerCase();
                            const href = (a.getAttribute('href') || '').toLowerCase();
                            return text.includes(kw.toLowerCase()) || href.includes(kw.toLowerCase());
                        }});
                        if (found) {{
                            const href = found.getAttribute('href');
                            if (href && !href.startsWith('javascript:') && !href.startsWith('#')) {{
                                return href;
                            }}
                        }}
                    }}
                    
                    return null;
                }}
            """)
            
            if found_url:
                if found_url.startswith('/'):
                    found_url = urljoin(self.page.url, found_url)
                return found_url
                
        except Exception as e:
            logger.debug(f"Generic URL search failed: {e}")
        
        return None
    
    async def find_url_for_goal(self, goal: TaskGoal) -> Optional[str]:
        """Find URL for any goal type"""
        
        # Define patterns and keywords for each goal
        goal_patterns = {
            TaskGoal.FIND_CART: {
                'patterns': ['a[href*="cart"]', 'a[href*="koszyk"]', 'a[href*="basket"]'],
                'keywords': ['koszyk', 'cart', 'basket']
            },
            TaskGoal.FIND_CHECKOUT: {
                'patterns': ['a[href*="checkout"]', 'a[href*="zamow"]', 'a[href*="kasa"]'],
                'keywords': ['checkout', 'zamówienie', 'kasa', 'finalizuj']
            },
            TaskGoal.FIND_WISHLIST: {
                'patterns': ['a[href*="wishlist"]', 'a[href*="ulubione"]', 'a[href*="favorites"]'],
                'keywords': ['wishlist', 'ulubione', 'schowek', 'favorites']
            },
            TaskGoal.TRACK_ORDER: {
                'patterns': ['a[href*="track"]', 'a[href*="order"]', 'a[href*="status"]'],
                'keywords': ['śledzenie', 'tracking', 'status', 'zamówienia']
            },
            TaskGoal.FIND_LOGIN: {
                'patterns': ['a[href*="login"]', 'a[href*="signin"]', 'a[href*="zaloguj"]'],
                'keywords': ['zaloguj', 'login', 'sign in']
            },
            TaskGoal.FIND_REGISTER: {
                'patterns': ['a[href*="register"]', 'a[href*="signup"]', 'a[href*="rejestr"]'],
                'keywords': ['zarejestruj', 'register', 'załóż konto', 'sign up']
            },
            TaskGoal.FIND_ACCOUNT: {
                'patterns': ['a[href*="account"]', 'a[href*="konto"]', 'a[href*="profile"]'],
                'keywords': ['moje konto', 'my account', 'profil']
            },
            TaskGoal.FIND_CONTACT_FORM: {
                'patterns': ['a[href*="contact"]', 'a[href*="kontakt"]'],
                'keywords': ['kontakt', 'contact', 'napisz do nas']
            },
            TaskGoal.FIND_NEWSLETTER: {
                'patterns': ['a[href*="newsletter"]', 'a[href*="subscribe"]'],
                'keywords': ['newsletter', 'zapisz się', 'subscribe']
            },
            TaskGoal.FIND_CHAT: {
                'patterns': ['a[href*="chat"]', '[class*="chat"]', '[id*="chat"]'],
                'keywords': ['chat', 'czat', 'live chat']
            },
            TaskGoal.FIND_FAQ: {
                'patterns': ['a[href*="faq"]', 'a[href*="pytania"]', 'a[href*="questions"]'],
                'keywords': ['faq', 'pytania', 'często zadawane']
            },
            TaskGoal.FIND_HELP: {
                'patterns': ['a[href*="help"]', 'a[href*="pomoc"]', 'a[href*="support"]'],
                'keywords': ['pomoc', 'help', 'wsparcie', 'support']
            },
            TaskGoal.FIND_ABOUT: {
                'patterns': ['a[href*="about"]', 'a[href*="o-nas"]', 'a[href*="firma"]'],
                'keywords': ['o nas', 'about', 'kim jesteśmy', 'o firmie']
            },
            TaskGoal.FIND_SHIPPING: {
                'patterns': ['a[href*="shipping"]', 'a[href*="dostawa"]', 'a[href*="delivery"]'],
                'keywords': ['dostawa', 'shipping', 'wysyłka', 'delivery']
            },
            TaskGoal.FIND_RETURNS: {
                'patterns': ['a[href*="return"]', 'a[href*="zwrot"]', 'a[href*="reklamac"]'],
                'keywords': ['zwroty', 'returns', 'reklamacja', 'wymiana']
            },
            TaskGoal.FIND_WARRANTY: {
                'patterns': ['a[href*="warranty"]', 'a[href*="gwarancja"]', 'a[href*="serwis"]'],
                'keywords': ['gwarancja', 'warranty', 'serwis']
            },
            TaskGoal.FIND_PRICING: {
                'patterns': ['a[href*="pricing"]', 'a[href*="cennik"]', 'a[href*="plans"]'],
                'keywords': ['cennik', 'pricing', 'plany', 'ceny']
            },
            TaskGoal.FIND_TERMS: {
                'patterns': ['a[href*="terms"]', 'a[href*="regulamin"]', 'a[href*="tos"]'],
                'keywords': ['regulamin', 'terms', 'warunki']
            },
            TaskGoal.FIND_PRIVACY: {
                'patterns': ['a[href*="privacy"]', 'a[href*="prywatno"]', 'a[href*="rodo"]'],
                'keywords': ['prywatność', 'privacy', 'rodo', 'gdpr']
            },
            TaskGoal.FIND_BLOG: {
                'patterns': ['a[href*="blog"]', 'a[href*="artykul"]', 'a[href*="articles"]'],
                'keywords': ['blog', 'artykuły', 'poradnik']
            },
            TaskGoal.FIND_NEWS: {
                'patterns': ['a[href*="news"]', 'a[href*="aktualnosci"]', 'a[href*="nowosci"]'],
                'keywords': ['aktualności', 'news', 'nowości']
            },
            TaskGoal.FIND_DOWNLOADS: {
                'patterns': ['a[href*="download"]', 'a[href*="pobierz"]', 'a[href*="files"]'],
                'keywords': ['pobierz', 'download', 'pliki']
            },
            TaskGoal.FIND_RESOURCES: {
                'patterns': ['a[href*="resources"]', 'a[href*="zasoby"]', 'a[href*="docs"]'],
                'keywords': ['zasoby', 'resources', 'dokumentacja']
            },
            TaskGoal.FIND_CAREERS: {
                'patterns': ['a[href*="career"]', 'a[href*="jobs"]', 'a[href*="praca"]'],
                'keywords': ['kariera', 'careers', 'praca', 'jobs']
            },
            TaskGoal.FIND_STORES: {
                'patterns': ['a[href*="stores"]', 'a[href*="locations"]', 'a[href*="sklepy"]'],
                'keywords': ['sklepy', 'stores', 'lokalizacje', 'znajdź sklep']
            },
            TaskGoal.FIND_SOCIAL: {
                'patterns': ['a[href*="facebook"]', 'a[href*="instagram"]', 'a[href*="twitter"]'],
                'keywords': ['facebook', 'instagram', 'twitter', 'social']
            },
            TaskGoal.FIND_COMPARE: {
                'patterns': ['a[href*="compare"]', 'a[href*="porownaj"]'],
                'keywords': ['porównaj', 'compare', 'porównanie']
            },
        }
        
        if goal not in goal_patterns:
            return None
        
        config = goal_patterns[goal]
        return await self.find_generic_url(config['patterns'], config['keywords'])
    
    async def resolve_for_goal(
        self,
        url: str,
        goal: TaskGoal
    ) -> ResolvedUrl:
        """
        Resolve URL for a specific goal (cart, contact, login, etc.)
        
        Works for all TaskGoal types - automatically finds the right page
        based on the goal using link patterns and text matching.
        """
        steps = []
        self._log(f"🎯 Resolving for goal: {goal.value}")
        
        if self.page:
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                steps.append(f"Navigated to {urlparse(url).hostname}")
            except Exception as e:
                return ResolvedUrl(
                    original_url=url,
                    resolved_url=url,
                    resolution_method="none",
                    success=False,
                    steps_taken=[f"Navigation failed: {e}"],
                )
        
        # Use the universal goal-based URL finder
        target_url = await self.find_url_for_goal(goal)
        steps.append(f"Searched for {goal.value}: {'found' if target_url else 'not found'}")
        
        if target_url:
            try:
                await self.page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                self._log(f"✅ Found {goal.value}: {target_url}")
                return ResolvedUrl(
                    original_url=url,
                    resolved_url=target_url,
                    resolution_method=goal.value,
                    success=True,
                    steps_taken=steps,
                )
            except Exception as e:
                steps.append(f"Navigation to target failed: {e}")
        
        return ResolvedUrl(
            original_url=url,
            resolved_url=url,
            resolution_method="none",
            success=False,
            steps_taken=steps,
        )
    
    async def resolve(
        self,
        url: str,
        instruction: str,
        max_attempts: int = 3
    ) -> ResolvedUrl:
        """
        Resolve URL to match user intent.
        
        Args:
            url: Original URL provided by user
            instruction: User's task instruction
            max_attempts: Maximum navigation attempts
            
        Returns:
            ResolvedUrl with resolution details
        """
        self._log(f"🔍 URL Resolver: Analyzing {url}")
        self._log(f"   Intent: {instruction[:100]}...")
        
        # Detect goal first
        goal = self.detect_goal(instruction)
        self._log(f"   Detected goal: {goal.value}")
        
        # For specific goals (anything except GENERIC and EXTRACT_PRODUCTS), 
        # use specialized resolution to find the right page
        if goal not in [TaskGoal.GENERIC, TaskGoal.EXTRACT_PRODUCTS]:
            return await self.resolve_for_goal(url, goal)
        
        steps = []
        current_url = url
        
        # Step 1: Navigate to original URL
        if self.page:
            try:
                await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
                current_url = self.page.url
                steps.append(f"Navigated to {urlparse(url).hostname}")
            except Exception as e:
                self._log(f"Navigation failed: {e}", "error")
                return ResolvedUrl(
                    original_url=url,
                    resolved_url=url,
                    resolution_method="none",
                    success=False,
                    steps_taken=[f"Navigation failed: {e}"],
                )
        
        # Step 2: Analyze if current page matches intent
        page_match = await self._analyze_page_match(instruction)
        steps.append(f"Page analysis: {page_match.page_type}, matches={page_match.matches_intent}")
        
        # If page matches intent, we're done
        if page_match.matches_intent and page_match.confidence >= 0.7:
            self._log(f"✅ Page matches intent (confidence: {page_match.confidence:.0%})")
            return ResolvedUrl(
                original_url=url,
                resolved_url=current_url,
                resolution_method="direct",
                success=True,
                steps_taken=steps,
                page_match=page_match,
            )
        
        # Step 3: Extract search term from instruction
        search_term = await self._extract_search_term(instruction)
        if search_term:
            steps.append(f"Extracted search term: {search_term}")
            self._log(f"🔎 Search term extracted: {search_term}")
        
        # Step 4: Try to find content via search
        if search_term and page_match.search_available:
            search_result = await self._try_search_navigation(search_term)
            if search_result:
                current_url = self.page.url
                steps.append(f"Searched for: {search_term}")
                
                # Re-analyze after search
                page_match = await self._analyze_page_match(instruction)
                if page_match.matches_intent and page_match.confidence >= 0.6:
                    self._log(f"✅ Found via search: {current_url}")
                    return ResolvedUrl(
                        original_url=url,
                        resolved_url=current_url,
                        resolution_method="search",
                        success=True,
                        steps_taken=steps,
                        page_match=page_match,
                    )
        
        # Step 5: Try category navigation
        if page_match.categories_found:
            category_result = await self._try_category_navigation(
                page_match.categories_found, search_term or instruction
            )
            if category_result:
                current_url = self.page.url
                steps.append(f"Navigated to category: {category_result}")
                
                # Re-analyze after category navigation
                page_match = await self._analyze_page_match(instruction)
                if page_match.matches_intent and page_match.confidence >= 0.5:
                    self._log(f"✅ Found via category: {current_url}")
                    return ResolvedUrl(
                        original_url=url,
                        resolved_url=current_url,
                        resolution_method="category",
                        success=True,
                        steps_taken=steps,
                        page_match=page_match,
                    )
        
        # Step 6: Try sitemap if available
        sitemap_result = await self._try_sitemap_navigation(url, search_term or instruction)
        if sitemap_result:
            current_url = sitemap_result
            steps.append(f"Found via sitemap: {sitemap_result}")
            
            if self.page:
                try:
                    await self.page.goto(sitemap_result, wait_until="domcontentloaded")
                    page_match = await self._analyze_page_match(instruction)
                    if page_match.matches_intent:
                        self._log(f"✅ Found via sitemap: {current_url}")
                        return ResolvedUrl(
                            original_url=url,
                            resolved_url=current_url,
                            resolution_method="sitemap",
                            success=True,
                            steps_taken=steps,
                            page_match=page_match,
                        )
                except Exception:
                    pass
        
        # Fallback: Return with partial success if we found anything relevant
        self._log(f"⚠️ Partial resolution: {current_url}")
        return ResolvedUrl(
            original_url=url,
            resolved_url=current_url,
            resolution_method="partial",
            success=page_match.found_items > 0,
            steps_taken=steps,
            page_match=page_match,
        )
    
    async def _analyze_page_match(self, instruction: str) -> PageMatchResult:
        """Analyze if current page content matches user intent"""
        
        if not self.page:
            return PageMatchResult(matches_intent=False, confidence=0, reasoning="No page available")
        
        try:
            # Get page info
            page_data = await self.page.evaluate("""
                () => {
                    const body = document.body;
                    const text = body ? body.innerText.slice(0, 10000) : '';
                    
                    // Count product-like elements
                    const productSelectors = [
                        '.product', '.offer', '.item', '[data-product]',
                        '.product-card', '.product-item', '.produkt'
                    ];
                    let productCount = 0;
                    productSelectors.forEach(sel => {
                        productCount += document.querySelectorAll(sel).length;
                    });
                    
                    // Find search input
                    const searchSelectors = [
                        'input[type="search"]', 'input[name="q"]', 'input[name="search"]',
                        'input[placeholder*="szukaj" i]', 'input[placeholder*="search" i]',
                        '#search', '.search-input'
                    ];
                    let searchInput = null;
                    for (const sel of searchSelectors) {
                        const el = document.querySelector(sel);
                        if (el && el.offsetParent !== null) {
                            searchInput = sel;
                            break;
                        }
                    }
                    
                    // Find category links
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    const categoryLinks = links
                        .filter(a => {
                            const href = a.getAttribute('href') || '';
                            const text = a.innerText.trim();
                            return (href.includes('/kategori') || href.includes('/category') ||
                                    href.includes('/c/') || href.includes('/products')) &&
                                   text.length > 0 && text.length < 50;
                        })
                        .slice(0, 20)
                        .map(a => ({
                            text: a.innerText.trim(),
                            href: a.getAttribute('href')
                        }));
                    
                    return {
                        title: document.title,
                        url: location.href,
                        textPreview: text.slice(0, 3000),
                        productCount: productCount,
                        searchSelector: searchInput,
                        categoryLinks: categoryLinks,
                        hasSearchForm: !!searchInput
                    };
                }
            """)
            
            # Analyze with keywords
            instr_lower = instruction.lower()
            text_lower = page_data.get('textPreview', '').lower()
            
            # Extract key terms from instruction
            key_terms = self._extract_keywords(instruction)
            
            # Count matching terms
            matches = sum(1 for term in key_terms if term.lower() in text_lower)
            match_ratio = matches / len(key_terms) if key_terms else 0
            
            product_count = page_data.get('productCount', 0)
            
            # Determine page type
            if product_count > 5:
                page_type = "category"
            elif product_count > 0:
                page_type = "product"
            elif "search" in page_data.get('url', '').lower() or "wynik" in text_lower:
                page_type = "search_results"
            elif page_data.get('url', '').rstrip('/').endswith(urlparse(page_data.get('url', '')).hostname):
                page_type = "home"
            else:
                page_type = "other"
            
            # Calculate confidence
            confidence = min(1.0, match_ratio * 0.5 + (0.3 if product_count > 0 else 0) + (0.2 if matches > 2 else 0))
            
            # Determine if it matches
            matches_intent = (
                (product_count > 0 and match_ratio >= 0.3) or
                (match_ratio >= 0.5) or
                (product_count > 10 and matches > 0)
            )
            
            return PageMatchResult(
                matches_intent=matches_intent,
                confidence=confidence,
                found_items=product_count,
                page_type=page_type,
                search_available=page_data.get('hasSearchForm', False),
                search_selector=page_data.get('searchSelector'),
                categories_found=page_data.get('categoryLinks', []),
                suggested_search_term=key_terms[0] if key_terms else None,
                reasoning=f"Found {product_count} products, {matches}/{len(key_terms)} keywords matched"
            )
            
        except Exception as e:
            logger.error(f"Page analysis failed: {e}")
            return PageMatchResult(
                matches_intent=False,
                confidence=0,
                reasoning=f"Analysis failed: {e}"
            )
    
    async def _extract_search_term(self, instruction: str) -> Optional[str]:
        """Extract the best search term from instruction"""
        
        # Try LLM extraction if available
        if self.llm:
            try:
                prompt = f"""Extract the main product/category search term from this instruction.
Return ONLY the search term (1-3 words), nothing else.

Instruction: {instruction}

Search term:"""
                response = await self.llm.ainvoke(prompt)
                term = response.content if hasattr(response, 'content') else str(response)
                term = term.strip().strip('"\'').strip()
                if term and len(term) < 50:
                    return term
            except Exception:
                pass
        
        # Fallback: Extract keywords
        keywords = self._extract_keywords(instruction)
        if keywords:
            return " ".join(keywords[:2])
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        
        # Common product/category terms
        product_patterns = [
            r'DDR[345]',
            r'RAM\s*\d+GB',
            r'\d+GB\s*RAM',
            r'SSD\s*\d+',
            r'procesor\w*',
            r'karta\s+graficzn\w*',
            r'monitor\s*\d+',
            r'laptop\w*',
            r'smartfon\w*',
            r'telefon\w*',
            r'tablet\w*',
            r'słuchawk\w*',
            r'telewizor\w*',
            r'pralk\w*',
            r'lodówk\w*',
        ]
        
        keywords = []
        text_lower = text.lower()
        
        # Find pattern matches
        for pattern in product_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)
        
        # Also extract capitalized words (likely product names)
        words = re.findall(r'\b[A-Z][a-zA-Z0-9]+\b', text)
        keywords.extend([w for w in words if len(w) > 2])
        
        # Extract quoted terms
        quoted = re.findall(r'"([^"]+)"', text)
        keywords.extend(quoted)
        
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                unique.append(kw)
        
        return unique[:5]
    
    async def _try_search_navigation(self, search_term: str) -> bool:
        """Try to use site search to find content"""
        
        if not self.page:
            return False
        
        try:
            # Find search input
            search_input = None
            for selector in self.SEARCH_SELECTORS:
                try:
                    el = await self.page.query_selector(selector)
                    if el and await el.is_visible():
                        search_input = el
                        break
                except Exception:
                    continue
            
            if not search_input:
                self._log("No search input found")
                return False
            
            # Clear and fill search
            await search_input.fill("")
            await search_input.fill(search_term)
            await self.page.wait_for_timeout(500)
            
            # Try to submit
            submitted = False
            
            # Try Enter key first
            try:
                await search_input.press("Enter")
                await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                submitted = True
            except Exception:
                pass
            
            # Try clicking search button if Enter didn't work
            if not submitted:
                for selector in self.SEARCH_SUBMIT_SELECTORS:
                    try:
                        btn = await self.page.query_selector(selector)
                        if btn and await btn.is_visible():
                            await btn.click()
                            await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                            submitted = True
                            break
                    except Exception:
                        continue
            
            if submitted:
                self._log(f"Search submitted: {search_term}")
                return True
            
            return False
            
        except Exception as e:
            self._log(f"Search navigation failed: {e}", "error")
            return False
    
    async def _try_category_navigation(
        self,
        categories: List[Dict[str, str]],
        search_term: str
    ) -> Optional[str]:
        """Try to navigate to a matching category"""
        
        if not self.page or not categories:
            return None
        
        search_lower = search_term.lower()
        keywords = self._extract_keywords(search_term)
        
        # Score categories by relevance
        scored = []
        for cat in categories:
            text = cat.get('text', '').lower()
            href = cat.get('href', '')
            
            score = 0
            for kw in keywords:
                if kw.lower() in text:
                    score += 2
                if kw.lower() in href.lower():
                    score += 1
            
            if score > 0:
                scored.append((score, cat))
        
        if not scored:
            return None
        
        # Sort by score and try best match
        scored.sort(key=lambda x: x[0], reverse=True)
        best_cat = scored[0][1]
        
        try:
            href = best_cat.get('href', '')
            if href.startswith('/'):
                href = urljoin(self.page.url, href)
            
            await self.page.goto(href, wait_until="domcontentloaded", timeout=15000)
            self._log(f"Navigated to category: {best_cat.get('text')}")
            return best_cat.get('text')
            
        except Exception as e:
            self._log(f"Category navigation failed: {e}", "error")
            return None
    
    async def _try_sitemap_navigation(
        self,
        base_url: str,
        search_term: str
    ) -> Optional[str]:
        """Try to find relevant URL in sitemap"""
        
        parsed = urlparse(base_url)
        sitemap_urls = [
            f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
            f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
        ]
        
        keywords = self._extract_keywords(search_term)
        
        for sitemap_url in sitemap_urls:
            try:
                # Fetch sitemap
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(sitemap_url)
                    if response.status_code != 200:
                        continue
                    
                    content = response.text
                    
                    # Extract URLs from sitemap
                    urls = re.findall(r'<loc>([^<]+)</loc>', content)
                    
                    # Score URLs by keyword match
                    for url in urls:
                        url_lower = url.lower()
                        for kw in keywords:
                            if kw.lower() in url_lower:
                                return url
                    
            except Exception as e:
                logger.debug(f"Sitemap fetch failed: {e}")
                continue
        
        return None
    
    def _log(self, message: str, level: str = "info"):
        """Log message"""
        if self.run_logger:
            if level == "error":
                self.run_logger.log_text(f"❌ {message}")
            elif level == "warning":
                self.run_logger.log_text(f"⚠️ {message}")
            else:
                self.run_logger.log_text(f"   {message}")
        logger.info(message)


async def resolve_url(
    url: str,
    instruction: str,
    page=None,
    llm=None,
    run_logger=None
) -> ResolvedUrl:
    """
    Convenience function for URL resolution.
    
    Args:
        url: URL to validate/resolve
        instruction: User's task instruction
        page: Playwright page (optional)
        llm: LLM client (optional)
        run_logger: Logger (optional)
        
    Returns:
        ResolvedUrl with resolution details
    """
    resolver = UrlResolver(page, llm, run_logger)
    return await resolver.resolve(url, instruction)
