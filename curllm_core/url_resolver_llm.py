"""
URL Resolver LLM - Intelligent link finding using LLM + atomic functions

Instead of hardcoded selectors, this module uses:
1. LLM to understand goal and generate search criteria
2. Atomic DOM functions to efficiently search
3. LLM to validate/rank results

This provides flexibility without the brittleness of hardcoded selectors.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .url_types import TaskGoal
from . import dom_helpers

logger = logging.getLogger(__name__)


@dataclass
class LinkCandidate:
    """A potential link match"""
    url: str
    text: str
    score: float
    context: str  # surrounding text
    location: str  # header, footer, nav, main, etc.
    reason: str  # why this link matches


class LLMUrlResolver:
    """
    Intelligent URL resolver using LLM + atomic functions.
    
    Flow:
    1. LLM analyzes goal → generates search criteria (keywords, patterns)
    2. Atomic functions scan DOM efficiently
    3. LLM ranks/validates candidates
    """
    
    def __init__(self, page, llm_client=None):
        self.page = page
        self.llm = llm_client
        
    async def find_url_for_goal(self, goal: TaskGoal, instruction: str) -> Optional[LinkCandidate]:
        """
        Find URL for a specific goal using LLM-guided search.
        
        Args:
            goal: TaskGoal enum
            instruction: User's original instruction
            
        Returns:
            Best matching LinkCandidate or None
        """
        # Step 1: Generate search criteria using LLM (or fallback heuristics)
        search_criteria = await self._generate_search_criteria(goal, instruction)
        
        # Step 2: Use atomic functions to find candidates
        candidates = await self._find_candidates(search_criteria)
        
        if not candidates:
            logger.info(f"No candidates found for {goal.value}")
            return None
        
        # Step 3: Rank candidates (with LLM if available, otherwise heuristics)
        best = await self._rank_candidates(candidates, goal, instruction)
        
        if best:
            logger.info(f"✅ Found {goal.value}: {best.url} (score: {best.score:.2f})")
        
        return best
    
    async def _generate_search_criteria(self, goal: TaskGoal, instruction: str) -> Dict[str, Any]:
        """
        Generate search criteria for finding links.
        Uses LLM if available, otherwise uses intelligent heuristics.
        """
        if self.llm:
            return await self._llm_generate_criteria(goal, instruction)
        else:
            return self._heuristic_criteria(goal, instruction)
    
    async def _llm_generate_criteria(self, goal: TaskGoal, instruction: str) -> Dict[str, Any]:
        """Use LLM to generate search criteria"""
        prompt = f"""Analyze this user goal and generate search criteria for finding the right link on a webpage.

Goal: {goal.value}
User instruction: {instruction}

Generate JSON with:
- keywords: list of Polish and English words to look for in link text
- url_patterns: list of URL path patterns (e.g., "/kontakt", "/contact")
- aria_labels: list of possible aria-label values
- icon_hints: list of icon classes that might indicate this link
- section_priority: where to look first (header, footer, nav, main)

