"""
Command Parser - Structural parsing of natural language commands

Parses complex commands like:
  "Wejdź na prototypowanie.pl i wyślij wiadomość przez formularz 
   z zapytaniem o dostępność usługi prototypowania 3d 
   z adresem email info@softreck.com i nazwiskiem Sapletta"

Into structured ParsedCommand with:
  - target domain/URL
  - primary and secondary goals
  - form data (email, name, phone, etc.)
  - message content
  - product/order info
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from curllm_core.url_types import TaskGoal

logger = logging.getLogger(__name__)


@dataclass
class FormData:
    """Extracted form field data"""
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    order_number: Optional[str] = None
    product_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dict, excluding None values"""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def is_empty(self) -> bool:
        return all(v is None for v in self.__dict__.values())


@dataclass
class ParsedCommand:
    """Structured representation of a natural language command"""
    
    # Target
    target_domain: Optional[str] = None
    target_url: Optional[str] = None
    
    # Goals
    primary_goal: TaskGoal = TaskGoal.GENERIC
    secondary_goals: List[TaskGoal] = field(default_factory=list)
    
    # Data
    form_data: FormData = field(default_factory=FormData)
    search_query: Optional[str] = None
    
    # Action sequence
    action_keywords: List[str] = field(default_factory=list)
    
    # Original
    original_instruction: str = ""
    
    # Parsing confidence
    confidence: float = 0.0
    parsing_notes: List[str] = field(default_factory=list)
    
    def get_url(self) -> Optional[str]:
        """Get full URL"""
        if self.target_url:
            return self.target_url
        if self.target_domain:
            return f"https://{self.target_domain}"
        return None


