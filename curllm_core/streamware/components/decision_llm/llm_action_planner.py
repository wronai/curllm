from typing import Any, Dict, List, Optional

from .llm_field_analyzer import LLMFieldAnalyzer

class LLMActionPlanner:
    """
    LLM-driven action planner - plans form filling actions without hardcoded selectors.
    """
    
    def __init__(self, llm=None):
        self.llm = llm
        self.field_analyzer = LLMFieldAnalyzer(llm)
    
    async def plan_next_action(
        self,
        instruction: str,
        form_analysis: Dict,
        history: List[Dict]
    ) -> Dict[str, Any]:
        """
        Plan the next action using LLM.
        
        Args:
            instruction: User instruction
            form_analysis: Current form state
            history: Previous actions
            
        Returns:
            Action dict with type and parameters
        """
        if not self.llm:
            return self._plan_heuristic(instruction, form_analysis, history)
        
        try:
            prompt = f"""Plan the next form filling action.

Instruction: "{instruction}"
Form state: {form_analysis}
Previous actions: {len(history)} actions taken

What should be done next? Respond with JSON:
{{"type": "fill|click|wait|complete", "selector": "...", "value": "...", "reason": "..."}}"""

            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            import json
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.debug(f"LLM action planning failed: {e}")
        
        return self._plan_heuristic(instruction, form_analysis, history)
    
    def _plan_heuristic(
        self,
        instruction: str,
        form_analysis: Dict,
        history: List[Dict]
    ) -> Dict[str, Any]:
        """Fallback heuristic planning."""
        # Check for loops
        if len(history) >= 2 and history[-1] == history[-2]:
            return {'type': 'wait', 'duration': 500, 'reason': 'avoid_loop'}
        
        forms = form_analysis.get('forms', [])
        if not forms:
            return {'type': 'complete', 'reason': 'no_forms'}
        
        form = forms[0]
        if form.get('completion_rate', 0) >= 1.0:
            return {'type': 'click', 'selector': 'button, input[type="submit"]', 'action': 'submit'}
        
        # Find next unfilled field
        for field in form.get('fields', []):
            if not field.get('value'):
                return {
                    'type': 'fill',
                    'selector': f"[name='{field.get('name')}']",
                    'field': field.get('name'),
                }
        
        return {'type': 'complete', 'reason': 'all_filled'}
