"""
Tool Registry - auto-discovers and registers all available tools
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import importlib
import inspect
from .base import BaseTool


class ToolRegistry:
    """Global registry for curllm tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.by_category: Dict[str, List[str]] = {}
        
    def register(self, tool: BaseTool):
        """Register a tool instance"""
        name = tool.name
        if name in self.tools:
            print(f"Warning: Tool {name} already registered, overwriting")
        
        self.tools[name] = tool
        
        # Add to category index
        category = tool.category
        if category not in self.by_category:
            self.by_category[category] = []
        if name not in self.by_category[category]:
            self.by_category[category].append(name)
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def get_by_category(self, category: str) -> List[BaseTool]:
        """Get all tools in a category"""
        tool_names = self.by_category.get(category, [])
        return [self.tools[name] for name in tool_names if name in self.tools]
    
    def find_matching_tools(self, instruction: str, category: Optional[str] = None) -> List[BaseTool]:
        """Find tools that match instruction (based on triggers)"""
        candidates = []
        
        # Filter by category if specified
        if category:
            tools_to_check = self.get_by_category(category)
        else:
            tools_to_check = list(self.tools.values())
        
        for tool in tools_to_check:
            if tool.matches_trigger(instruction):
                candidates.append(tool)
        
        return candidates
    
    def list_all(self) -> List[str]:
        """List all registered tool names"""
        return list(self.tools.keys())
    
    def get_manifests(self) -> Dict[str, Dict[str, Any]]:
        """Get all tool manifests for LLM"""
        return {name: tool.get_manifest() for name, tool in self.tools.items()}
    
    def autodiscover(self, tools_dir: Optional[Path] = None):
        """Auto-discover and register all tools in tools directory"""
        if tools_dir is None:
            tools_dir = Path(__file__).parent
        
        print(f"🔍 Auto-discovering tools in {tools_dir}")
        
        # Scan all subdirectories
        categories = ['extraction', 'forms', 'navigation', 'validation']
        
        for category in categories:
            category_dir = tools_dir / category
            if not category_dir.exists():
                continue
            
            # Find all .py files (except __init__.py)
            for py_file in category_dir.glob('*.py'):
                if py_file.name.startswith('_'):
                    continue
                
                # Import module
                module_name = f"curllm_core.tools.{category}.{py_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    
                    # Find BaseTool subclasses
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseTool) and obj != BaseTool:
                            # Instantiate and register
                            tool_instance = obj()
                            self.register(tool_instance)
                            print(f"  ✅ Registered: {tool_instance.name} ({category})")
                
                except Exception as e:
                    print(f"  ⚠️  Failed to load {module_name}: {e}")
        
        print(f"✅ Registered {len(self.tools)} tools across {len(self.by_category)} categories")


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get global tool registry"""
    return _registry


def init_tools():
    """Initialize and auto-discover all tools"""
    _registry.autodiscover()
    return _registry
