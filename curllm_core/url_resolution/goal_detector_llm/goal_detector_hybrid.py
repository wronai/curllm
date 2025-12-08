import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from curllm_core.url_types import TaskGoal

from .goal_detection_result import GoalDetectionResult

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
        
        For async contexts, use detect_goal() instead.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Can't run async in running loop, use fallback
                return self._detect_goal_heuristic(instruction)
            return loop.run_until_complete(self.detect_goal(instruction))
        except RuntimeError:
            return self._detect_goal_heuristic(instruction)
    
    async def detect_goal(self, instruction: str) -> GoalDetectionResult:
        """
        Detect user's navigation goal using LLM.
        
        Args:
            instruction: User's instruction text
            
        Returns:
            GoalDetectionResult with detected goal and confidence
        """
        if not self.llm:
            return self._detect_goal_heuristic(instruction)
        
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
        
        return self._detect_goal_heuristic(instruction)
    
    def _map_goal_name(self, goal_name: str) -> TaskGoal:
        """Map goal name string to TaskGoal enum."""
        mapping = {
            'FIND_PRODUCTS': TaskGoal.FIND_PRODUCTS,
            'FIND_CART': TaskGoal.FIND_CART,
            'FIND_LOGIN': TaskGoal.FIND_LOGIN,
            'FIND_REGISTER': TaskGoal.FIND_REGISTER,
            'FIND_CONTACT_FORM': TaskGoal.FIND_CONTACT_FORM,
            'FIND_SHIPPING': TaskGoal.FIND_SHIPPING,
            'FIND_RETURNS': TaskGoal.FIND_RETURNS,
            'FIND_FAQ': TaskGoal.FIND_FAQ,
            'FIND_HELP': TaskGoal.FIND_HELP,
            'NAVIGATE_TO_CATEGORY': TaskGoal.NAVIGATE_TO_CATEGORY,
            'SEARCH_FOR_PRODUCTS': TaskGoal.SEARCH_FOR_PRODUCTS,
        }
        return mapping.get(goal_name, TaskGoal.OTHER)
    
    def _detect_goal_heuristic(self, instruction: str) -> GoalDetectionResult:
        """
        Fallback heuristic detection (used when LLM unavailable).
        
        Note: This uses simple patterns but should rarely be needed
        as LLM detection is preferred.
        """
        instr_lower = instruction.lower()
        
        # Very simple heuristics - LLM is preferred
        if any(w in instr_lower for w in ['cart', 'koszyk', 'basket']):
            return GoalDetectionResult(TaskGoal.FIND_CART, 0.6)
        if any(w in instr_lower for w in ['login', 'zaloguj', 'sign in']):
            return GoalDetectionResult(TaskGoal.FIND_LOGIN, 0.6)
        if any(w in instr_lower for w in ['contact', 'kontakt', 'message']):
            return GoalDetectionResult(TaskGoal.FIND_CONTACT_FORM, 0.6)
        if any(w in instr_lower for w in ['product', 'produkt', 'item', 'buy']):
            return GoalDetectionResult(TaskGoal.FIND_PRODUCTS, 0.5)
        
        return GoalDetectionResult(TaskGoal.OTHER, 0.3)
