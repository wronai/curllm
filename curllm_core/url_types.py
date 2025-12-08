"""
URL Types - Data structures for URL resolution

Contains:
- TaskGoal enum - what the user wants to achieve
- PageMatchResult - result of page content analysis
- ResolvedUrl - result of URL resolution

Extracted from url_resolver.py for better modularity.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class TaskGoal(Enum):
    """What the user wants to achieve"""
    # Shopping
    EXTRACT_PRODUCTS = "extract_products"
    FIND_PRODUCTS = "find_products"
    SEARCH_FOR_PRODUCTS = "search_for_products"
    NAVIGATE_TO_CATEGORY = "navigate_to_category"
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


# Backward compatibility exports
__all__ = ['TaskGoal', 'PageMatchResult', 'ResolvedUrl']
