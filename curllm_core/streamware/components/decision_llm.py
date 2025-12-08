"""
LLM-Driven Decision Components - No hardcoded field lists

Uses LLM to:
1. Detect fillable fields without hardcoded type lists
2. Extract field values from instructions using NLU
3. Plan form filling actions intelligently
"""

import logging
from typing import Any, Dict, List, Optional

from ..core import Component
from ..registry import register
from ..exceptions import ComponentError

logger = logging.getLogger(__name__)


class LLMFieldAnalyzer:
    """
    LLM-driven field analyzer - no hardcoded field types or names.
    """
    
    def __init__(self, llm=None):
        self.llm = llm
    
    async def is_fillable_field(self, field: Dict) -> bool:
        """
        Use LLM to determine if a field is fillable.
        
        Falls back to simple heuristics when LLM unavailable.
        """
        if not self.llm:
            return self._is_fillable_heuristic(field)
        
        try:
            field_info = {
                'type': field.get('type', 'text'),
                'name': field.get('name', ''),
                'id': field.get('id', ''),
                'placeholder': field.get('placeholder', ''),
            }
            
            prompt = f"""Is this form field meant for user text input?

Field: {field_info}

Respond with just: YES or NO"""

            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return 'YES' in content.upper()
        except Exception:
            return self._is_fillable_heuristic(field)
    
    def _is_fillable_heuristic(self, field: Dict) -> bool:
        """Fallback heuristic for fillable detection."""
        field_type = field.get('type', 'text').lower()
        # Common input types that accept text
        return field_type in ['text', 'email', 'tel', 'textarea', 'password', 
                               'search', 'url', 'number']
    
    async def extract_fields_from_instruction(
        self, 
        instruction: str,
        available_fields: List[Dict]
    ) -> Dict[str, str]:
        """
        Use LLM to extract field values from natural language instruction.
        
        Args:
            instruction: User's instruction (e.g., "Fill with name John, email john@test.com")
            available_fields: List of field dicts from the form
            
        Returns:
            Dict mapping field names to values
        """
        if not self.llm:
            return self._extract_fields_heuristic(instruction)
        
        try:
            field_names = [f.get('name') or f.get('id') or f.get('placeholder', '') 
                          for f in available_fields]
            
            prompt = f"""Extract form field values from this instruction.

Instruction: "{instruction}"

Available form fields: {field_names}

Extract any values the user wants to fill. Respond with JSON:
{{"field_name": "value", ...}}

Only include fields where you can clearly identify a value."""

            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            import json
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.debug(f"LLM field extraction failed: {e}")
        
        return self._extract_fields_heuristic(instruction)
    
    def _extract_fields_heuristic(self, instruction: str) -> Dict[str, str]:
        """Fallback heuristic for field extraction."""
        fields = {}
        
        # Simple key=value parsing
        parts = instruction.replace(':', '=').split(',')
        for part in parts:
            if '=' in part:
                key_val = part.split('=', 1)
                if len(key_val) == 2:
                    key = key_val[0].strip().lower()
                    val = key_val[1].strip()
                    if key and val:
                        fields[key] = val
        
        return fields


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


@register("decision-llm")
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