Return ONLY valid JSON, no explanation."""

        try:
            response = await self.llm.generate(prompt)
            return json.loads(response)
        except Exception as e:
            logger.debug(f"LLM criteria generation failed: {e}")
            return self._heuristic_criteria(goal, instruction)
    
    def _heuristic_criteria(self, goal: TaskGoal, instruction: str) -> Dict[str, Any]:
        """Generate search criteria using heuristics (fallback)"""
        
        # Goal-specific criteria
        criteria_map = {
            TaskGoal.FIND_CONTACT_FORM: {
                "keywords": ["kontakt", "contact", "napisz", "formularz", "zapytanie", 
                            "pomoc", "support", "help", "obsługa"],
                "url_patterns": ["/kontakt", "/contact", "/help", "/support", "/pomoc"],
                "section_priority": ["footer", "header", "nav"],
            },
            TaskGoal.FIND_CART: {
                "keywords": ["koszyk", "cart", "basket", "bag", "zakupy", "shopping"],
                "url_patterns": ["/koszyk", "/cart", "/basket", "/checkout"],
                "section_priority": ["header", "nav"],
            },
            TaskGoal.FIND_LOGIN: {
                "keywords": ["zaloguj", "login", "logowanie", "sign in", "moje konto", 
                            "account", "konto", "profil"],
                "url_patterns": ["/login", "/logowanie", "/account", "/konto", "/signin"],
                "section_priority": ["header", "nav"],
            },
            TaskGoal.FIND_REGISTER: {
                "keywords": ["zarejestruj", "register", "rejestracja", "załóż konto", 
                            "create account", "sign up", "nowe konto"],
                "url_patterns": ["/register", "/rejestracja", "/signup", "/create-account"],
                "section_priority": ["header", "nav"],
            },
            TaskGoal.FIND_FAQ: {
                "keywords": ["faq", "pytania", "pomoc", "help", "często zadawane", 
                            "questions", "odpowiedzi"],
                "url_patterns": ["/faq", "/help", "/pomoc", "/pytania"],
                "section_priority": ["footer", "nav"],
            },
            TaskGoal.FIND_SHIPPING: {
                "keywords": ["dostawa", "wysyłka", "shipping", "delivery", "transport",
                            "czas dostawy", "koszty wysyłki"],
                "url_patterns": ["/dostawa", "/shipping", "/delivery", "/wysylka"],
                "section_priority": ["footer", "nav"],
            },
            TaskGoal.FIND_RETURNS: {
                "keywords": ["zwrot", "zwroty", "return", "reklamacja", "wymiana",
                            "odstąpienie", "polityka zwrotów"],
                "url_patterns": ["/zwroty", "/returns", "/reklamacje", "/return-policy"],
                "section_priority": ["footer"],
            },
            TaskGoal.FIND_WARRANTY: {
                "keywords": ["gwarancja", "warranty", "serwis", "naprawa", "rękojmia"],
                "url_patterns": ["/gwarancja", "/warranty", "/serwis"],
                "section_priority": ["footer"],
            },
            TaskGoal.FIND_TERMS: {
                "keywords": ["regulamin", "terms", "warunki", "zasady", "rules"],
                "url_patterns": ["/regulamin", "/terms", "/warunki", "/tos"],
                "section_priority": ["footer"],
            },
            TaskGoal.FIND_PRIVACY: {
                "keywords": ["prywatność", "privacy", "rodo", "gdpr", "cookies", "dane"],
                "url_patterns": ["/privacy", "/prywatnosc", "/rodo", "/polityka-prywatnosci"],
                "section_priority": ["footer"],
            },
            TaskGoal.FIND_ABOUT: {
                "keywords": ["o nas", "about", "firma", "historia", "kim jesteśmy"],
                "url_patterns": ["/about", "/o-nas", "/firma", "/about-us"],
                "section_priority": ["footer", "nav"],
            },
            TaskGoal.FIND_CAREERS: {
                "keywords": ["kariera", "careers", "praca", "jobs", "oferty pracy", 
                            "rekrutacja", "hiring", "dołącz do zespołu"],
                "url_patterns": ["/kariera", "/careers", "/praca", "/jobs", "/hiring"],
                "section_priority": ["footer", "nav"],
            },
            TaskGoal.FIND_BLOG: {
                "keywords": ["blog", "artykuły", "articles", "poradnik", "porady",
                            "aktualności", "news", "wpisy"],
                "url_patterns": ["/blog", "/articles", "/poradnik", "/news", "/aktualnosci"],
                "section_priority": ["nav", "header", "footer"],
            },
            TaskGoal.FIND_STORES: {
                "keywords": ["sklepy", "stores", "lokalizacje", "locations", "salony",
                            "punkty sprzedaży", "znajdź sklep"],
                "url_patterns": ["/sklepy", "/stores", "/locations", "/salony"],
                "section_priority": ["footer", "nav"],
            },
            TaskGoal.FIND_ACCOUNT: {
                "keywords": ["konto", "account", "profil", "moje zamówienia", 
                            "historia zamówień", "zaloguj", "login"],
                "url_patterns": ["/account", "/konto", "/profil", "/login", "/panel"],
                "section_priority": ["header", "nav"],
            },
            TaskGoal.FIND_HELP: {
                "keywords": ["pomoc", "help", "wsparcie", "support", "centrum pomocy",
                            "jak", "how to"],
                "url_patterns": ["/help", "/pomoc", "/support", "/wsparcie"],
                "section_priority": ["footer", "header", "nav"],
            },
        }
        
        return criteria_map.get(goal, {
            "keywords": instruction.lower().split()[:5],
            "url_patterns": [],
            "section_priority": ["nav", "header", "footer", "main"],
        })
    
    async def _find_candidates(self, criteria: Dict[str, Any]) -> List[LinkCandidate]:
        """
        Use atomic DOM functions to find link candidates.
        Uses dom_helpers module for efficient, reusable operations.
        """
        keywords = criteria.get("keywords", [])
        url_patterns = criteria.get("url_patterns", [])
        section_priority = criteria.get("section_priority", [])
        
        candidates = []
        
        # Use atomic dom_helpers for multi-strategy link finding
        try:
            # Strategy 1: Find by text keywords
            text_matches = await dom_helpers.find_links_by_text(self.page, keywords)
            for link in text_matches[:5]:
                candidates.append(LinkCandidate(
                    url=link.url,
                    text=link.text[:100],
                    score=link.score * 2.0 + (1.0 if link.location in section_priority else 0),
                    context=link.context[:200],
                    location=link.location,
                    reason=f"text match"
                ))
            
            # Strategy 2: Find by URL patterns
            url_matches = await dom_helpers.find_links_by_url_pattern(self.page, url_patterns)
            for link in url_matches[:5]:
                candidates.append(LinkCandidate(
                    url=link.url,
                    text=link.text[:100],
                    score=link.score * 3.0 + (1.0 if link.location in section_priority else 0),
                    context=link.context[:200],
                    location=link.location,
                    reason=f"URL pattern"
                ))
            
            # Strategy 3: Find by aria labels
            aria_matches = await dom_helpers.find_links_by_aria(self.page, keywords)
            for link in aria_matches[:3]:
                candidates.append(LinkCandidate(
                    url=link.url,
                    text=link.text[:100],
                    score=link.score * 1.5 + (1.0 if link.location in section_priority else 0),
                    context=link.context[:200],
                    location=link.location,
                    reason=f"aria-label"
                ))
            
            # Deduplicate by URL
            seen = set()
            unique = []
            for c in sorted(candidates, key=lambda x: x.score, reverse=True):
                if c.url not in seen:
                    seen.add(c.url)
                    unique.append(c)
            
            if unique:
                return unique[:10]
                
        except Exception as e:
            logger.debug(f"dom_helpers failed, using fallback: {e}")
        
        # Fallback to legacy extraction
        links_data = await self._atomic_extract_links()
        
        for link in links_data:
            score = 0.0
            reasons = []
            
            text_lower = link.get("text", "").lower()
            href_lower = link.get("href", "").lower()
            aria_lower = link.get("aria_label", "").lower()
            location = link.get("location", "main")
            
            # Score based on keyword matches in text
            for kw in keywords:
                if kw.lower() in text_lower:
                    score += 2.0
                    reasons.append(f"text contains '{kw}'")
                if kw.lower() in aria_lower:
                    score += 1.5
                    reasons.append(f"aria-label contains '{kw}'")
            
            # Score based on URL pattern matches
            for pattern in url_patterns:
                if pattern.lower() in href_lower:
                    score += 3.0
                    reasons.append(f"URL matches '{pattern}'")
            
            # Bonus for being in prioritized section
            if location in section_priority:
                priority_bonus = (len(section_priority) - section_priority.index(location)) * 0.5
                score += priority_bonus
                reasons.append(f"in {location} section")
            
            # Penalize very long links (probably not navigation)
            if len(text_lower) > 100:
                score -= 1.0
            
            # Penalize empty or very short text
            if len(text_lower) < 2:
                score -= 2.0
            
            if score > 0:
                candidates.append(LinkCandidate(
                    url=link.get("href", ""),
                    text=link.get("text", "")[:100],
                    score=score,
                    context=link.get("context", "")[:200],
                    location=location,
                    reason="; ".join(reasons)
                ))
        
        # Sort by score
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        return candidates[:10]  # Return top 10
    
    async def _atomic_extract_links(self) -> List[Dict[str, Any]]:
        """
        Atomic function: Extract all links with rich context.
        This runs in the browser and is very fast.
        """
        return await self.page.evaluate("""
            () => {
                const links = [];
                const allAnchors = document.querySelectorAll('a[href]');
                
                // Helper to determine section location
                function getLocation(el) {
                    let current = el;
                    while (current && current !== document.body) {
                        const tag = current.tagName.toLowerCase();
                        const id = (current.id || '').toLowerCase();
                        const cls = (current.className || '').toLowerCase();
                        
                        if (tag === 'header' || id.includes('header') || cls.includes('header')) {
                            return 'header';
                        }
                        if (tag === 'footer' || id.includes('footer') || cls.includes('footer')) {
                            return 'footer';
                        }
                        if (tag === 'nav' || id.includes('nav') || cls.includes('nav') || cls.includes('menu')) {
                            return 'nav';
                        }
                        if (id.includes('sidebar') || cls.includes('sidebar')) {
                            return 'sidebar';
                        }
                        current = current.parentElement;
                    }
                    return 'main';
                }
                
                // Helper to get surrounding text context
                function getContext(el) {
                    const parent = el.parentElement;
                    if (!parent) return '';
                    return parent.innerText.slice(0, 300);
                }
                
                allAnchors.forEach(a => {
                    const href = a.href;
                    if (!href || href.startsWith('javascript:') || href === '#') return;
                    
                    // Get visible text
                    let text = a.innerText.trim();
                    if (!text) {
                        // Try aria-label or title
                        text = a.getAttribute('aria-label') || a.getAttribute('title') || '';
                    }
                    
                    // Skip image-only links without text
                    const hasOnlyImage = !text && a.querySelector('img, svg');
                    if (hasOnlyImage) {
                        const img = a.querySelector('img');
                        if (img) text = img.alt || '';
                    }
                    
                    links.push({
                        href: href,
                        text: text.trim(),
                        aria_label: a.getAttribute('aria-label') || '',
                        title: a.getAttribute('title') || '',
                        location: getLocation(a),
                        context: getContext(a),
                        class: a.className,
                        visible: a.offsetParent !== null
                    });
                });
                
                return links;
            }
        """)
    
    async def _rank_candidates(
        self, 
        candidates: List[LinkCandidate], 
        goal: TaskGoal, 
        instruction: str
    ) -> Optional[LinkCandidate]:
        """
        Rank candidates. Uses LLM if available for smarter ranking.
        """
        if not candidates:
            return None
        
        # If LLM available and we have multiple candidates, use it to pick best
        if self.llm and len(candidates) > 1:
            return await self._llm_rank_candidates(candidates, goal, instruction)
        
        # Otherwise return highest scored
        return candidates[0] if candidates[0].score > 0.5 else None
    
    async def _llm_rank_candidates(
        self, 
        candidates: List[LinkCandidate], 
        goal: TaskGoal, 
        instruction: str
    ) -> Optional[LinkCandidate]:
        """Use LLM to pick the best candidate"""
        
        # Prepare candidates for LLM
        candidates_text = "\n".join([
            f"{i+1}. URL: {c.url}\n   Text: {c.text}\n   Location: {c.location}\n   Score: {c.score:.1f}"
            for i, c in enumerate(candidates[:5])
        ])
        
        prompt = f"""Pick the best link for this goal:

