"""
Intent Detector - Smart task classification using page context + instruction analysis

This module provides intelligent task classification by analyzing:
1. User instruction semantics
2. Page content and structure
3. Combined context to determine true intent

Key improvement: Analyze WHAT is on the page BEFORE deciding what to do.
This prevents false positives like treating product listing pages as form tasks.
"""

import re
import json
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


class TaskIntent(Enum):
    """User intent categories"""
    EXTRACT_PRODUCTS = "extract_products"      # Extract product data from listing/detail pages
    EXTRACT_ARTICLES = "extract_articles"      # Extract articles/news/blog posts
    EXTRACT_LINKS = "extract_links"            # Extract links from page
    EXTRACT_TABLE = "extract_table"            # Extract tabular data
    EXTRACT_GENERIC = "extract_generic"        # Generic data extraction
    
    FILL_CONTACT_FORM = "fill_contact_form"    # Fill contact/inquiry form
    FILL_LOGIN_FORM = "fill_login_form"        # Login to site
    FILL_REGISTER_FORM = "fill_register_form"  # Register new account
    FILL_SEARCH_FORM = "fill_search_form"      # Fill search form
    FILL_GENERIC = "fill_generic"              # Generic form filling
    
    NAVIGATE = "navigate"                       # Navigate to URL
    CLICK_ELEMENT = "click_element"            # Click specific element
    SCROLL_PAGE = "scroll_page"                # Scroll to load content
    
    COMPARE_DATA = "compare_data"              # Compare data across sources
    MONITOR_CHANGES = "monitor_changes"        # Monitor for changes
    
    UNKNOWN = "unknown"


@dataclass
class PageAnalysis:
    """Analysis of page structure"""
    has_product_listings: bool = False
    has_forms: bool = False
    has_login_form: bool = False
    has_contact_form: bool = False
    has_search_form: bool = False
    has_articles: bool = False
    has_tables: bool = False
    product_count: int = 0
    form_count: int = 0
    article_count: int = 0
    primary_content_type: str = "unknown"


@dataclass
class IntentResult:
    """Result of intent detection"""
    intent: TaskIntent
    confidence: float
    page_analysis: PageAnalysis
    instruction_analysis: Dict[str, Any]
    recommended_params: Dict[str, Any]
    reasoning: str


