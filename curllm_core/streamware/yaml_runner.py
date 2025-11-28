"""
YAML Flow Runner - Execute Streamware pipelines from YAML files

Allows defining pipelines in YAML format for easy configuration and reuse.
"""

import yaml
import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from .flow import flow, Flow
from .patterns import split, join, multicast, choose
from .registry import create_component
from .exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


class YAMLFlowRunner:
    """
    Execute Streamware flows from YAML configuration
    
    YAML Format:
        name: "Pipeline Name"
        description: "Pipeline description"
        input:
          type: "json"
          data: {...}
        steps:
          - component: "curllm://browse"
            params:
              url: "https://example.com"
              stealth: true
          - component: "transform://csv"
          - component: "file://write"
            params:
              path: "/tmp/output.csv"
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize YAML flow runner
        
        Args:
            config: Optional global configuration
        """
        self.config = config or {}
        self.variables = {}
        
    def load_yaml(self, path: str) -> Dict[str, Any]:
        """
        Load YAML flow definition from file
        
        Args:
            path: Path to YAML file
            
        Returns:
            Parsed YAML as dictionary
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Replace variables
            content = self._replace_variables(content)
            
            return yaml.safe_load(content)
            
        except FileNotFoundError:
            raise ComponentError(f"YAML file not found: {path}")
        except yaml.YAMLError as e:
            raise ComponentError(f"Invalid YAML format: {e}")
            
    def set_variable(self, name: str, value: Any):
        """Set a variable for template replacement"""
        self.variables[name] = value
        
    def set_variables(self, variables: Dict[str, Any]):
        """Set multiple variables"""
        self.variables.update(variables)
        
    def _replace_variables(self, content: str) -> str:
        """Replace ${VAR} placeholders with variable values"""
        for name, value in self.variables.items():
            placeholder = f"${{{name}}}"
            content = content.replace(placeholder, str(value))
        return content
        
    def build_flow(self, spec: Dict[str, Any]) -> Flow:
        """
        Build Flow from YAML specification
        
        Args:
            spec: YAML flow specification
            
        Returns:
            Constructed Flow object
        """
        if 'steps' not in spec or not spec['steps']:
            raise ComponentError("Flow specification must contain 'steps'")
            
        steps = spec['steps']
        
        # Build URI for first step
        first_step = steps[0]
        first_uri = self._build_uri(first_step)
        
        # Create flow
        pipeline = flow(first_uri)
        
        # Add input data if specified
        if 'input' in spec:
            input_spec = spec['input']
            if 'data' in input_spec:
                pipeline = pipeline.with_data(input_spec['data'])
                
        # Add diagnostics if specified
        if spec.get('diagnostics', False):
            pipeline = pipeline.with_diagnostics(trace=spec.get('trace', False))
            
        # Add remaining steps
        for step in steps[1:]:
            step_uri = self._build_uri(step)
            pipeline = pipeline | step_uri
            
        return pipeline
        
    def _build_uri(self, step: Dict[str, Any]) -> str:
        """
        Build URI string from step specification
        
        Args:
            step: Step specification
            
        Returns:
            URI string
        """
        component = step.get('component')
        if not component:
            raise ComponentError("Step must have 'component' field")
            
        # If component is already a full URI, return it
        if '://' in component:
            uri = component
        else:
            # Build URI from parts
            scheme = step.get('scheme', component)
            operation = step.get('operation', '')
            uri = f"{scheme}://{operation}" if operation else f"{scheme}://"
            
        # Add parameters
        params = step.get('params', {})
        if params:
            param_str = '&'.join(f"{k}={v}" for k, v in params.items())
            uri += f"?{param_str}" if '?' not in uri else f"&{param_str}"
            
        return uri
        
    def run_yaml(self, path: str, input_data: Any = None) -> Any:
        """
        Load and execute YAML flow
        
        Args:
            path: Path to YAML file
            input_data: Optional input data (overrides YAML input)
            
        Returns:
            Flow execution result
        """
        spec = self.load_yaml(path)
        
        logger.info(f"Running YAML flow: {spec.get('name', 'Unnamed')}")
        if 'description' in spec:
            logger.info(f"Description: {spec['description']}")
            
        pipeline = self.build_flow(spec)
        
        # Override input data if provided
        if input_data is not None:
            pipeline = pipeline.with_data(input_data)
            
        return pipeline.run()
        
    def run_yaml_stream(self, path: str, input_stream: Any = None):
        """
        Load and execute YAML flow in streaming mode
        
        Args:
            path: Path to YAML file
            input_stream: Optional input stream
            
        Yields:
            Stream results
        """
        spec = self.load_yaml(path)
        pipeline = self.build_flow(spec)
        
        yield from pipeline.stream(input_stream)
        
    def validate_yaml(self, path: str) -> bool:
        """
        Validate YAML flow syntax
        
        Args:
            path: Path to YAML file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            spec = self.load_yaml(path)
            
            # Check required fields
            if 'steps' not in spec:
                logger.error("Missing 'steps' field")
                return False
                
            if not isinstance(spec['steps'], list):
                logger.error("'steps' must be a list")
                return False
                
            if len(spec['steps']) == 0:
                logger.error("'steps' cannot be empty")
                return False
                
            # Validate each step
            for i, step in enumerate(spec['steps']):
                if not isinstance(step, dict):
                    logger.error(f"Step {i} must be a dictionary")
                    return False
                    
                if 'component' not in step:
                    logger.error(f"Step {i} missing 'component' field")
                    return False
                    
            logger.info(f"YAML flow validation passed: {path}")
            return True
            
        except Exception as e:
            logger.error(f"YAML validation error: {e}")
            return False


def run_yaml_flow(path: str, input_data: Any = None, variables: Dict[str, Any] = None) -> Any:
    """
    Quick helper to run YAML flow
    
    Args:
        path: Path to YAML file
        input_data: Optional input data
        variables: Optional variables for template replacement
        
    Returns:
        Flow execution result
    """
    runner = YAMLFlowRunner()
    
    if variables:
        runner.set_variables(variables)
        
    return runner.run_yaml(path, input_data)


def validate_yaml_flow(path: str) -> bool:
    """
    Quick helper to validate YAML flow
    
    Args:
        path: Path to YAML file
        
    Returns:
        True if valid
    """
    runner = YAMLFlowRunner()
    return runner.validate_yaml(path)
