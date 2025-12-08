"""
Hybrid Selector Ranking System

Combines algorithmic scoring with LLM validation for transparent, intelligent selector choice.

Architecture:
1. Algorithm generates candidates + scores (fast, deterministic)
2. LLM validates top candidates (semantic understanding)
3. Final decision combines both (transparent reasoning)
"""

from typing import Dict, List, Optional, Any
import json


class HybridSelectorRanker:
    """
    Hybrid ranking: Algorithm + LLM validation
    
    Provides full transparency:
    - Algorithmic scores with breakdown
    - LLM reasoning for top candidates
    - Combined decision with explanation
    """
    
    def __init__(self, llm_client, run_logger=None):
        self.llm = llm_client
        self.run_logger = run_logger
    
    def _log(self, msg: str, data: Any = None):
        """Log with structured data"""
        if self.run_logger:
            if data:
                self.run_logger.log_substep(msg, data)
            else:
                self.run_logger.log_substep(msg)
    
    async def rank_candidates(
        self,
        candidates: List[Dict[str, Any]],
        page_context: str,
        instruction: str,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Rank selector candidates with hybrid approach
        
        Args:
            candidates: List of {selector, score, specificity, ...}
            page_context: Sample HTML/text from page
            instruction: User's extraction goal
            use_llm: Whether to use LLM validation (default True)
        
        Returns:
            {
                "winner": {...},
                "algorithm_choice": {...},
                "llm_choice": {...} if use_llm,
                "reasoning": "...",
                "score_breakdown": {...},
                "transparency": {...}
            }
        """
        
        if not candidates:
            return {"error": "No candidates to rank"}
        
        # Sort by algorithmic score
        candidates_sorted = sorted(candidates, key=lambda c: c.get("score", 0), reverse=True)
        algo_winner = candidates_sorted[0]
        
        self._log("🤖 Algorithm Ranking", {
            "top_3": [
                {
                    "selector": c["selector"],
                    "score": c.get("score", 0),
                    "specificity": c.get("specificity", 0)
                }
                for c in candidates_sorted[:3]
            ]
        })
        
        # If not using LLM, return algorithmic choice
        if not use_llm:
            return {
                "winner": algo_winner,
                "algorithm_choice": algo_winner,
                "llm_choice": None,
                "reasoning": "Algorithm-only (LLM disabled)",
                "method": "algorithm_only"
            }
        
        # Get LLM validation for top candidates
        top_candidates = candidates_sorted[:3]  # Top 3 for LLM review
        
        llm_result = await self._llm_validate_candidates(
            top_candidates,
            page_context,
            instruction
        )
        
        # Combine decisions
        final_decision = self._combine_decisions(
            algo_winner,
            llm_result,
            candidates_sorted
        )
        
        self._log("🎯 Final Decision", final_decision)
        
        return final_decision
    
    async def _llm_validate_candidates(
        self,
        candidates: List[Dict],
        page_context: str,
        instruction: str
    ) -> Dict[str, Any]:
        """
        Ask LLM to validate and rank top candidates
        
        Provides semantic understanding that pure algorithm lacks.
        """
        
        # Prepare candidates for LLM
        candidates_text = "\n".join([
            f"{i+1}. {c['selector']}\n"
            f"   - Algorithmic Score: {c.get('score', 0):.1f}\n"
            f"   - Specificity: {c.get('specificity', 0)} classes\n"
            f"   - Count: {c.get('count', 0)} elements\n"
            f"   - Sample Text: {c.get('sample_text', '')[:100]}...\n"
            for i, c in enumerate(candidates)
        ])
        
        prompt = f"""You are analyzing product container selectors for web extraction.

INSTRUCTION: {instruction}

PAGE CONTEXT (sample):
{page_context[:500]}

ALGORITHM DETECTED THESE TOP CANDIDATES:
{candidates_text}

Your task:
1. Analyze each candidate semantically (not just by score)
2. Consider:
   - Does the sample text look like actual products?
   - Is the selector specific enough (not too generic)?
   - Does it match the instruction context?
3. Choose the BEST selector for extracting products

Respond with JSON:
{{
  "recommended_selector": "<selector>",
  "reasoning": "<explain why this is best>",
  "concerns": ["<any concerns about algorithm's choice>"],
  "confidence": <0.0-1.0>,
  "agrees_with_algorithm": <true/false>
}}

JSON only:"""

        try:
            response = await self.llm.generate(prompt, temperature=0.3)
            
            # Parse LLM response
            llm_data = json.loads(response.strip().replace("```json", "").replace("```", ""))
            
            self._log("🧠 LLM Validation", llm_data)
            
            return {
                "recommended_selector": llm_data.get("recommended_selector"),
                "reasoning": llm_data.get("reasoning", ""),
                "concerns": llm_data.get("concerns", []),
                "confidence": llm_data.get("confidence", 0.5),
                "agrees_with_algorithm": llm_data.get("agrees_with_algorithm", True),
                "raw_response": llm_data
            }
            
        except Exception as e:
            self._log(f"⚠️ LLM validation failed: {e}")
            return {
                "error": str(e),
                "recommended_selector": None,
                "reasoning": "LLM validation failed",
                "confidence": 0.0
            }
    
    def _combine_decisions(
        self,
        algo_winner: Dict,
        llm_result: Dict,
        all_candidates: List[Dict]
    ) -> Dict[str, Any]:
        """
        Combine algorithmic and LLM decisions with transparency
        
        Rules:
        1. If LLM agrees with algorithm → use algorithm (fast, reliable)
        2. If LLM disagrees but low confidence → use algorithm (trust math)
        3. If LLM disagrees with high confidence → use LLM (semantic override)
        """
        
        llm_selector = llm_result.get("recommended_selector")
        llm_confidence = llm_result.get("confidence", 0.5)
        agrees = llm_result.get("agrees_with_algorithm", True)
        
        # Case 1: LLM agrees or failed
        if agrees or not llm_selector or llm_result.get("error"):
            return {
                "winner": algo_winner,
                "algorithm_choice": algo_winner,
                "llm_choice": llm_result,
                "method": "algorithm_validated_by_llm" if agrees else "algorithm_only",
                "reasoning": (
                    f"Algorithm choice validated by LLM. {llm_result.get('reasoning', '')}"
                    if agrees else
                    "Algorithm choice used (LLM unavailable or agreed)"
                ),
                "transparency": {
                    "llm_agreed": agrees,
                    "llm_confidence": llm_confidence,
                    "decision_maker": "algorithm"
                }
            }
        
        # Case 2: LLM disagrees but low confidence
        if llm_confidence < 0.7:
            return {
                "winner": algo_winner,
                "algorithm_choice": algo_winner,
                "llm_choice": llm_result,
                "method": "algorithm_over_llm_low_confidence",
                "reasoning": (
                    f"Algorithm choice used despite LLM disagreement "
                    f"(LLM confidence only {llm_confidence:.1%}). "
                    f"LLM concerns: {llm_result.get('concerns', [])}"
                ),
                "transparency": {
                    "llm_agreed": False,
                    "llm_confidence": llm_confidence,
                    "decision_maker": "algorithm",
                    "override_reason": "llm_confidence_too_low"
                }
            }
        
        # Case 3: LLM disagrees with high confidence → OVERRIDE
        llm_winner = next(
            (c for c in all_candidates if c["selector"] == llm_selector),
            None
        )
        
        if not llm_winner:
            # LLM suggested selector not in candidates?
            return {
                "winner": algo_winner,
                "algorithm_choice": algo_winner,
                "llm_choice": llm_result,
                "method": "algorithm_fallback",
                "reasoning": (
                    f"LLM suggested '{llm_selector}' but not in candidates. "
                    f"Using algorithm choice."
                ),
                "transparency": {
                    "llm_agreed": False,
                    "llm_confidence": llm_confidence,
                    "decision_maker": "algorithm",
                    "override_reason": "llm_selector_not_found"
                }
            }
        
        return {
            "winner": llm_winner,
            "algorithm_choice": algo_winner,
            "llm_choice": llm_result,
            "method": "llm_override",
            "reasoning": (
                f"LLM override: {llm_result.get('reasoning', '')} "
                f"(Confidence: {llm_confidence:.1%}). "
                f"Algorithm suggested '{algo_winner['selector']}' "
                f"but LLM prefers '{llm_selector}' for semantic reasons."
            ),
            "transparency": {
                "llm_agreed": False,
                "llm_confidence": llm_confidence,
                "decision_maker": "llm",
                "override_reason": "llm_high_confidence_disagreement",
                "algo_score": algo_winner.get("score", 0),
                "llm_score": llm_winner.get("score", 0),
                "score_difference": abs(
                    algo_winner.get("score", 0) - llm_winner.get("score", 0)
                )
            }
        }
    
    def get_score_breakdown(self, candidate: Dict) -> Dict[str, float]:
        """
        Generate transparent score breakdown
        
        Shows exactly how score was calculated (for transparency).
        """
        breakdown = {}
        score = 0
        
        # Specificity
        specificity = candidate.get("specificity", 0)
        if specificity >= 3:
            breakdown["specificity"] = 50
            score += 50
        elif specificity >= 2:
            breakdown["specificity"] = 35
            score += 35
        elif specificity >= 1:
            breakdown["specificity"] = 20
            score += 20
        
        # Utility class penalty
        first_class = (candidate.get("classes", "") or "").split()[0]
        utility_prefixes = ['mt-', 'mb-', 'p-', 'flex', 'grid', 'border-']
        generic_layouts = ['container', 'row', 'col', 'wrapper', 'inner']
        
        is_utility = any(first_class.startswith(p) for p in utility_prefixes)
        is_generic = first_class in generic_layouts
        
        if is_utility or is_generic:
            breakdown["utility_penalty"] = -30
            score -= 30
        
        # Size
        count = candidate.get("count", 0)
        size_score = min(count / 50, 1) * 15
        breakdown["size"] = round(size_score, 1)
        score += size_score
        
        # Structure
        breakdown["has_price"] = 25 if candidate.get("has_price") else 0
        breakdown["has_link"] = 20 if candidate.get("has_link") else 0
        breakdown["has_image"] = 15 if candidate.get("has_image") else 0
        score += breakdown["has_price"] + breakdown["has_link"] + breakdown["has_image"]
        
        # Text quality
        text = candidate.get("sample_text", "").lower()
        
        if any(kw in text for kw in ["laptop", "phone", "notebook"]):
            breakdown["product_keywords"] = 15
            score += 15
        
        if any(spec in text for spec in ["gb", "ghz", "core", "ryzen"]):
            breakdown["specs"] = 20
            score += 20
        
        if any(noise in text for noise in ["okazja", "promocja", "rabat"]):
            breakdown["marketing_penalty"] = -15
            score -= 15
        
        # Complete structure
        if all([candidate.get("has_price"), candidate.get("has_link"), candidate.get("has_image")]):
            breakdown["complete_structure"] = 10
            score += 10
        
        breakdown["total"] = round(score, 1)
        
        return breakdown
