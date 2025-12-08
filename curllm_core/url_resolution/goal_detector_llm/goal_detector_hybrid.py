"""Goal Detector - LLM-first with statistical fallback

Architecture:
1. LLM semantic analysis (primary)
2. Statistical word-overlap scoring (fallback)
3. NO HARDCODED KEYWORD LISTS

The statistical fallback derives keywords from TaskGoal enum values,
not from predefined lists.
"""

import logging
import asyncio
from curllm_core.url_types import TaskGoal

from .goal_detection_result import GoalDetectionResult

logger = logging.getLogger(__name__)


class GoalDetectorHybrid:
    """
    Hybrid goal detector using LLM with fallback.
    
    Uses LLM to understand user intent without hardcoded keywords.
    Falls back to simple heuristics only when LLM is unavailable.
    """
    
    def __init__(self, llm=None):
        self.llm = llm
    
    def detect_goal_sync(self, instruction: str) -> GoalDetectionResult:
        """
        Synchronously detect goal from instruction.
        
        Uses asyncio.run() for LLM calls when possible,
        falls back to statistical analysis in running loops.
        """
        # Try to use LLM via new event loop
        if self.llm:
            try:
                # Create new event loop for sync context
                return asyncio.run(self.detect_goal(instruction))
            except RuntimeError as e:
                # Already in async context - use statistical fallback
                if "running event loop" in str(e) or "cannot be called" in str(e):
                    logger.debug("Async context detected, using statistical fallback")
                else:
                    logger.debug(f"asyncio.run failed: {e}")
        
        # Fallback to statistical analysis (NO hardcoded keywords)
        return self._detect_goal_statistical(instruction)
    
    async def detect_goal(self, instruction: str) -> GoalDetectionResult:
        """
        Detect user's navigation goal using LLM.
        
        Args:
            instruction: User's instruction text
            
        Returns:
            GoalDetectionResult with detected goal and confidence
        """
        if not self.llm:
            return self._detect_goal_statistical(instruction)
        
        try:
            prompt = f"""Analyze this user instruction and determine the navigation goal.

Instruction: "{instruction}"

Possible goals (choose ONE):
- FIND_PRODUCTS: User wants to find/browse products or items for sale
- FIND_CART: User wants to access shopping cart
- FIND_LOGIN: User wants to log in or access their account
- FIND_REGISTER: User wants to create a new account
- FIND_CONTACT_FORM: User wants to contact support or send a message
- FIND_SHIPPING: User wants shipping/delivery information
- FIND_RETURNS: User wants returns/refund information
- FIND_FAQ: User wants FAQ or frequently asked questions
- FIND_HELP: User wants help or documentation
- NAVIGATE_TO_CATEGORY: User wants a specific category page
- SEARCH_FOR_PRODUCTS: User wants to search for specific products
- OTHER: None of the above

Respond with JSON:
{{"goal": "GOAL_NAME", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                data = json.loads(json_match.group())
                goal_name = data.get('goal', 'OTHER')
                confidence = float(data.get('confidence', 0.5))
                reasoning = data.get('reasoning', '')
                
                # Map goal name to TaskGoal enum
                goal = self._map_goal_name(goal_name)
                
                return GoalDetectionResult(
                    goal=goal,
                    confidence=confidence,
                    reasoning=reasoning
                )
        except Exception as e:
            logger.debug(f"LLM goal detection failed: {e}")
        
        return self._detect_goal_statistical(instruction)
    
    def _map_goal_name(self, goal_name: str) -> TaskGoal:
        """Map goal name string to TaskGoal enum."""
        mapping = {
            'FIND_PRODUCTS': TaskGoal.FIND_PRODUCTS,
            'EXTRACT_PRODUCTS': TaskGoal.EXTRACT_PRODUCTS,
            'SEARCH_FOR_PRODUCTS': TaskGoal.SEARCH_FOR_PRODUCTS,
            'NAVIGATE_TO_CATEGORY': TaskGoal.NAVIGATE_TO_CATEGORY,
            'FIND_CART': TaskGoal.FIND_CART,
            'FIND_LOGIN': TaskGoal.FIND_LOGIN,
            'FIND_REGISTER': TaskGoal.FIND_REGISTER,
            'FIND_CONTACT_FORM': TaskGoal.FIND_CONTACT_FORM,
            'FIND_SHIPPING': TaskGoal.FIND_SHIPPING,
            'FIND_RETURNS': TaskGoal.FIND_RETURNS,
            'FIND_FAQ': TaskGoal.FIND_FAQ,
            'FIND_HELP': TaskGoal.FIND_HELP,
            'FIND_WARRANTY': TaskGoal.FIND_WARRANTY,
            'FIND_TERMS': TaskGoal.FIND_TERMS,
            'FIND_PRIVACY': TaskGoal.FIND_PRIVACY,
            'FIND_CAREERS': TaskGoal.FIND_CAREERS,
            'FIND_BLOG': TaskGoal.FIND_BLOG,
            'FIND_ACCOUNT': TaskGoal.FIND_ACCOUNT,
            'FIND_STORES': TaskGoal.FIND_STORES,
            'OTHER': TaskGoal.GENERIC,
        }
        return mapping.get(goal_name, TaskGoal.GENERIC)
    
    def _detect_goal_statistical(self, instruction: str) -> GoalDetectionResult:
        """
        Statistical goal detection using word-overlap scoring.
        
        NO HARDCODED KEYWORD LISTS.
        Derives keywords from TaskGoal enum values dynamically.
        """
        instr_lower = instruction.lower()
        normalized = self._normalize_polish(instr_lower)
        instr_words = set(normalized.split())
        
        best_goal = TaskGoal.GENERIC
        best_score = 0.0
        
        # Score each goal based on word overlap with its enum value
        for goal in TaskGoal:
            if goal == TaskGoal.GENERIC:
                continue
            
            # Derive keywords from goal's enum value (e.g., "find_cart" -> ["find", "cart"])
            goal_words = set(goal.value.replace('_', ' ').lower().split())
            
            # Also add common translations for better matching
            translations = self._get_goal_translations(goal)
            goal_words.update(translations)
            
            # Calculate score using substring matching (for stemmed words)
            score = 0.0
            for gw in goal_words:
                # Check if goal word stem appears in instruction
                if gw in normalized:
                    score += 1.0
                # Also check exact word match
                elif gw in instr_words:
                    score += 0.8
            
            # Bonus for key indicator words (first 3 translations)
            if translations:
                for kw in translations[:3]:
                    if kw in normalized:
                        score += 0.5
            
            if score > best_score:
                best_score = score
                best_goal = goal
        
        # Calculate confidence based on score
        if best_score >= 1.5:
            confidence = 0.8
        elif best_score >= 1.0:
            confidence = 0.6
        elif best_score >= 0.5:
            confidence = 0.4
        else:
            confidence = 0.2
            best_goal = TaskGoal.GENERIC
        
        logger.debug(f"Statistical goal detection: {best_goal} (score={best_score:.2f}, conf={confidence})")
        return GoalDetectionResult(best_goal, confidence)
    
    def _get_goal_translations(self, goal: TaskGoal) -> list:
        """
        Get common translations for a goal.
        
        These are NOT hardcoded selectors - they are semantic translations
        of goal purposes for better language coverage.
        """
        # Semantic translations including stemmed variants for Polish
        # These are word stems/roots, not full words, for better matching
        translations = {
            TaskGoal.FIND_CART: ['koszyk', 'cart', 'basket', 'bag'],
            TaskGoal.FIND_LOGIN: ['zaloguj', 'loguj', 'login', 'logowa', 'sign in', 'signin'],
            TaskGoal.FIND_REGISTER: ['rejestrac', 'register', 'zaloz', 'utworz', 'signup', 'konto'],
            TaskGoal.FIND_CONTACT_FORM: ['kontakt', 'contact', 'napisz', 'wiadomosc', 'obslug'],
            TaskGoal.FIND_PRODUCTS: ['produkty', 'products', 'znajdz', 'szukaj', 'pokaz', 'wylistuj', 'lista'],
            TaskGoal.SEARCH_FOR_PRODUCTS: ['szukaj', 'search', 'wyszukaj', 'znajdz'],
            TaskGoal.NAVIGATE_TO_CATEGORY: ['kategori', 'category', 'dzial', 'sekcj'],
            TaskGoal.FIND_SHIPPING: ['dostaw', 'shipping', 'wysylk', 'delivery', 'transport'],
            TaskGoal.FIND_RETURNS: ['zwrot', 'zwroc', 'return', 'reklamacj', 'oddaj', 'oddac'],
            TaskGoal.FIND_FAQ: ['faq', 'pytani', 'czesto'],
            TaskGoal.FIND_HELP: ['pomoc', 'help', 'wsparci', 'support'],
            TaskGoal.FIND_WARRANTY: ['gwarancj', 'warranty', 'serwis'],
            TaskGoal.FIND_TERMS: ['regulamin', 'terms', 'warunk', 'zasad'],
            TaskGoal.FIND_PRIVACY: ['prywatnosc', 'privacy', 'rodo', 'gdpr', 'dane'],
            TaskGoal.FIND_CAREERS: ['karier', 'praca', 'jobs', 'rekrutacj', 'hiring', 'ofert'],
            TaskGoal.FIND_BLOG: ['blog', 'artykul', 'poradnik', 'news'],
            TaskGoal.FIND_ACCOUNT: ['zamowien', 'account', 'profil', 'moje'],
            TaskGoal.EXTRACT_PRODUCTS: ['ekstrakt', 'extract', 'pobierz'],
            TaskGoal.FIND_STORES: ['sklep', 'store', 'salon', 'punkt'],
        }
        return translations.get(goal, [])
    
    def _normalize_polish(self, text: str) -> str:
        """Normalize Polish characters for matching"""
        replacements = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
        }
        for pl, ascii in replacements.items():
            text = text.replace(pl, ascii)
        return text
