"""
URL Patterns - DEPRECATED

⚠️ DEPRECATED: This module contains hardcoded selectors and patterns.
Use LLM-DSL approach instead:
- dom_helpers.find_search_input(page, llm=llm) - semantic search input finding
- dom_helpers.find_link_for_goal(page, goal, llm=llm) - LLM-driven link finding
- goal_detector_hybrid.detect_goal() - statistical goal detection

These patterns are kept for backward compatibility only.
Will be removed in future versions.
"""

from .url_types import TaskGoal


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
        'zaloguj', 'login', 'sign in', 'logowanie', 'moje konto',
        'my account', 'konto', 'zalogować'
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
        'formularz kontaktowy', 'contact form', 'zapytanie', 'inquiry',
        'wiadomość', 'message', 'obsługa klienta', 'customer service',
        'dział obsługi', 'support', 'skontaktuj'
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

# Goal patterns for URL matching (used in find_url_for_goal)
GOAL_URL_PATTERNS = {
    TaskGoal.FIND_CONTACT_FORM: {
        'patterns': ['a[href*="contact"]', 'a[href*="kontakt"]', 'a[href*="form"]'],
        'keywords': ['kontakt', 'contact', 'formularz', 'napisz']
    },
    TaskGoal.FIND_CART: {
        'patterns': ['a[href*="cart"]', 'a[href*="koszyk"]', 'a[href*="basket"]'],
        'keywords': ['koszyk', 'cart', 'basket']
    },
    TaskGoal.FIND_CHECKOUT: {
        'patterns': ['a[href*="checkout"]', 'a[href*="zamow"]', 'a[href*="kasa"]'],
        'keywords': ['zamówienie', 'checkout', 'kasa', 'finalizuj']
    },
    TaskGoal.FIND_LOGIN: {
        'patterns': ['a[href*="login"]', 'a[href*="logowanie"]', 'a[href*="signin"]'],
        'keywords': ['zaloguj', 'login', 'logowanie']
    },
    TaskGoal.FIND_REGISTER: {
        'patterns': ['a[href*="register"]', 'a[href*="rejestr"]', 'a[href*="signup"]'],
        'keywords': ['zarejestruj', 'register', 'rejestracja', 'załóż konto']
    },
    TaskGoal.FIND_FAQ: {
        'patterns': ['a[href*="faq"]', 'a[href*="pytania"]', 'a[href*="help"]'],
        'keywords': ['faq', 'pytania', 'pomoc']
    },
    TaskGoal.FIND_SHIPPING: {
        'patterns': ['a[href*="shipping"]', 'a[href*="dostawa"]', 'a[href*="delivery"]'],
        'keywords': ['dostawa', 'shipping', 'wysyłka']
    },
    TaskGoal.FIND_RETURNS: {
        'patterns': ['a[href*="return"]', 'a[href*="zwrot"]', 'a[href*="reklamacja"]'],
        'keywords': ['zwrot', 'return', 'reklamacja']
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
        'patterns': ['a[href*="terms"]', 'a[href*="regulamin"]', 'a[href*="warunki"]'],
        'keywords': ['regulamin', 'terms', 'warunki']
    },
    TaskGoal.FIND_PRIVACY: {
        'patterns': ['a[href*="privacy"]', 'a[href*="prywatnosc"]', 'a[href*="rodo"]'],
        'keywords': ['prywatność', 'privacy', 'rodo']
    },
    TaskGoal.FIND_ABOUT: {
        'patterns': ['a[href*="about"]', 'a[href*="o-nas"]', 'a[href*="firma"]'],
        'keywords': ['o nas', 'about', 'about us']
    },
    TaskGoal.FIND_BLOG: {
        'patterns': ['a[href*="blog"]', 'a[href*="artykuly"]', 'a[href*="news"]'],
        'keywords': ['blog', 'artykuły', 'news']
    },
    TaskGoal.FIND_CAREERS: {
        'patterns': ['a[href*="career"]', 'a[href*="kariera"]', 'a[href*="praca"]'],
        'keywords': ['kariera', 'praca', 'jobs']
    },
}


def detect_goal_from_instruction(instruction: str) -> TaskGoal:
    """
    Detect the user's goal from instruction text.
    
    Args:
        instruction: User's instruction text
        
    Returns:
        TaskGoal enum value
    """
    lower = instruction.lower()
    best_goal = TaskGoal.GENERIC
    best_score = 0
    
    for goal, keywords in GOAL_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lower)
        if score > best_score:
            best_score = score
            best_goal = goal
    
    return best_goal
