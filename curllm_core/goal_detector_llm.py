"""
Goal Detector LLM - Intelligent goal detection using LLM + statistical methods

Instead of hardcoded keyword lists, this module uses:
1. LLM to understand user intent (when available)
2. Statistical similarity (TF-IDF, cosine similarity) as fallback
3. Goal embeddings for semantic matching

This provides flexibility without maintaining large keyword dictionaries.
"""

import re
import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

from .url_types import TaskGoal

logger = logging.getLogger(__name__)


@dataclass
class GoalMatch:
    """Result of goal detection"""
    goal: TaskGoal
    confidence: float
    method: str  # "llm", "statistical", "embedding", "fallback"
    reasoning: str


# Goal descriptions for LLM and semantic matching (PL + EN for better coverage)
GOAL_DESCRIPTIONS = {
    TaskGoal.FIND_CART: "koszyk cart basket zakupy shopping dodaj do koszyka add to cart bag",
    TaskGoal.FIND_CHECKOUT: "checkout kasa zamowienie zamówienie zaplac zapłać platnosc płatność finalizuj order payment",
    TaskGoal.FIND_LOGIN: "zaloguj login logowanie sign in konto account moje konto my account zalogowac zalogować",
    TaskGoal.FIND_REGISTER: "zarejestruj register rejestracja sign up zaloz konto załóż konto create account nowe konto",
    TaskGoal.FIND_ACCOUNT: "moje konto profil ustawienia konta account settings historia zamowien order history panel",
    TaskGoal.FIND_CONTACT_FORM: "kontakt contact formularz form napisz wyslij wyślij wiadomosc wiadomość obsluga klienta obsługa support pomoc",
    TaskGoal.FIND_FAQ: "faq pytania questions czesto zadawane często help center centrum pomocy",
    TaskGoal.FIND_HELP: "pomoc help wsparcie support jak how to centrum pomocy assistance",
    TaskGoal.FIND_SHIPPING: "dostawa shipping wysylka wysyłka delivery transport kurier koszty dostawy czas dostawy",
    TaskGoal.FIND_RETURNS: "zwrot return reklamacja wymiana zwroty returns odstapienie odstąpienie polityka zwrotow refund",
    TaskGoal.FIND_WARRANTY: "gwarancja warranty serwis naprawa guarantee rękojmia warunki gwarancji",
    TaskGoal.FIND_TERMS: "regulamin terms warunki zasady rules tos terms of service",
    TaskGoal.FIND_PRIVACY: "prywatnosc prywatność privacy rodo gdpr cookies dane osobowe data protection",
    TaskGoal.FIND_ABOUT: "o nas about about us firma kim jestesmy kim jesteśmy historia company",
    TaskGoal.FIND_PRICING: "cena ceny cennik prices pricing price list koszt wycena oplaty opłaty pakiety plans",
    TaskGoal.FIND_BLOG: "blog artykuly artykuły articles poradnik guide porady aktualnosci aktualności news wpisy",
    TaskGoal.FIND_CAREERS: "kariera careers praca jobs oferty pracy rekrutacja hiring dolacz do nas dołącz szukam pracy",
    TaskGoal.FIND_STORES: "sklepy stores lokalizacje locations znajdz sklep znajdź punkty sprzedazy salony",
    TaskGoal.EXTRACT_PRODUCTS: "produkty products szukaj znajdz znajdź wyszukaj lista produktow wylistuj",
    TaskGoal.GENERIC: "przegladaj przeglądaj ogolne ogólne browsing",
}


