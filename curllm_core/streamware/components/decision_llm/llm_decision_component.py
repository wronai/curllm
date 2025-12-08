import logging
from typing import Any, Dict, List, Optional
from ...core import Component
from ...registry import register
from ...exceptions import ComponentError

from .llm_field_analyzer import LLMFieldAnalyzer
from .llm_action_planner import LLMActionPlanner

class LLMDecisionComponent(Component):
    """
    LLM-driven decision making component.
    
    URI: decision-llm://plan?mode=form|navigate|extract
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri, llm=None, **kwargs):
        super().__init__(uri, **kwargs)
        self.llm = llm
        self.planner = LLMActionPlanner(llm)
        self.field_analyzer = LLMFieldAnalyzer(llm)
    
    def process(self, data: Any) -> Dict[str, Any]:
        """Process synchronously (for async, use process_async)."""
        # Return delegate action for async processing
        return {
            'type': 'delegate_async',
            'component': 'decision-llm',
            'data': data
        }
    
    async def process_async(self, data: Any) -> Dict[str, Any]:
        """Process with LLM asynchronously."""
        mode = self.uri.get_param('mode', 'form')
        
        if mode == 'form':
            return await self._process_form(data)
        else:
            return {'type': 'unknown_mode', 'mode': mode}
    
    async def _process_form(self, data: Dict) -> Dict[str, Any]:
        """Process form filling decision."""
        instruction = data.get('instruction', '')
        form_analysis = data.get('analysis', {})
        history = data.get('history', [])
        
        action = await self.planner.plan_next_action(instruction, form_analysis, history)
        
        return {
            'action': action,
            'confidence': 0.8 if self.llm else 0.5,
            'method': 'llm' if self.llm else 'heuristic'
        }
