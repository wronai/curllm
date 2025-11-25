"""
Base Tool class for curllm tool orchestration system.

Each tool:
- Has a JSON manifest describing its interface
- Implements execute() method
- Returns typed output matching schema
- Can be composed with other tools
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import json
from pathlib import Path


class BaseTool(ABC):
    """Abstract base class for all curllm tools"""
    
    def __init__(self):
        self.manifest = self._load_manifest()
        self.name = self.manifest.get("name", self.__class__.__name__)
        self.version = self.manifest.get("version", "1.0.0")
        self.category = self.manifest.get("category", "unknown")
        self.description = self.manifest.get("description", "")
        self.param_schema = self.manifest.get("parameters", {})
        self.output_schema = self.manifest.get("output_schema", {})
        
    def _load_manifest(self) -> Dict[str, Any]:
        """Load tool manifest from JSON file"""
        # Get manifest path relative to tool module
        module_path = Path(__file__).parent
        tool_file = Path(self.__class__.__module__.replace('.', '/') + '.py')
        manifest_path = tool_file.with_suffix('.json')
        
        try:
            if manifest_path.exists():
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load manifest for {self.__class__.__name__}: {e}")
        
        # Return minimal manifest if file not found
        return {
            "name": self.__class__.__name__,
            "version": "1.0.0",
            "category": "unknown",
            "description": "No manifest available",
            "parameters": {},
            "output_schema": {}
        }
    
    @abstractmethod
    async def execute(self, page, parameters: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.
        
        Args:
            page: Playwright page object
            parameters: Tool parameters (validated against schema)
            context: Optional context from previous tools in pipeline
            
        Returns:
            Dict matching output_schema from manifest
        """
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate parameters against schema (basic implementation)"""
        schema = self.param_schema
        if not schema:
            return True
            
        props = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Check required fields
        for field in required:
            if field not in parameters:
                raise ValueError(f"Missing required parameter: {field}")
        
        # Basic type checking
        for key, value in parameters.items():
            if key in props:
                expected_type = props[key].get("type")
                if expected_type == "number" and not isinstance(value, (int, float)):
                    raise ValueError(f"Parameter {key} must be number, got {type(value)}")
                elif expected_type == "string" and not isinstance(value, str):
                    raise ValueError(f"Parameter {key} must be string, got {type(value)}")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    raise ValueError(f"Parameter {key} must be boolean, got {type(value)}")
        
        return True
    
    def get_manifest(self) -> Dict[str, Any]:
        """Return tool manifest for registry"""
        return self.manifest
    
    def matches_trigger(self, instruction: str) -> bool:
        """Check if tool matches instruction based on triggers"""
        import re
        triggers = self.manifest.get("triggers", [])
        instruction_lower = instruction.lower()
        
        for trigger in triggers:
            if re.search(trigger, instruction_lower, re.IGNORECASE):
                return True
        return False
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} v{self.version}: {self.description}>"