class GoalDetectorLLM:
    """
    Intelligent goal detector using LLM and statistical methods.
    
    Replaces hardcoded keyword matching with:
    1. LLM classification (most accurate)
    2. TF-IDF similarity (fast fallback)
    3. N-gram matching (lightweight fallback)
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self._tfidf_cache = {}
        self._build_goal_vectors()
    
    def _build_goal_vectors(self):
        """Build TF-IDF vectors for goal descriptions"""
        self.goal_tokens = {}
        self.idf = Counter()
        
        # Tokenize all goal descriptions
        all_docs = []
        for goal, desc in GOAL_DESCRIPTIONS.items():
            tokens = self._tokenize(desc)
            self.goal_tokens[goal] = tokens
            all_docs.append(set(tokens))
            self.idf.update(set(tokens))
        
        # Calculate IDF
        n_docs = len(all_docs)
        self.idf = {
            token: math.log(n_docs / count) 
            for token, count in self.idf.items()
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization with Polish support"""
        text = text.lower()
        # Normalize Polish characters
        replacements = {
            'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n',
            'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z'
        }
        for pl, ascii in replacements.items():
            text = text.replace(pl, ascii)
        
        # Extract words
        tokens = re.findall(r'\b\w{2,}\b', text)
        return tokens
    
    async def detect_goal(self, instruction: str) -> GoalMatch:
        """
        Detect user's goal from instruction.
        
        Uses LLM if available, otherwise falls back to statistical methods.
        """
        # Try LLM first (most accurate)
        if self.llm:
            try:
                result = await self._detect_with_llm(instruction)
                if result.confidence > 0.6:
                    return result
            except Exception as e:
                logger.debug(f"LLM detection failed: {e}")
        
        # Fall back to statistical methods
        return self._detect_statistical(instruction)
    
    async def _detect_with_llm(self, instruction: str) -> GoalMatch:
        """Use LLM to classify user intent"""
        
        # Build goal options
        goal_options = "\n".join([
            f"- {goal.value}: {desc}"
            for goal, desc in GOAL_DESCRIPTIONS.items()
            if goal != TaskGoal.GENERIC
        ])
        
        prompt = f"""Classify the user's intent into one of these categories:

{goal_options}

User instruction: "{instruction}"

Respond with JSON only:
{{"goal": "goal_name", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

        response = await self.llm.generate(prompt)
        
        try:
            data = json.loads(response)
            goal_name = data.get("goal", "generic")
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning", "")
            
            # Find matching TaskGoal
            goal = TaskGoal.GENERIC
            for g in TaskGoal:
                if g.value == goal_name:
                    goal = g
                    break
            
            return GoalMatch(
                goal=goal,
                confidence=confidence,
                method="llm",
                reasoning=reasoning
            )
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Failed to parse LLM response: {e}")
            return GoalMatch(
                goal=TaskGoal.GENERIC,
                confidence=0.3,
                method="llm_fallback",
                reasoning="Failed to parse LLM response"
            )
    
    def _detect_statistical(self, instruction: str) -> GoalMatch:
        """Use TF-IDF similarity to detect goal"""
        
        query_tokens = self._tokenize(instruction)
        if not query_tokens:
            return GoalMatch(
                goal=TaskGoal.GENERIC,
                confidence=0.2,
                method="statistical",
                reasoning="No tokens extracted"
            )
        
        # Calculate TF for query
        query_tf = Counter(query_tokens)
        query_len = len(query_tokens)
        
        # Calculate similarity with each goal
        scores = {}
        for goal, goal_tokens in self.goal_tokens.items():
            if goal == TaskGoal.GENERIC:
                continue
            
            goal_tf = Counter(goal_tokens)
            goal_len = len(goal_tokens)
            
            # Cosine similarity with TF-IDF weighting
            score = 0.0
            query_norm = 0.0
            goal_norm = 0.0
            
            all_tokens = set(query_tokens) | set(goal_tokens)
            for token in all_tokens:
                idf = self.idf.get(token, 1.0)
                q_tfidf = (query_tf.get(token, 0) / query_len) * idf
                g_tfidf = (goal_tf.get(token, 0) / goal_len) * idf
                
                score += q_tfidf * g_tfidf
                query_norm += q_tfidf ** 2
                goal_norm += g_tfidf ** 2
            
            if query_norm > 0 and goal_norm > 0:
                score = score / (math.sqrt(query_norm) * math.sqrt(goal_norm))
                scores[goal] = score
        
        if not scores:
            return GoalMatch(
                goal=TaskGoal.GENERIC,
                confidence=0.2,
                method="statistical",
                reasoning="No matching goals found"
            )
        
        # Get best match
        best_goal = max(scores, key=scores.get)
        best_score = scores[best_goal]
        
        # Normalize confidence
        confidence = min(0.9, best_score * 2)  # Scale up since TF-IDF scores are usually low
        
        return GoalMatch(
            goal=best_goal,
            confidence=confidence,
            method="statistical",
            reasoning=f"TF-IDF similarity: {best_score:.3f}"
        )
    
    def detect_goal_sync(self, instruction: str) -> GoalMatch:
        """Synchronous version using only statistical methods"""
        return self._detect_statistical(instruction)


class GoalDetectorHybrid:
    """
    Hybrid goal detector combining multiple methods.
    
    Uses ensemble of:
    1. LLM classification
    2. Statistical similarity
    3. Pattern matching (lightweight)
    """
    
    def __init__(self, llm_client=None):
        self.llm_detector = GoalDetectorLLM(llm_client)
        self._build_patterns()
    
    def _build_patterns(self):
        """Build regex patterns for quick matching"""
        self.patterns = {
            TaskGoal.FIND_CART: [
                r'\bkoszyk\b', r'\bcart\b', r'\bbasket\b', r'\bbag\b',
                r'\bdodaj\s+do\s+koszyka\b', r'\badd\s+to\s+cart\b'
            ],
            TaskGoal.FIND_CHECKOUT: [
                r'\bcheckout\b', r'\bkasa\b', r'\bzam[oó]wienie\b',
                r'\bzap[lł]a[cć]\b', r'\bp[lł]atno[sś][cć]\b'
            ],
            TaskGoal.FIND_LOGIN: [
                r'\bzaloguj\b', r'\blogin\b', r'\blogowanie\b',
                r'\bsign\s*in\b', r'\bkonto\b', r'\baccount\b'
            ],
            TaskGoal.FIND_REGISTER: [
                r'\bzarejestruj\b', r'\bregister\b', r'\brejestracja\b',
                r'\bza[lł][oó][zż]\s+konto\b', r'\bsign\s*up\b', r'\bnowe\s+konto\b'
            ],
            TaskGoal.FIND_CONTACT_FORM: [
                r'\bkontakt\b', r'\bcontact\b', r'\bformularz\b',
                r'\bwiadomo[sś][cć]\b', r'\bobs[lł]ug[aią]\s+klienta\b',
                r'\bsupport\b', r'\bpomoc\b'
            ],
            TaskGoal.FIND_SHIPPING: [
                r'\bdostawa\b', r'\bshipping\b', r'\bwysy[lł]ka\b',
                r'\bdelivery\b', r'\btransport\b', r'\bkurier\b'
            ],
            TaskGoal.FIND_RETURNS: [
                r'\bzwrot\b', r'\breturn\b', r'\breklamacja\b',
                r'\bwymiana\b', r'\bodst[aą]pienie\b'
            ],
            TaskGoal.FIND_FAQ: [
                r'\bfaq\b', r'\bpytania\b', r'\bquestions\b'
            ],
            TaskGoal.FIND_HELP: [
                r'\bpomoc\b', r'\bhelp\b', r'\bwsparcie\b'
            ],
            TaskGoal.FIND_CAREERS: [
                r'\bkariera\b', r'\bcareers?\b', r'\bpraca\b',
                r'\bjobs?\b', r'\brekrutacja\b', r'\bhiring\b'
            ],
            TaskGoal.FIND_BLOG: [
                r'\bblog\b', r'\bartykuły\b', r'\barticles?\b',
                r'\bporadnik\b', r'\bguide\b', r'\baktualn\b'
            ],
        }
        
        # Compile patterns
        self.compiled_patterns = {
            goal: [re.compile(p, re.IGNORECASE) for p in patterns]
            for goal, patterns in self.patterns.items()
        }
    
    def _pattern_match(self, instruction: str) -> Dict[TaskGoal, float]:
        """Quick pattern matching"""
        scores = {}
        for goal, patterns in self.compiled_patterns.items():
            match_count = sum(1 for p in patterns if p.search(instruction))
            if match_count > 0:
                scores[goal] = match_count / len(patterns)
        return scores
    
    async def detect_goal(self, instruction: str) -> GoalMatch:
        """
        Detect goal using ensemble of methods.
        
        Combines:
        1. Pattern matching (fast, specific)
        2. Statistical similarity (broader matching)
        3. LLM (most accurate, slower)
        """
        # Quick pattern check first
        pattern_scores = self._pattern_match(instruction)
        
        # If strong pattern match, use it
        if pattern_scores:
            best_pattern_goal = max(pattern_scores, key=pattern_scores.get)
            best_pattern_score = pattern_scores[best_pattern_goal]
            if best_pattern_score >= 0.5:
                return GoalMatch(
                    goal=best_pattern_goal,
                    confidence=min(0.9, best_pattern_score + 0.3),
                    method="pattern",
                    reasoning=f"Pattern match score: {best_pattern_score:.2f}"
                )
        
        # Try statistical matching
        stat_result = self.llm_detector._detect_statistical(instruction)
        
        # Combine pattern and statistical scores
        if pattern_scores and stat_result.goal in pattern_scores:
            combined_score = (
                pattern_scores[stat_result.goal] * 0.4 +
                stat_result.confidence * 0.6
            )
            stat_result.confidence = min(0.95, combined_score)
        
        # If still low confidence and LLM available, use it
        if stat_result.confidence < 0.5 and self.llm_detector.llm:
            try:
                llm_result = await self.llm_detector._detect_with_llm(instruction)
                if llm_result.confidence > stat_result.confidence:
                    return llm_result
            except Exception:
                pass
        
        return stat_result
    
    def detect_goal_sync(self, instruction: str) -> GoalMatch:
        """Synchronous detection without LLM"""
        pattern_scores = self._pattern_match(instruction)
        
        if pattern_scores:
            best_goal = max(pattern_scores, key=pattern_scores.get)
            best_score = pattern_scores[best_goal]
            if best_score >= 0.3:
                return GoalMatch(
                    goal=best_goal,
                    confidence=min(0.9, best_score + 0.3),
                    method="pattern",
                    reasoning=f"Pattern match: {best_score:.2f}"
                )
        
        return self.llm_detector._detect_statistical(instruction)


# Convenience functions
async def detect_goal_intelligent(
    instruction: str, 
    llm_client=None
) -> GoalMatch:
    """Detect goal using intelligent hybrid method"""
    detector = GoalDetectorHybrid(llm_client)
    return await detector.detect_goal(instruction)


def detect_goal_fast(instruction: str) -> GoalMatch:
    """Fast synchronous goal detection without LLM"""
    detector = GoalDetectorHybrid(None)
    return detector.detect_goal_sync(instruction)