class CommandParser:
    """
    Parse natural language commands into structured format.
    
    Usage:
        parser = CommandParser()
        parsed = parser.parse("Wejdź na example.com i wyślij formularz...")
        
        print(parsed.target_domain)  # example.com
        print(parsed.primary_goal)   # TaskGoal.FIND_CONTACT_FORM
        print(parsed.form_data.email)  # extracted email
    """
    
    # Domain extraction patterns
    DOMAIN_PATTERNS = [
        # Full URLs with protocol
        r'(https?://[^\s]+)',
        # Domain with path (e.g., httpbin.org/forms/post)
        r'(?:wejdź na|wejdz na|otwórz|otworz|przejdź do|przejdz do|idź na|idz na|odwiedź|odwiedz)\s+(?:stronę\s+|strone\s+)?(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*)+(?:/[^\s]*)?)',
        r'(?:na|do|w)\s+(?:sklepie?\s+|serwisie?\s+)?(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-z]{2,}(?:\.[a-z]{2,})?(?:/[^\s]*)?)',
        # Just domain
        r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:pl|com|net|eu|org|io|co)(?:\.[a-z]{2,})?(?:/[^\s]*)?)\b',
    ]
    
    # Email pattern
    EMAIL_PATTERN = r'[\w.+-]+@[\w.-]+\.[a-z]{2,}'
    
    # Phone patterns
    PHONE_PATTERNS = [
        r'\b(\+?\d{2,3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3})\b',
        r'\b(\d{3}[-\s]?\d{3}[-\s]?\d{3})\b',
        r'\b(\d{9})\b',
    ]
    
    # Name patterns
    NAME_PATTERNS = [
        r'nazwisk(?:o|iem|a)\s*[:\s]+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?)',
        r'imi(?:ę|e|eniem)\s*[:\s]+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)?)',
        r'dane[:\s]+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)',
        r'(?:imię i nazwisko|name)[:\s]+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)',
    ]
    
    # Order/invoice patterns
    ORDER_PATTERNS = [
        r'(?:zamówieni[ea]|nr|numer|order)\s*[:#]?\s*([A-Z0-9][-A-Z0-9/]+)',
        r'(?:paragon|faktur[ay]|invoice)\s*[:#]?\s*([A-Z0-9][-A-Z0-9/]+)',
        r'#\s*(\d+)',
    ]
    
    # Goal keywords mapping - expanded for better detection
    GOAL_KEYWORDS = {
        # Communication
        TaskGoal.FIND_CONTACT_FORM: [
            'kontakt', 'contact', 'formularz', 'form', 'napisz', 'wyślij', 'wiadomość',
            'zapytanie', 'inquiry', 'message', 'skontaktuj', 'obsługa klienta',
            'customer service', 'support', 'dział obsługi', 'biuro obsługi'
        ],
        
        # Shopping
        TaskGoal.FIND_CART: [
            'koszyk', 'cart', 'basket', 'dodaj do koszyka', 'add to cart', 'bag'
        ],
        TaskGoal.FIND_CHECKOUT: [
            'checkout', 'kasa', 'zamówienie', 'zapłać', 'płatność', 'finalizuj',
            'przejdź do płatności', 'złóż zamówienie', 'place order'
        ],
        
        # Account
        TaskGoal.FIND_LOGIN: [
            'zaloguj', 'login', 'logowanie', 'sign in', 'moje konto', 'my account',
            'konto', 'account', 'zalogować', 'logować się'
        ],
        TaskGoal.FIND_REGISTER: [
            'zarejestruj', 'register', 'załóż konto', 'rejestracja', 'nowe konto',
            'create account', 'sign up', 'założyć konto'
        ],
        TaskGoal.FIND_ACCOUNT: [
            'moje zamówienia', 'historia zamówień', 'order history', 'profil',
            'ustawienia konta', 'account settings'
        ],
        
        # Information
        TaskGoal.FIND_SHIPPING: [
            'dostawa', 'shipping', 'wysyłka', 'delivery', 'koszty dostawy',
            'czas dostawy', 'metody wysyłki', 'transport', 'kurier'
        ],
        TaskGoal.FIND_RETURNS: [
            'zwrot', 'return', 'reklamacja', 'wymiana', 'zwrócić produkt',
            'polityka zwrotów', 'return policy', 'zwroty', 'odstąpienie'
        ],
        TaskGoal.FIND_FAQ: [
            'faq', 'pytania', 'często zadawane', 'questions', 'q&a'
        ],
        TaskGoal.FIND_HELP: [
            'pomoc', 'help', 'wsparcie', 'support', 'jak', 'how to',
            'centrum pomocy', 'help center'
        ],
        TaskGoal.FIND_WARRANTY: [
            'gwarancja', 'warranty', 'serwis', 'naprawa', 'guarantee'
        ],
        TaskGoal.FIND_TERMS: [
            'regulamin', 'terms', 'warunki', 'zasady', 'rules', 'tos'
        ],
        TaskGoal.FIND_PRIVACY: [
            'prywatność', 'privacy', 'rodo', 'gdpr', 'cookies', 'dane osobowe'
        ],
        TaskGoal.FIND_ABOUT: [
            'o nas', 'about', 'about us', 'kim jesteśmy', 'o firmie', 'historia'
        ],
        
        # Pricing
        TaskGoal.FIND_PRICING: [
            'cena', 'ceny', 'cennik', 'prices', 'pricing', 'price list',
            'ile kosztuje', 'koszt', 'wycena', 'opłaty', 'tariff', 'rates',
            'ceny usług', 'pakiety', 'plans', 'subskrypcja'
        ],
        
        # Content
        TaskGoal.FIND_BLOG: [
            'blog', 'artykuły', 'articles', 'poradnik', 'guide', 'porady',
            'tips', 'wpisy', 'posts', 'aktualności'
        ],
        TaskGoal.FIND_NEWS: [
            'nowości', 'news', 'aktualności', 'ogłoszenia', 'what\'s new'
        ],
        TaskGoal.FIND_DOWNLOADS: [
            'pobierz', 'download', 'pliki', 'dokumenty', 'files', 'materiały'
        ],
        
        # Other
        TaskGoal.FIND_CAREERS: [
            'kariera', 'careers', 'praca', 'jobs', 'oferty pracy', 'rekrutacja',
            'hiring', 'dołącz do nas', 'oferty rekrutacyjne', 'szukam pracy'
        ],
        TaskGoal.FIND_STORES: [
            'sklepy', 'stores', 'lokalizacje', 'locations', 'znajdź sklep',
            'punkty sprzedaży', 'salony'
        ],
        
        # Products - lower priority so other goals match first
        TaskGoal.EXTRACT_PRODUCTS: [
            'produkty', 'products', 'wylistuj', 'lista produktów'
        ],
    }
    
    # Action keywords for sequence detection
    ACTION_KEYWORDS = [
        'wejdź', 'otwórz', 'przejdź', 'znajdź', 'wyszukaj', 'szukaj',
        'wypełnij', 'wyślij', 'napisz', 'dodaj', 'kup', 'zamów',
        'zaloguj', 'zarejestruj', 'pobierz', 'sprawdź'
    ]
    
    def parse(self, instruction: str) -> ParsedCommand:
        """
        Parse natural language instruction into structured command.
        
        Args:
            instruction: Natural language command
            
        Returns:
            ParsedCommand with extracted data
        """
        result = ParsedCommand(original_instruction=instruction)
        notes = []
        confidence_scores = []
        
        instruction_lower = instruction.lower()
        
        # 1. Extract domain/URL
        domain, url = self._extract_domain(instruction)
        if domain:
            result.target_domain = domain
            result.target_url = url
            notes.append(f"Domain: {domain}")
            confidence_scores.append(0.9)
        else:
            notes.append("No domain found")
            confidence_scores.append(0.3)
        
        # 2. Extract form data
        form_data = self._extract_form_data(instruction)
        result.form_data = form_data
        if not form_data.is_empty():
            notes.append(f"Form data: {form_data.to_dict()}")
            confidence_scores.append(0.8)
        
        # 3. Detect primary goal
        primary_goal, goal_confidence = self._detect_goal(instruction_lower)
        result.primary_goal = primary_goal
        notes.append(f"Primary goal: {primary_goal.value} ({goal_confidence:.0%})")
        confidence_scores.append(goal_confidence)
        
        # 4. Extract message content
        message = self._extract_message(instruction)
        if message:
            result.form_data.message = message
            notes.append(f"Message: {message[:50]}...")
        
        # 5. Extract search query (for product searches)
        search_query = self._extract_search_query(instruction)
        if search_query:
            result.search_query = search_query
            notes.append(f"Search query: {search_query}")
        
        # 6. Detect action sequence
        actions = self._detect_actions(instruction_lower)
        result.action_keywords = actions
        if actions:
            notes.append(f"Actions: {' → '.join(actions)}")
        
        # Calculate overall confidence
        result.confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        result.parsing_notes = notes
        
        logger.info(f"Parsed command: {result.primary_goal.value}, confidence={result.confidence:.0%}")
        
        return result
    
    def _extract_domain(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract domain and URL from text"""
        for pattern in self.DOMAIN_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matched = match.group(1) if match.lastindex else match.group(0)
                
                # Clean up trailing punctuation
                matched = matched.rstrip('.,;:')
                
                # Check if it's a full URL with protocol (http:// or https://)
                if matched.startswith('http://') or matched.startswith('https://'):
                    parsed = urlparse(matched)
                    return parsed.netloc, matched
                else:
                    # It might be domain or domain+path (like httpbin.org/path)
                    full_url = f"https://{matched}"
                    parsed = urlparse(full_url)
                    # Extract just the domain (netloc)
                    domain = parsed.netloc if parsed.netloc else matched.split('/')[0]
                    return domain, full_url
        
        return None, None
    
    def _extract_form_data(self, text: str) -> FormData:
        """Extract form field data from text"""
        data = FormData()
        
        # Email
        email_match = re.search(self.EMAIL_PATTERN, text, re.IGNORECASE)
        if email_match:
            data.email = email_match.group(0)
        
        # Phone
        for pattern in self.PHONE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                data.phone = match.group(1)
                break
        
        # Name
        for pattern in self.NAME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data.name = match.group(1).strip()
                break
        
        # Order number
        for pattern in self.ORDER_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data.order_number = match.group(1).strip()
                break
        
        return data
    
    def _detect_goal(self, text_lower: str) -> Tuple[TaskGoal, float]:
        """Detect primary goal from text with fuzzy matching"""
        scores = {}
        
        # Normalize text - remove polish accents for matching
        text_normalized = self._normalize_polish(text_lower)
        
        for goal, keywords in self.GOAL_KEYWORDS.items():
            score = 0
            for kw in keywords:
                kw_normalized = self._normalize_polish(kw.lower())
                # Exact match
                if kw in text_lower:
                    score += 2
                # Normalized match (handles accents)
                elif kw_normalized in text_normalized:
                    score += 1.5
                # Stem match (zalogować → zaloguj)
                elif len(kw) >= 4 and kw[:4] in text_lower:
                    score += 1
                # Word stem in text
                elif len(kw) >= 5 and any(kw[:5] in word for word in text_lower.split()):
                    score += 0.8
            if score > 0:
                scores[goal] = score
        
        if not scores:
            return TaskGoal.GENERIC, 0.3
        
        best_goal = max(scores, key=scores.get)
        max_score = scores[best_goal]
        
        # Normalize confidence
        confidence = min(0.95, 0.5 + (max_score * 0.1))
        
        return best_goal, confidence
    
    def _normalize_polish(self, text: str) -> str:
        """Normalize Polish characters for matching"""
        replacements = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
        }
        for pl, ascii in replacements.items():
            text = text.replace(pl, ascii)
        return text
    
    def _extract_message(self, text: str) -> Optional[str]:
        """Extract message content from instruction"""
        patterns = [
            r'(?:z\s+)?(?:zapytaniem|pytaniem)\s+o\s+(.+?)(?:,\s*z\s+(?:adresem|email)|$)',
            r'(?:w\s+)?sprawie\s+(.+?)(?:,\s*(?:dane|moje|email)|$)',
            r'(?:treść|message|wiadomość)[:\s]+(.+?)(?:,|$)',
            r'(?:napisz|wyślij)[:\s]+(.+?)(?:,\s*(?:dane|email)|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_search_query(self, text: str) -> Optional[str]:
        """Extract product/search query"""
        patterns = [
            r'(?:znajdź|szukaj|wyszukaj)\s+(.+?)(?:,|i\s+(?:dodaj|kup|zamów)|$)',
            r'(?:produkty?|products?)\s*[:\s]+(.+?)(?:,|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                # Clean up common suffixes
                query = re.sub(r'\s+(?:i\s+)?(?:dodaj|kup|zamów|wyślij).*$', '', query)
                return query
        
        return None
    
    def _detect_actions(self, text_lower: str) -> List[str]:
        """Detect action sequence in instruction"""
        found = []
        for action in self.ACTION_KEYWORDS:
            if action in text_lower:
                # Find position for ordering
                pos = text_lower.find(action)
                found.append((pos, action))
        
        # Sort by position and return just actions
        found.sort(key=lambda x: x[0])
        return [action for pos, action in found]


def parse_command(instruction: str) -> ParsedCommand:
    """Convenience function for parsing commands"""
    parser = CommandParser()
    return parser.parse(instruction)