Goal: {goal.value}
User wants: {instruction}

Candidates:
{candidates_text}

Return ONLY the number (1-5) of the best matching link, or 0 if none match well."""

        try:
            response = await self.llm.generate(prompt)
            choice = int(response.strip())
            if 1 <= choice <= len(candidates):
                return candidates[choice - 1]
        except Exception as e:
            logger.debug(f"LLM ranking failed: {e}")
        
        # Fallback to highest score
        return candidates[0] if candidates[0].score > 0.5 else None
    
    async def try_direct_url_patterns(self, base_url: str, goal: TaskGoal) -> Optional[str]:
        """
        Try common URL patterns directly without parsing the page.
        Includes path patterns and subdomain patterns.
        """
        from urllib.parse import urlparse
        
        parsed = urlparse(base_url)
        domain = parsed.netloc.replace('www.', '')
        scheme = parsed.scheme or 'https'
        
        # Path patterns to try
        path_patterns = {
            TaskGoal.FIND_CONTACT_FORM: ["/kontakt", "/contact", "/contact-us", "/help", "/support", "/pomoc"],
            TaskGoal.FIND_CART: ["/koszyk", "/cart", "/basket", "/bag", "/checkout"],
            TaskGoal.FIND_LOGIN: ["/login", "/logowanie", "/signin", "/account/login", "/konto", "/zaloguj"],
            TaskGoal.FIND_REGISTER: ["/register", "/rejestracja", "/signup", "/account/create", "/zaloz-konto"],
            TaskGoal.FIND_FAQ: ["/faq", "/help", "/pomoc", "/pytania", "/centrum-pomocy", "/faq.html"],
            TaskGoal.FIND_HELP: ["/help", "/pomoc", "/support", "/wsparcie", "/centrum-pomocy"],
            TaskGoal.FIND_SHIPPING: [
                "/dostawa", "/shipping", "/delivery", "/wysylka", "/koszty-dostawy",
                "/informacje/dostawa", "/info/dostawa", "/lp,dostawa", "/s,dostawa",
                "/cms/dostawa", "/strona/dostawa", "/page/shipping"
            ],
            TaskGoal.FIND_RETURNS: ["/zwroty", "/returns", "/return-policy", "/reklamacje", "/odstapienie"],
            TaskGoal.FIND_WARRANTY: ["/gwarancja", "/warranty", "/serwis", "/naprawa"],
            TaskGoal.FIND_TERMS: ["/regulamin", "/terms", "/warunki", "/zasady", "/tos"],
            TaskGoal.FIND_PRIVACY: ["/privacy", "/prywatnosc", "/polityka-prywatnosci", "/rodo"],
            TaskGoal.FIND_ABOUT: ["/o-nas", "/about", "/about-us", "/firma", "/o-firmie"],
            TaskGoal.FIND_CAREERS: ["/kariera", "/careers", "/praca", "/jobs", "/oferty-pracy", "/rekrutacja"],
            TaskGoal.FIND_BLOG: ["/blog", "/articles", "/artykuly", "/poradnik", "/aktualnosci", "/news"],
            TaskGoal.FIND_STORES: ["/sklepy", "/stores", "/lokalizacje", "/salony", "/punkty-sprzedazy"],
            TaskGoal.FIND_ACCOUNT: ["/konto", "/account", "/moje-konto", "/profil", "/panel"],
        }
        
        # Subdomain patterns (for careers, help, etc.)
        subdomain_patterns = {
            TaskGoal.FIND_CAREERS: ["kariera", "careers", "praca", "jobs"],
            TaskGoal.FIND_HELP: ["help", "pomoc", "support"],
            TaskGoal.FIND_CONTACT_FORM: ["kontakt", "help", "pomoc"],
        }
        
        # Try path patterns first
        for pattern in path_patterns.get(goal, []):
            test_url = f"{scheme}://{parsed.netloc.rstrip('/')}{pattern}"
            try:
                response = await self.page.goto(test_url, timeout=5000, wait_until="domcontentloaded")
                if response and response.status < 400:
                    logger.info(f"Direct URL pattern worked: {test_url}")
                    return test_url
            except Exception:
                continue
        
        # Try subdomain patterns
        for subdomain in subdomain_patterns.get(goal, []):
            test_url = f"{scheme}://{subdomain}.{domain}"
            try:
                response = await self.page.goto(test_url, timeout=5000, wait_until="domcontentloaded")
                if response and response.status < 400:
                    logger.info(f"Subdomain pattern worked: {test_url}")
                    return test_url
            except Exception:
                continue
        
        return None


# Convenience function
async def find_url_with_llm(
    page, 
    goal: TaskGoal, 
    instruction: str, 
    llm_client=None
) -> Optional[LinkCandidate]:
    """Find URL using LLM-guided search"""
    resolver = LLMUrlResolver(page, llm_client)
    return await resolver.find_url_for_goal(goal, instruction)
