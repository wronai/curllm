"""
Decision Tree Components - Modular decision-making for browser automation

This module implements the hierarchical planning system as reusable Streamware components.
"""

from typing import Any, Dict, List, Optional
from ..core import Component
from ..uri import StreamwareURI
from ..registry import register
from ..exceptions import ComponentError
from ...diagnostics import get_logger

logger = get_logger(__name__)


@register("dom-analyze")
class DOMAnalyzeComponent(Component):
    """
    Analyze DOM structure and extract relevant information
    
    URI: dom-analyze://extract?type=forms|links|text|structure
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Dict[str, Any]:
        """Analyze DOM data"""
        analysis_type = self.uri.get_param('type', 'forms')
        
        if not isinstance(data, dict):
            raise ComponentError("Input must be a dictionary")
        
        # Accept either {'page_context': {...}} or the page_context directly
        # This allows chaining with dom-snapshot which returns data directly
        if 'page_context' in data:
            page_context = data['page_context']
        elif 'forms' in data or 'title' in data or 'url' in data:
            # Data looks like a page context itself
            page_context = data
        else:
            raise ComponentError("Input must contain 'page_context' or be a page context dict")
        
        if analysis_type == 'forms':
            return self._analyze_forms(page_context)
        elif analysis_type == 'links':
            return self._analyze_links(page_context)
        elif analysis_type == 'text':
            return self._analyze_text(page_context)
        elif analysis_type == 'structure':
            return self._analyze_structure(page_context)
        else:
            raise ComponentError(f"Unknown analysis type: {analysis_type}")
            
    def _analyze_forms(self, context: Dict) -> Dict[str, Any]:
        """Analyze form fields and their states"""
        forms = context.get('forms', [])
        
        analyzed_forms = []
        for form in forms:
            fields = form.get('fields', [])
            
            # Group fields by type and analyze completeness
            fillable_fields = [f for f in fields if f.get('type') in ['text', 'email', 'tel', 'textarea']]
            filled_fields = [f for f in fillable_fields if f.get('value')]
            
            analyzed_forms.append({
                'form_id': form.get('id'),
                'total_fields': len(fillable_fields),
                'filled_fields': len(filled_fields),
                'completion_rate': len(filled_fields) / len(fillable_fields) if fillable_fields else 0,
                'fields': fillable_fields,
                'has_submit': any(f.get('type') == 'submit' for f in fields)
            })
            
        return {
            'forms': analyzed_forms,
            'has_forms': len(analyzed_forms) > 0,
            'all_filled': all(f['completion_rate'] == 1.0 for f in analyzed_forms)
        }
        
    def _analyze_links(self, context: Dict) -> Dict[str, Any]:
        """Analyze links on the page"""
        links = context.get('links', [])
        
        return {
            'total_links': len(links),
            'internal_links': [l for l in links if not l.get('external', False)],
            'external_links': [l for l in links if l.get('external', False)],
        }
        
    def _analyze_text(self, context: Dict) -> Dict[str, Any]:
        """Analyze text content"""
        text = context.get('text', '')
        
        return {
            'text_length': len(text),
            'has_content': len(text) > 100,
            'word_count': len(text.split())
        }
        
    def _analyze_structure(self, context: Dict) -> Dict[str, Any]:
        """Analyze page structure"""
        return {
            'title': context.get('title', ''),
            'url': context.get('url', ''),
            'has_forms': len(context.get('forms', [])) > 0,
            'has_links': len(context.get('links', [])) > 0
        }


@register("action-plan")
class ActionPlanComponent(Component):
    """
    Plan next action based on instruction and page state
    
    URI: action-plan://decide?strategy=sequential|smart|llm
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Dict[str, Any]:
        """Plan next action"""
        if not isinstance(data, dict):
            raise ComponentError("Input must be a dictionary")
            
        instruction = data.get('instruction', '')
        page_analysis = data.get('page_analysis', {})
        history = data.get('history', [])
        strategy = self.uri.get_param('strategy', 'sequential')
        
        if strategy == 'sequential':
            return self._plan_sequential(instruction, page_analysis, history)
        elif strategy == 'smart':
            return self._plan_smart(instruction, page_analysis, history)
        elif strategy == 'llm':
            return self._plan_llm(instruction, page_analysis, history)
        else:
            raise ComponentError(f"Unknown strategy: {strategy}")
            
    def _plan_sequential(self, instruction: str, analysis: Dict, history: List) -> Dict:
        """Plan actions sequentially based on instruction"""
        # Extract required fields from instruction
        required_fields = self._extract_fields_from_instruction(instruction)
        
        # Get form analysis
        forms = analysis.get('forms', [])
        if not forms:
            return {'type': 'complete', 'reason': 'no_forms_found'}
            
        form = forms[0]
        fields = form.get('fields', [])
        
        # Find next unfilled field
        for field in fields:
            field_name = field.get('name', '')
            field_value = field.get('value', '')
            
            # Check if this field needs to be filled
            for req_field, req_value in required_fields.items():
                if req_field.lower() in field_name.lower() and not field_value:
                    return {
                        'type': 'fill',
                        'selector': f"[name='{field_name}']",
                        'value': req_value,
                        'field': req_field
                    }
                    
        # All fields filled, submit
        if form.get('has_submit'):
            return {
                'type': 'click',
                'selector': 'button[type="submit"], input[type="submit"]',
                'action': 'submit'
            }
            
        return {'type': 'complete', 'reason': 'all_fields_filled'}
        
    def _plan_smart(self, instruction: str, analysis: Dict, history: List) -> Dict:
        """Smart planning with history awareness"""
        # Check for repeated actions
        if len(history) >= 2:
            last_two = history[-2:]
            if last_two[0] == last_two[1]:
                logger.warning("Repeated action detected, trying alternative")
                return {'type': 'wait', 'duration': 500, 'reason': 'avoid_loop'}
                
        # Use sequential but with loop detection
        action = self._plan_sequential(instruction, analysis, history)
        
        # Add action to history check
        action['_history_check'] = True
        
        return action
        
    def _plan_llm(self, instruction: str, analysis: Dict, history: List) -> Dict:
        """LLM-based planning (delegates to LLM)"""
        # This would call the LLM planner
        return {
            'type': 'delegate_llm',
            'instruction': instruction,
            'analysis': analysis,
            'history': history
        }
        
    def _extract_fields_from_instruction(self, instruction: str) -> Dict[str, str]:
        """Extract field values from instruction - NO REGEX, simple parsing"""
        fields = {}
        
        # Simple key=value parsing without regex
        parts = instruction.replace(':', '=').split(',')
        for part in parts:
            if '=' in part:
                key_val = part.split('=', 1)
                if len(key_val) == 2:
                    key = key_val[0].strip().lower()
                    val = key_val[1].strip()
                    # Only accept known field names
                    if key in ['name', 'email', 'phone', 'subject', 'message', 
                               'first_name', 'last_name', 'company', 'address']:
                        fields[key] = val
                
        return fields


