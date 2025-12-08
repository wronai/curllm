"""
DOM Selectors - Centralized selector definitions for DOM operations

Instead of hardcoding selectors throughout the codebase, import them from here.
This allows for:
1. Easy maintenance and updates
2. Consistent selector patterns across modules
3. Fallback to LLMElementFinder when selectors fail

Usage:
    from curllm_core.dom_selectors import FORM_SELECTORS, ERROR_SELECTORS
    
    # Use with fallback to dynamic detection
    from curllm_core.dom_selectors import find_element_with_fallback
    element = await find_element_with_fallback(page, FORM_SELECTORS['email'])
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# FORM FIELD SELECTORS
# =============================================================================

FORM_SELECTORS = {
    # Email fields
    'email': [
        'input[type="email"]',
        'input[name*="email" i]',
        'input[name*="mail" i]',
        'input[placeholder*="email" i]',
        'input[placeholder*="e-mail" i]',
        'input[autocomplete="email"]',
        '#email', '#mail', '#e-mail',
    ],
    
    # Name fields
    'name': [
        'input[name*="name" i]',
        'input[name*="imie" i]',
        'input[name*="nazwisko" i]',
        'input[placeholder*="imię" i]',
        'input[placeholder*="name" i]',
        'input[autocomplete="name"]',
        '#name', '#imie', '#nazwisko',
    ],
    
    # Phone fields
    'phone': [
        'input[type="tel"]',
        'input[name*="phone" i]',
        'input[name*="telefon" i]',
        'input[name*="tel" i]',
        'input[placeholder*="telefon" i]',
        'input[placeholder*="phone" i]',
        'input[autocomplete="tel"]',
        '#phone', '#telefon', '#tel',
    ],
    
    # Message/textarea fields
    'message': [
        'textarea[name*="message" i]',
        'textarea[name*="wiadomosc" i]',
        'textarea[name*="tresc" i]',
        'textarea[name*="content" i]',
        'textarea[placeholder*="wiadomość" i]',
        'textarea[placeholder*="message" i]',
        'textarea',
        '#message', '#wiadomosc',
    ],
    
    # Subject fields
    'subject': [
        'input[name*="subject" i]',
        'input[name*="temat" i]',
        'input[placeholder*="temat" i]',
        'input[placeholder*="subject" i]',
        '#subject', '#temat',
    ],
    
    # Password fields
    'password': [
        'input[type="password"]',
        'input[name*="password" i]',
        'input[name*="haslo" i]',
        'input[autocomplete="current-password"]',
        'input[autocomplete="new-password"]',
    ],
    
    # Username fields
    'username': [
        'input[name*="username" i]',
        'input[name*="login" i]',
        'input[name*="user" i]',
        'input[autocomplete="username"]',
        '#username', '#login', '#user',
    ],
}


# =============================================================================
# BUTTON SELECTORS
# =============================================================================

BUTTON_SELECTORS = {
    'submit': [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:not([type])',  # Buttons without type default to submit
        '[role="button"]',
        '.submit-button', '.btn-submit', '.button-submit',
    ],
    
    'login': [
        'button[type="submit"]',
        'button:contains("Zaloguj")',
        'button:contains("Log in")',
        'button:contains("Sign in")',
        'input[type="submit"][value*="log" i]',
        'input[type="submit"][value*="zaloguj" i]',
    ],
    
    'register': [
        'button[type="submit"]',
        'button:contains("Zarejestruj")',
        'button:contains("Register")',
        'button:contains("Sign up")',
    ],
    
    'search': [
        'button[type="submit"]',
        'button[aria-label*="search" i]',
        'button[aria-label*="szukaj" i]',
        '.search-button', '.btn-search',
    ],
}


# =============================================================================
# ERROR/VALIDATION SELECTORS
# =============================================================================

ERROR_SELECTORS = {
    'validation_error': [
        '.error',
        '.invalid',
        '.forminator-error-message',
        '.wpcf7-not-valid-tip',
        '.elementor-field-required',
        '[aria-invalid="true"]',
        '.error-message',
        '.validation-error',
        '.field-error',
    ],
    
    'success_message': [
        '.wpcf7-mail-sent-ok',
        '.wpcf7-response-output',
        '.elementor-message-success',
        '.success-message',
        '.thank-you-message',
        '.form-success',
        '[role="alert"][class*="success"]',
    ],
    
    'captcha': [
        '.g-recaptcha',
        '.h-captcha',
        '.cf-turnstile',
        '[data-sitekey]',
        '[data-hcaptcha-sitekey]',
        'iframe[src*="recaptcha"]',
        'iframe[src*="hcaptcha"]',
    ],
}


# =============================================================================
# SEARCH SELECTORS
# =============================================================================

SEARCH_SELECTORS = {
    'input': [
        'input[type="search"]',
        'input[name="q"]',
        'input[name="s"]',
        'input[name="search"]',
        'input[name="query"]',
        'input[placeholder*="szukaj" i]',
        'input[placeholder*="search" i]',
        'input[aria-label*="szukaj" i]',
        'input[aria-label*="search" i]',
        '#search', '#q', '.search-input',
    ],
    
    'submit': [
        'button[type="submit"]',
        '.search-submit',
        '.search-button',
        'button[aria-label*="search" i]',
        'button[aria-label*="szukaj" i]',
    ],
}


# =============================================================================
# REQUIRED FIELD SELECTORS
# =============================================================================

REQUIRED_SELECTORS = [
    'input[required]',
    'textarea[required]',
    'select[required]',
    'input[aria-required="true"]',
    'textarea[aria-required="true"]',
    'select[aria-required="true"]',
]


# =============================================================================
# PRODUCT/ITEM SELECTORS
# =============================================================================

PRODUCT_SELECTORS = [
    '.product',
    '.offer',
    '.item',
    '[data-product]',
    '[data-product-id]',
    '.product-card',
    '.product-item',
    '.produkt',
    '.oferta',
    '[itemtype*="Product"]',
]


# =============================================================================
# NAVIGATION SELECTORS
# =============================================================================

NAV_SELECTORS = {
    'cart': [
        'a[href*="cart"]',
        'a[href*="koszyk"]',
        'a[href*="basket"]',
        '.cart-link', '.basket-link',
        '[aria-label*="koszyk" i]',
        '[aria-label*="cart" i]',
    ],
    
    'login': [
        'a[href*="login"]',
        'a[href*="logowanie"]',
        'a[href*="signin"]',
        'a[href*="konto"]',
        '[aria-label*="zaloguj" i]',
        '[aria-label*="login" i]',
    ],
    
    'contact': [
        'a[href*="kontakt"]',
        'a[href*="contact"]',
        'a[href*="support"]',
        'a[href*="pomoc"]',
        '[aria-label*="kontakt" i]',
        '[aria-label*="contact" i]',
    ],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_selectors_js(selector_list: List[str]) -> str:
    """
    Convert Python selector list to JavaScript array string.
    
    Usage:
        js_code = f"const selectors = {get_selectors_js(FORM_SELECTORS['email'])};"
    """
    escaped = [s.replace("'", "\\'").replace('"', '\\"') for s in selector_list]
    return "[" + ", ".join(f"'{s}'" for s in escaped) + "]"


def build_querySelector_chain(selector_list: List[str]) -> str:
    """
    Build a JavaScript querySelector chain that tries each selector.
    
    Returns JS code like:
        document.querySelector('input[type="email"]') || 
        document.querySelector('input[name*="email"]') || ...
    """
    parts = [f"document.querySelector('{s}')" for s in selector_list]
    return " || ".join(parts)


async def find_element_with_fallback(
    page,
    selectors: List[str],
    llm_finder=None,
    field_purpose: str = ""
) -> Optional[Any]:
    """
    Try to find element using selectors, fall back to LLM if available.
    
    Args:
        page: Playwright page
        selectors: List of CSS selectors to try
        llm_finder: Optional LLMElementFinder instance
        field_purpose: Description for LLM (e.g., "email input field")
    
    Returns:
        Found element or None
    """
    # Try each selector
    for selector in selectors:
        try:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                logger.debug(f"Found element with selector: {selector}")
                return element
        except Exception:
            continue
    
    # Fallback to LLM if available
    if llm_finder and field_purpose:
        try:
            match = await llm_finder.find_form_field(field_purpose)
            if match and match.selector:
                element = await page.query_selector(match.selector)
                if element:
                    logger.info(f"Found element via LLM: {match.selector}")
                    return element
        except Exception as e:
            logger.debug(f"LLM element finding failed: {e}")
    
    return None


def generate_find_element_js(
    selector_list: List[str],
    return_all: bool = False
) -> str:
    """
    Generate JavaScript code to find elements using selectors.
    
    Args:
        selector_list: List of selectors to try
        return_all: If True, use querySelectorAll; otherwise querySelector
    
    Returns:
        JavaScript code string
    """
    selectors_js = get_selectors_js(selector_list)
    
    if return_all:
        return f"""
            (() => {{
                const selectors = {selectors_js};
                const results = [];
                for (const sel of selectors) {{
                    try {{
                        const els = document.querySelectorAll(sel);
                        els.forEach(el => {{
                            if (el.offsetParent !== null) results.push(el);
                        }});
                    }} catch (e) {{}}
                }}
                return results;
            }})()
        """
    else:
        return f"""
            (() => {{
                const selectors = {selectors_js};
                for (const sel of selectors) {{
                    try {{
                        const el = document.querySelector(sel);
                        if (el && el.offsetParent !== null) return el;
                    }} catch (e) {{}}
                }}
                return null;
            }})()
        """
