"""
LLM-DSL Bridge - Enable LLM to communicate with Streamware components via JSON/YAML

This module allows the LLM to:
1. Generate JSON/YAML commands to control Streamware components
2. Receive structured responses from components
3. Make decisions based on component outputs
4. Chain multiple component calls to achieve goals
"""

import json
import yaml
from typing import Any, Dict, List, Optional, Union
from ..diagnostics import get_logger
from .flow import flow, Flow
from .registry import create_component, list_available_components
from .exceptions import ComponentError

logger = get_logger(__name__)



class LLMDSLBridge:
    """
    Bridge between LLM and Streamware DSL
    
    Enables LLM to:
    - Issue commands in JSON/YAML format
    - Execute Streamware components
    - Receive structured responses
    - Make multi-step decisions
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize LLM-DSL Bridge
        
        Args:
            llm_client: Optional LLM client for generating commands
        """
        self.llm_client = llm_client
        self.execution_history = []
        self.context = {}
        
    def execute_llm_command(self, command: Union[str, Dict]) -> Dict[str, Any]:
        """
        Execute a command from LLM in JSON/YAML format
        
        Args:
            command: JSON string, YAML string, or dict
            
        Returns:
            Execution result
            
        Example command (JSON):
            {
                "action": "analyze_form",
                "components": [
                    {"type": "dom-snapshot", "params": {"include_values": true}},
                    {"type": "dom-analyze", "params": {"type": "forms"}},
                    {"type": "field-mapper", "params": {"strategy": "fuzzy"}}
                ],
                "data": {"page": "<page_object>"}
            }
        """
        try:
            # Parse command
            if isinstance(command, str):
                try:
                    parsed = json.loads(command)
                except json.JSONDecodeError:
                    parsed = yaml.safe_load(command)
            else:
                parsed = command
                
            logger.info(f"Executing LLM command: {parsed.get('action', 'unknown')}")
            
            # Execute based on command type
            action = parsed.get('action')
            
            if action == 'analyze_form':
                return self._execute_analyze_form(parsed)
            elif action == 'fill_field':
                return self._execute_fill_field(parsed)
            elif action == 'extract_data':
                return self._execute_extract_data(parsed)
            elif action == 'validate_state':
                return self._execute_validate_state(parsed)
            elif action == 'plan_action':
                return self._execute_plan_action(parsed)
            elif action == 'execute_flow':
                return self._execute_flow(parsed)
            else:
                return self._execute_generic(parsed)
                
        except Exception as e:
            logger.error(f"LLM command execution error: {e}")
            return {
                'success': False,
                'error': str(e),
                'command': command
            }
            
    def _execute_analyze_form(self, command: Dict) -> Dict:
        """Execute form analysis workflow"""
        components = command.get('components', [])
        data = command.get('data', {})
        
        result = data
        for comp in components:
            comp_type = comp.get('type')
            params = comp.get('params', {})
            
            # Build URI
            uri = f"{comp_type}://"
            if params:
                param_str = '&'.join(f"{k}={v}" for k, v in params.items())
                uri += f"?{param_str}"
                
            # Execute component
            result = flow(uri).with_data(result).run()
            
        return {
            'success': True,
            'action': 'analyze_form',
            'result': result
        }
        
    def _execute_fill_field(self, command: Dict) -> Dict:
        """Execute field filling"""
        field = command.get('field')
        value = command.get('value')
        strategy = command.get('strategy', 'smart')
        
        # Execute action plan component
        result = flow(f"action-plan://decide?strategy={strategy}").with_data({
            'instruction': f"Fill {field} with {value}",
            'page_analysis': command.get('page_analysis', {}),
            'history': self.execution_history
        }).run()
        
        return {
            'success': True,
            'action': 'fill_field',
            'field': field,
            'value': value,
            'planned_action': result
        }
        
    def _execute_extract_data(self, command: Dict) -> Dict:
        """Execute data extraction"""
        extract_type = command.get('type', 'forms')
        page_context = command.get('page_context', {})
        
        result = flow(f"dom-analyze://extract?type={extract_type}").with_data({
            'page_context': page_context
        }).run()
        
        return {
            'success': True,
            'action': 'extract_data',
            'extracted': result
        }
        
    def _execute_validate_state(self, command: Dict) -> Dict:
        """Execute state validation"""
        validation_type = command.get('type', 'form_filled')
        snapshot = command.get('snapshot', {})
        expectations = command.get('expectations', {})
        
        result = flow(f"dom-validate://check?type={validation_type}").with_data({
            'snapshot': snapshot,
            'expectations': expectations
        }).run()
        
        return {
            'success': True,
            'action': 'validate_state',
            'validation': result
        }
        
    def _execute_plan_action(self, command: Dict) -> Dict:
        """Execute action planning"""
        instruction = command.get('instruction')
        page_analysis = command.get('page_analysis', {})
        strategy = command.get('strategy', 'smart')
        
        result = flow(f"action-plan://decide?strategy={strategy}").with_data({
            'instruction': instruction,
            'page_analysis': page_analysis,
            'history': self.execution_history
        }).run()
        
        return {
            'success': True,
            'action': 'plan_action',
            'plan': result
        }
        
    def _execute_flow(self, command: Dict) -> Dict:
        """Execute a complete Streamware flow"""
        steps = command.get('steps', [])
        initial_data = command.get('data', {})
        
        # Build flow from steps
        pipeline = None
        for step in steps:
            uri = step.get('uri') or self._build_uri_from_step(step)
            
            if pipeline is None:
                pipeline = flow(uri)
            else:
                pipeline = pipeline | uri
                
        # Execute with initial data
        result = pipeline.with_data(initial_data).run()
        
        return {
            'success': True,
            'action': 'execute_flow',
            'result': result
        }
        
    def _execute_generic(self, command: Dict) -> Dict:
        """Execute generic component call"""
        component_type = command.get('component')
        params = command.get('params', {})
        data = command.get('data', {})
        
        # Build URI
        uri = f"{component_type}://"
        if params:
            param_str = '&'.join(f"{k}={v}" for k, v in params.items())
            uri += f"?{param_str}"
            
        result = flow(uri).with_data(data).run()
        
        return {
            'success': True,
            'action': 'generic',
            'component': component_type,
            'result': result
        }
        
    def _build_uri_from_step(self, step: Dict) -> str:
        """Build URI from step definition"""
        component = step.get('component') or step.get('type')
        params = step.get('params', {})
        
        uri = f"{component}://"
        if params:
            param_str = '&'.join(f"{k}={v}" for k, v in params.items())
            uri += f"?{param_str}"
            
        return uri
        
    def generate_component_list(self) -> str:
        """Generate list of available components for LLM context"""
        components = list_available_components()
        
        component_docs = {
            'available_components': components,
            'examples': {
                'analyze_form': {
                    'action': 'analyze_form',
                    'components': [
                        {'type': 'dom-snapshot', 'params': {'include_values': True}},
                        {'type': 'dom-analyze', 'params': {'type': 'forms'}}
                    ]
                },
                'fill_field': {
                    'action': 'fill_field',
                    'field': 'email',
                    'value': 'test@example.com',
                    'strategy': 'smart'
                },
                'extract_data': {
                    'action': 'extract_data',
                    'type': 'forms',
                    'page_context': {}
                }
            }
        }
        
        return json.dumps(component_docs, indent=2)
        
    def get_llm_prompt_context(self) -> str:
        """Get context string for LLM prompts"""
        return f"""
You can control browser automation using JSON commands.

Available Actions:
1. analyze_form - Analyze form structure
2. fill_field - Fill a specific field
3. extract_data - Extract data from page
4. validate_state - Validate page state
5. plan_action - Plan next action
6. execute_flow - Execute complete workflow

Available Components:
{', '.join(list_available_components())}

Example Command (JSON):
{{
    "action": "analyze_form",
    "components": [
        {{"type": "dom-snapshot", "params": {{"include_values": true}}}},
        {{"type": "dom-analyze", "params": {{"type": "forms"}}}}
    ],
    "data": {{"page": "<page_object>"}}
}}

Example Command (YAML):
action: fill_field
field: email
value: test@example.com
strategy: smart

Always respond with valid JSON or YAML.
"""


# Convenience function
def execute_llm_dsl_command(command: Union[str, Dict]) -> Dict[str, Any]:
    """
    Quick execution of LLM DSL command
    
    Args:
        command: JSON/YAML string or dict
        
    Returns:
        Execution result
    """
    bridge = LLMDSLBridge()
    return bridge.execute_llm_command(command)