@register("action-validate")
class ActionValidateComponent(Component):
    """
    Validate if action was successfully executed
    
    URI: action-validate://check?type=fill|click|navigation
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Dict[str, Any]:
        """Validate action execution"""
        if not isinstance(data, dict):
            raise ComponentError("Input must be dictionary")
            
        action = data.get('action', {})
        before_state = data.get('before_state', {})
        after_state = data.get('after_state', {})
        
        validation_type = self.uri.get_param('type', action.get('type', 'fill'))
        
        if validation_type == 'fill':
            return self._validate_fill(action, before_state, after_state)
        elif validation_type == 'click':
            return self._validate_click(action, before_state, after_state)
        elif validation_type == 'navigation':
            return self._validate_navigation(action, before_state, after_state)
        else:
            return {'success': True, 'validated': False, 'reason': 'unknown_type'}
            
    def _validate_fill(self, action: Dict, before: Dict, after: Dict) -> Dict:
        """Validate fill action"""
        selector = action.get('selector', '')
        expected_value = action.get('value', '')
        
        # Extract field name from selector - simple parsing without regex
        field_name = self._extract_name_from_selector(selector)
            
        if not field_name:
            return {'success': False, 'reason': 'cannot_parse_selector'}
        
        # Check if field value changed in after_state
        after_forms = after.get('forms', [])
        for form in after_forms:
            for field in form.get('fields', []):
                if field.get('name') == field_name:
                    actual_value = field.get('value', '')
                    success = actual_value == expected_value or len(actual_value) > 0
                    
                    return {
                        'success': success,
                        'field': field_name,
                        'expected': expected_value,
                        'actual': actual_value,
                        'validated': True
                    }
                    
        return {'success': False, 'reason': 'field_not_found', 'validated': False}
        
    def _validate_click(self, action: Dict, before: Dict, after: Dict) -> Dict:
        """Validate click action"""
        # Check URL change or DOM change
        url_changed = before.get('url') != after.get('url')
        
        return {
            'success': True,  # Clicks usually succeed if no error
            'url_changed': url_changed,
            'validated': True
        }
    
    def _extract_name_from_selector(self, selector: str) -> Optional[str]:
        """Extract field name from CSS selector without regex"""
        # Handle [name='value'] pattern
        if "name='" in selector:
            start = selector.find("name='") + 6
            end = selector.find("'", start)
            if end > start:
                return selector[start:end]
        
        # Handle [name=value] pattern (without quotes)
        if "name=" in selector:
            start = selector.find("name=") + 5
            end = selector.find("]", start)
            if end > start:
                return selector[start:end].strip("'\"")
        
        # Handle #id pattern
        if selector.startswith("#"):
            return selector[1:].split()[0]
        
        return None
        
    def _validate_navigation(self, action: Dict, before: Dict, after: Dict) -> Dict:
        """Validate navigation"""
        expected_url = action.get('url', '')
        actual_url = after.get('url', '')
        
        return {
            'success': expected_url in actual_url or actual_url == expected_url,
            'expected_url': expected_url,
            'actual_url': actual_url,
            'validated': True
        }


@register("decision-tree")
class DecisionTreeComponent(Component):
    """
    Complete decision tree for browser automation
    
    URI: decision-tree://execute?max_steps=10&strategy=smart
    
    This is a meta-component that coordinates the entire decision-making process.
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Dict[str, Any]:
        """Execute decision tree"""
        from ..flow import flow
        
        if not isinstance(data, dict):
            raise ComponentError("Input must be dictionary")
            
        instruction = data.get('instruction', '')
        page_context = data.get('page_context', {})
        max_steps = self.uri.get_param('max_steps', 10)
        strategy = self.uri.get_param('strategy', 'smart')
        
        history = []
        step = 0
        
        while step < max_steps:
            # Step 1: Analyze DOM
            analysis = (
                flow("dom-analyze://extract?type=forms")
                .with_data({'page_context': page_context})
                .run()
            )
            
            # Step 2: Plan action
            plan_data = {
                'instruction': instruction,
                'page_analysis': analysis,
                'history': history
            }
            
            action = (
                flow(f"action-plan://decide?strategy={strategy}")
                .with_data(plan_data)
                .run()
            )
            
            # Check if complete
            if action.get('type') == 'complete':
                return {
                    'success': True,
                    'steps': step,
                    'reason': action.get('reason'),
                    'history': history
                }
                
            # Add to history
            history.append(action)
            
            # Here would execute action and get new page_context
            # (skipped in this component as it needs browser integration)
            
            step += 1
            
        return {
            'success': False,
            'reason': 'max_steps_reached',
            'steps': step,
            'history': history
        }