class IntentDetector:
    """
    Smart intent detection using both instruction AND page context.
    
    Key principle: The TRUE intent is determined by what the user WANTS
    combined with what the page OFFERS.
    """
    
    # Extraction intent keywords
    EXTRACTION_KEYWORDS = {
        'pl': [
            'wyciągnij', 'pobierz', 'znajdź', 'pokaż', 'lista', 'wylistuj',
            'zbierz', 'wyszukaj', 'jakie', 'ile', 'podaj', 'wymień',
            'produkty', 'artykuły', 'ceny', 'dane', 'informacje'
        ],
        'en': [
            'extract', 'get', 'find', 'show', 'list', 'collect', 
            'scrape', 'fetch', 'retrieve', 'search', 'what', 'how many',
            'products', 'articles', 'prices', 'data', 'information'
        ]
    }
    
    # Form filling keywords
    FORM_KEYWORDS = {
        'pl': [
            'wypełnij', 'wyślij', 'zaloguj', 'zarejestruj', 'napisz',
            'formularz', 'kontakt', 'logowanie', 'rejestracja'
        ],
        'en': [
            'fill', 'submit', 'login', 'register', 'write', 'send',
            'form', 'contact', 'sign in', 'sign up'
        ]
    }
    
    # Product page indicators
    PRODUCT_INDICATORS = [
        '.product', '.offer', '.item', '[data-product]', '.price',
        '.product-card', '.product-item', '.product-tile',
        '.cena', '.produkt', 'koszyk', 'add-to-cart'
    ]
    
    # Form indicators
    FORM_INDICATORS = [
        'form', 'input[type="text"]', 'input[type="email"]',
        'textarea', 'button[type="submit"]'
    ]
    
    # Contact form specific indicators
    CONTACT_FORM_INDICATORS = [
        'contact', 'kontakt', 'message', 'wiadomość', 'inquiry',
        'zapytanie', 'email', 'phone', 'telefon', 'name', 'imię'
    ]
    
    def __init__(self, llm=None):
        self.llm = llm
    
    async def detect_intent(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None
    ) -> IntentResult:
        """
        Detect user intent from instruction and page context.
        
        This is the main entry point. It:
        1. Analyzes the page structure first
        2. Analyzes the instruction semantics
        3. Combines both to determine true intent
        """
        # Step 1: Analyze page structure
        page_analysis = self._analyze_page(page_context, url)
        
        # Step 2: Analyze instruction
        instruction_analysis = self._analyze_instruction(instruction)
        
        # Step 3: Determine intent using both
        intent, confidence, reasoning = self._determine_intent(
            instruction_analysis, page_analysis
        )
        
        # Step 4: Generate recommended parameters
        recommended_params = self._get_recommended_params(intent, page_analysis)
        
        return IntentResult(
            intent=intent,
            confidence=confidence,
            page_analysis=page_analysis,
            instruction_analysis=instruction_analysis,
            recommended_params=recommended_params,
            reasoning=reasoning
        )
    
    def _analyze_page(
        self,
        page_context: Optional[Dict[str, Any]],
        url: Optional[str]
    ) -> PageAnalysis:
        """Analyze page structure to understand what's available"""
        
        analysis = PageAnalysis()
        
        if not page_context:
            return analysis
        
        # Get DOM HTML if available
        dom_html = page_context.get('dom_html', '') or page_context.get('dom', '') or ''
        dom_lower = dom_html.lower()
        
        # Get interactive elements
        interactives = page_context.get('interactives', []) or []
        forms = page_context.get('forms', []) or []
        
        # Analyze URL for hints
        url_lower = (url or '').lower()
        
        # Check for product listings
        product_indicators = [
            'product', 'produkt', 'offer', 'oferta', 'item', 'price', 'cena',
            'kategoria', 'category', 'sklep', 'shop', 'listing'
        ]
        has_product_url = any(ind in url_lower for ind in product_indicators)
        has_product_dom = any(ind in dom_lower for ind in self.PRODUCT_INDICATORS)
        
        if has_product_url or has_product_dom:
            analysis.has_product_listings = True
            # Estimate product count from DOM patterns
            analysis.product_count = max(
                dom_lower.count('class="product'),
                dom_lower.count('class="offer'),
                dom_lower.count('class="item'),
                dom_lower.count('data-product')
            )
        
        # Check for forms
        analysis.form_count = len(forms)
        if analysis.form_count > 0 or '<form' in dom_lower:
            analysis.has_forms = True
            
            # Classify form types
            for form in forms:
                form_html = str(form).lower()
                form_fields = form.get('fields', []) if isinstance(form, dict) else []
                
                # Login form detection
                if any(x in form_html for x in ['login', 'password', 'hasło', 'logowanie']):
                    analysis.has_login_form = True
                
                # Contact form detection
                if any(x in form_html for x in self.CONTACT_FORM_INDICATORS):
                    analysis.has_contact_form = True
                
                # Search form detection
                if any(x in form_html for x in ['search', 'szukaj', 'wyszukaj', 'q=']):
                    analysis.has_search_form = True
        
        # Check for articles
        article_indicators = ['article', 'post', 'blog', 'news', 'wpis', 'artykuł']
        if any(ind in dom_lower for ind in article_indicators):
            analysis.has_articles = True
            analysis.article_count = max(
                dom_lower.count('<article'),
                dom_lower.count('class="post'),
                dom_lower.count('class="article')
            )
        
        # Check for tables
        if '<table' in dom_lower:
            analysis.has_tables = True
        
        # Determine primary content type
        if analysis.has_product_listings and analysis.product_count > 1:
            analysis.primary_content_type = "product_listing"
        elif analysis.has_articles and analysis.article_count > 0:
            analysis.primary_content_type = "article_listing"
        elif analysis.has_contact_form:
            analysis.primary_content_type = "contact_page"
        elif analysis.has_login_form:
            analysis.primary_content_type = "login_page"
        elif analysis.has_tables:
            analysis.primary_content_type = "data_table"
        else:
            analysis.primary_content_type = "generic"
        
        return analysis
    
    def _analyze_instruction(self, instruction: str) -> Dict[str, Any]:
        """Analyze instruction to extract intent signals"""
        
        instr_lower = instruction.lower()
        
        # Check for extraction keywords
        extraction_score = 0
        for keywords in self.EXTRACTION_KEYWORDS.values():
            extraction_score += sum(1 for kw in keywords if kw in instr_lower)
        
        # Check for form keywords
        form_score = 0
        for keywords in self.FORM_KEYWORDS.values():
            form_score += sum(1 for kw in keywords if kw in instr_lower)
        
        # Check for specific patterns
        wants_list = any(x in instr_lower for x in ['list', 'lista', 'wszystkie', 'all'])
        wants_prices = any(x in instr_lower for x in ['price', 'cena', 'ceny', 'prices'])
        wants_products = any(x in instr_lower for x in ['product', 'produkt', 'products', 'produkty'])
        wants_compare = any(x in instr_lower for x in ['compare', 'porównaj', 'comparison', 'porównanie'])
        wants_send = any(x in instr_lower for x in ['send', 'wyślij', 'submit', 'napisz'])
        
        # Detect negative signals (things user explicitly doesn't want)
        no_click = any(x in instr_lower for x in ['nie klikaj', 'don\'t click', 'no click', 'bez klikania'])
        no_fill = any(x in instr_lower for x in ['nie wypełniaj', 'don\'t fill', 'no fill'])
        read_only = any(x in instr_lower for x in ['read only', 'tylko odczyt', 'tylko pobierz'])
        
        return {
            'extraction_score': extraction_score,
            'form_score': form_score,
            'wants_list': wants_list,
            'wants_prices': wants_prices,
            'wants_products': wants_products,
            'wants_compare': wants_compare,
            'wants_send': wants_send,
            'no_click': no_click,
            'no_fill': no_fill,
            'read_only': read_only,
            'primary_intent': 'extraction' if extraction_score > form_score else 'form' if form_score > extraction_score else 'unknown'
        }
    
    def _determine_intent(
        self,
        instruction_analysis: Dict[str, Any],
        page_analysis: PageAnalysis
    ) -> Tuple[TaskIntent, float, str]:
        """
        Determine true intent by combining instruction and page analysis.
        
        Key insight: User intent + Page content = True action needed
        """
        
        instr = instruction_analysis
        page = page_analysis
        
        # RULE 1: Explicit read-only/no-fill means extraction
        if instr['no_fill'] or instr['read_only']:
            if page.has_product_listings:
                return TaskIntent.EXTRACT_PRODUCTS, 0.95, "Read-only mode + product page = product extraction"
            elif page.has_articles:
                return TaskIntent.EXTRACT_ARTICLES, 0.95, "Read-only mode + articles = article extraction"
            else:
                return TaskIntent.EXTRACT_GENERIC, 0.9, "Read-only mode = generic extraction"
        
        # RULE 2: User wants list/products + product page = extraction
        if (instr['wants_list'] or instr['wants_products'] or instr['wants_prices']):
            if page.has_product_listings:
                return TaskIntent.EXTRACT_PRODUCTS, 0.9, "User wants products + product page detected"
            elif page.has_articles:
                return TaskIntent.EXTRACT_ARTICLES, 0.85, "User wants list + article page detected"
        
        # RULE 3: User wants to compare = extraction (even if forms present)
        if instr['wants_compare']:
            return TaskIntent.COMPARE_DATA, 0.9, "User wants comparison = data extraction first"
        
        # RULE 4: Product listing page + extraction keywords = product extraction
        if page.primary_content_type == "product_listing" and instr['extraction_score'] > 0:
            return TaskIntent.EXTRACT_PRODUCTS, 0.85, "Product listing page + extraction intent"
        
        # RULE 5: High extraction score + no form intent = extraction
        if instr['extraction_score'] > instr['form_score'] and instr['form_score'] == 0:
            if page.has_product_listings:
                return TaskIntent.EXTRACT_PRODUCTS, 0.8, "Extraction keywords + product page"
            elif page.has_articles:
                return TaskIntent.EXTRACT_ARTICLES, 0.8, "Extraction keywords + article page"
            elif page.has_tables:
                return TaskIntent.EXTRACT_TABLE, 0.75, "Extraction keywords + table detected"
            else:
                return TaskIntent.EXTRACT_GENERIC, 0.7, "Extraction keywords detected"
        
        # RULE 6: User wants to send + contact form = form filling
        if instr['wants_send'] and page.has_contact_form:
            return TaskIntent.FILL_CONTACT_FORM, 0.9, "User wants to send + contact form detected"
        
        # RULE 7: Login page + form keywords = login
        if page.has_login_form and instr['form_score'] > 0:
            return TaskIntent.FILL_LOGIN_FORM, 0.85, "Login form detected + form intent"
        
        # RULE 8: Contact page + form intent = contact form
        if page.primary_content_type == "contact_page" and instr['form_score'] > 0:
            return TaskIntent.FILL_CONTACT_FORM, 0.8, "Contact page + form intent"
        
        # RULE 9: Form keywords + forms present (but NOT product listings) = form
        if instr['form_score'] > instr['extraction_score'] and page.has_forms:
            if not page.has_product_listings:  # Don't fill forms on product pages!
                return TaskIntent.FILL_GENERIC, 0.7, "Form intent + forms present (no products)"
        
        # RULE 10: Product page without clear intent = probably extraction
        if page.has_product_listings and instr['extraction_score'] >= instr['form_score']:
            return TaskIntent.EXTRACT_PRODUCTS, 0.65, "Product page default = extraction"
        
        # Fallback
        if instr['extraction_score'] > 0:
            return TaskIntent.EXTRACT_GENERIC, 0.5, "Low confidence extraction"
        
        return TaskIntent.UNKNOWN, 0.3, "Could not determine intent"
    
    def _get_recommended_params(
        self,
        intent: TaskIntent,
        page_analysis: PageAnalysis
    ) -> Dict[str, Any]:
        """Generate recommended runtime parameters for the intent"""
        
        params = {}
        
        # Extraction intents
        if intent in [
            TaskIntent.EXTRACT_PRODUCTS,
            TaskIntent.EXTRACT_ARTICLES,
            TaskIntent.EXTRACT_LINKS,
            TaskIntent.EXTRACT_TABLE,
            TaskIntent.EXTRACT_GENERIC,
            TaskIntent.COMPARE_DATA
        ]:
            params = {
                'no_form_fill': True,  # Don't try to fill forms
                'no_click': True,       # Don't click navigation
                'include_dom_html': True,
                'fastpath': False,      # Use full extraction
            }
        
        # Form filling intents
        elif intent in [
            TaskIntent.FILL_CONTACT_FORM,
            TaskIntent.FILL_LOGIN_FORM,
            TaskIntent.FILL_REGISTER_FORM,
            TaskIntent.FILL_GENERIC
        ]:
            params = {
                'no_form_fill': False,
                'include_dom_html': True,
                'streamware_form': True,  # Use form orchestrator
            }
        
        return params


# Convenience function for quick intent detection
async def detect_intent(
    instruction: str,
    page_context: Optional[Dict[str, Any]] = None,
    url: Optional[str] = None,
    llm=None
) -> IntentResult:
    """Quick intent detection"""
    detector = IntentDetector(llm)
    return await detector.detect_intent(instruction, page_context, url)
