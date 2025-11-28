"""
Dynamic Tool Registry - generates tool definitions from actual function signatures.
No hardcoded JSON - uses inspect module to read real function definitions.
"""
import inspect
from typing import Dict, Any, Callable, get_type_hints

from .detect import detect_form, detect_forms, get_field_selectors
from .fill import fill_field, fill_fields
from .submit import (
    submit_form, 
    get_clickable_buttons, 
    detect_success,
    capture_page_state,
    detect_success_data
)


# Tool functions mapping - dynamically generated from actual functions
TOOL_FUNCTIONS: Dict[str, Callable] = {
    "form.detect": detect_form,
    "form.detect_all": detect_forms,
    "form.fields": get_field_selectors,
    "form.fill_field": fill_field,
    "form.fill_fields": fill_fields,
    "form.buttons": get_clickable_buttons,
    "form.submit": submit_form,
    "form.capture_state": capture_page_state,
    "form.check_success": detect_success_data,
}


def get_function_signature(func: Callable) -> Dict[str, Any]:
    """Extract function signature dynamically."""
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    
    # Get first line of docstring as description
    description = doc.split("\n")[0] if doc else func.__name__
    
    # Extract parameters (skip 'page' as it's internal)
    args = {}
    for name, param in sig.parameters.items():
        if name == "page":
            continue
        
        # Get type annotation
        annotation = param.annotation
        type_str = "any"
        if annotation != inspect.Parameter.empty:
            if hasattr(annotation, "__name__"):
                type_str = annotation.__name__
            elif hasattr(annotation, "_name"):
                type_str = str(annotation._name)
            else:
                type_str = str(annotation)
        
        # Check if optional
        is_optional = param.default != inspect.Parameter.empty
        
        args[name] = {
            "type": type_str,
            "optional": is_optional,
            "default": str(param.default) if param.default != inspect.Parameter.empty else None
        }
    
    # Extract return type
    try:
        hints = get_type_hints(func)
        return_hint = hints.get("return", Any)
        return_str = str(return_hint) if return_hint else "Dict"
    except Exception:
        return_str = "Dict"
    
    return {
        "description": description,
        "args": args,
        "returns": return_str
    }


def generate_tool_registry() -> Dict[str, Dict[str, Any]]:
    """Generate tool registry dynamically from function signatures."""
    registry = {}
    for tool_name, func in TOOL_FUNCTIONS.items():
        registry[tool_name] = get_function_signature(func)
    return registry


def get_tools_prompt() -> str:
    """Generate LLM prompt describing available tools."""
    registry = generate_tool_registry()
    lines = ["Atomic form tools (call individually for fine control):"]
    
    for name, info in registry.items():
        args_parts = []
        for arg_name, arg_info in info["args"].items():
            opt = "?" if arg_info.get("optional") else ""
            args_parts.append(f"{arg_name}{opt}: {arg_info['type']}")
        
        args_str = ", ".join(args_parts) if args_parts else "none"
        lines.append(f"- {name}({args_str}): {info['description']}")
    
    lines.append("")
    lines.append("Use: {\"type\": \"tool\", \"tool_name\": \"form.xxx\", \"args\": {...}}")
    
    return "\n".join(lines)


async def execute_tool(
    page,
    tool_name: str,
    args: Dict[str, Any],
    logger=None
) -> Dict[str, Any]:
    """
    Execute an atomic tool.
    
    Args:
        page: Playwright page
        tool_name: Tool name (e.g., "form.detect")
        args: Tool arguments
        logger: Optional logger
    
    Returns:
        Tool result dict
    """
    def log(msg):
        if logger:
            logger.log_text(f"[{tool_name}] {msg}")
    
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return {"error": f"Unknown tool: {tool_name}"}
    
    try:
        log(f"Executing with args: {args}")
        
        # Get function signature to know what args it expects
        sig = inspect.signature(func)
        params = sig.parameters
        
        # Build kwargs from provided args, filtering only expected params
        kwargs = {}
        for param_name in params:
            if param_name == "page":
                continue
            if param_name in args:
                kwargs[param_name] = args[param_name]
        
        # Call function
        result = await func(page, **kwargs)
        log(f"Result: {result}")
        return result
        
    except Exception as e:
        log(f"Error: {e}")
        return {"error": str(e)}


# Generate at import time for introspection
FORM_ATOMIC_TOOLS = generate_tool_registry()
