#!/usr/bin/env python3
"""
Simplified DSL Prompt Format for Smaller LLM Models

Instead of JSON, uses Python-like syntax that simpler models can understand:

Example DSL output:
    action = "fill"
    field = "email"
    value = "john@example.com"
    reason = "Fill email field with provided value"

Or for tools:
    action = "tool"
    tool_name = "form.fill"
    args = dict(name="John Doe", email="john@example.com")
    reason = "Fill form with user data"

This format is:
1. More readable for humans
2. Easier for small models to generate (no JSON escaping issues)
3. Can be parsed with simple regex
"""

import re
import json
from typing import Any, Dict, Optional, List
from .config import config


def format_prompt_response_instructions(use_dsl: bool = None) -> str:
    """
    Get response format instructions based on config.
    
    Args:
        use_dsl: Override config setting (None = use config)
        
    Returns:
        Instructions for LLM about response format
    """
    if use_dsl is None:
        use_dsl = config.prompt_format == "dsl"
    
    if use_dsl:
        return '''
Response format (Python-like DSL - NO JSON):

action = "click" | "fill" | "scroll" | "wait" | "complete" | "tool"
selector = "CSS selector" (if applicable)
value = "text value" (if applicable)
tool_name = "tool name" (if action is "tool")
args = dict(key="value", ...) (if action is "tool")
extracted_data = dict(key="value", ...) (if action is "complete")
reason = "brief explanation"

Example for form filling:
    action = "tool"
    tool_name = "form.fill"
    args = dict(name="John Doe", email="john@example.com", message="Hello")
    reason = "Fill contact form with user data"

Example for completion:
    action = "complete"
    extracted_data = dict(submitted=True)
    reason = "Form submitted successfully"
'''
    else:
        return '''
Response (JSON only):
{
    "type": "click|fill|scroll|wait|complete|tool",
    "selector": "CSS selector if applicable",
    "value": "value to fill if applicable",
    "tool_name": "if type=tool, name of the tool",
    "args": "if type=tool, arguments object",
    "extracted_data": "data if task is complete",
    "reason": "brief explanation of your decision"
}
'''


def parse_dsl_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Parse DSL format response from LLM into structured dict.
    
    Args:
        response: LLM response in DSL format
        
    Returns:
        Parsed action dict or None if parsing fails
    """
    result = {}
    
    # Clean response - remove markdown code blocks if present
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    
    # Parse key = value patterns
    patterns = [
        # action = "value"
        (r'^\s*action\s*=\s*["\']([^"\']+)["\']', 'type'),
        # selector = "value"
        (r'^\s*selector\s*=\s*["\']([^"\']+)["\']', 'selector'),
        # value = "value"
        (r'^\s*value\s*=\s*["\']([^"\']+)["\']', 'value'),
        # tool_name = "value"
        (r'^\s*tool_name\s*=\s*["\']([^"\']+)["\']', 'tool_name'),
        # reason = "value"
        (r'^\s*reason\s*=\s*["\']([^"\']+)["\']', 'reason'),
    ]
    
    for line in response.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
            
        for pattern, key in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                result[key] = match.group(1)
                break
        
        # Parse args = dict(...) or args = {...}
        if line.lower().startswith("args"):
            args_match = re.search(r'args\s*=\s*(?:dict\s*)?\(([^)]+)\)', line, re.IGNORECASE)
            if args_match:
                args_str = args_match.group(1)
                result['args'] = _parse_dict_args(args_str)
            else:
                # Try JSON-like format
                args_match = re.search(r'args\s*=\s*\{([^}]+)\}', line, re.IGNORECASE)
                if args_match:
                    try:
                        result['args'] = json.loads("{" + args_match.group(1) + "}")
                    except:
                        result['args'] = _parse_dict_args(args_match.group(1))
        
        # Parse extracted_data = dict(...) or extracted_data = {...}
        if line.lower().startswith("extracted_data"):
            data_match = re.search(r'extracted_data\s*=\s*(?:dict\s*)?\(([^)]+)\)', line, re.IGNORECASE)
            if data_match:
                result['extracted_data'] = _parse_dict_args(data_match.group(1))
            else:
                data_match = re.search(r'extracted_data\s*=\s*\{([^}]+)\}', line, re.IGNORECASE)
                if data_match:
                    try:
                        result['extracted_data'] = json.loads("{" + data_match.group(1) + "}")
                    except:
                        result['extracted_data'] = _parse_dict_args(data_match.group(1))
    
    # Validate required field
    if not result.get('type'):
        return None
    
    return result


def _parse_dict_args(args_str: str) -> Dict[str, Any]:
    """Parse key=value pairs from dict-like string."""
    result = {}
    
    # Split by comma, handling quoted values
    parts = re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\w+))', args_str)
    
    for part in parts:
        key = part[0]
        # Get value from whichever group matched
        value = part[1] or part[2] or part[3]
        
        # Try to convert to appropriate type
        if value.lower() == "true":
            result[key] = True
        elif value.lower() == "false":
            result[key] = False
        elif value.isdigit():
            result[key] = int(value)
        else:
            result[key] = value
    
    return result


def format_action_as_dsl(action: Dict[str, Any]) -> str:
    """
    Format an action dict as DSL for logging/display.
    
    Args:
        action: Action dictionary
        
    Returns:
        DSL formatted string
    """
    lines = []
    
    action_type = action.get('type', 'unknown')
    lines.append(f'action = "{action_type}"')
    
    if action.get('selector'):
        lines.append(f'selector = "{action["selector"]}"')
    
    if action.get('value'):
        lines.append(f'value = "{action["value"]}"')
    
    if action.get('tool_name'):
        lines.append(f'tool_name = "{action["tool_name"]}"')
    
    if action.get('args'):
        args_str = ", ".join(f'{k}="{v}"' for k, v in action['args'].items())
        lines.append(f'args = dict({args_str})')
    
    if action.get('extracted_data'):
        data_str = ", ".join(f'{k}="{v}"' for k, v in action['extracted_data'].items())
        lines.append(f'extracted_data = dict({data_str})')
    
    if action.get('reason'):
        lines.append(f'reason = "{action["reason"]}"')
    
    return "\n".join(lines)


def parse_response_auto(response: str) -> Optional[Dict[str, Any]]:
    """
    Automatically detect and parse response format (JSON or DSL).
    
    Args:
        response: LLM response string
        
    Returns:
        Parsed action dict or None
    """
    response = response.strip()
    
    # Try JSON first
    try:
        # Look for JSON object
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError:
        pass
    
    # Try DSL format
    dsl_result = parse_dsl_response(response)
    if dsl_result:
        return dsl_result
    
    # Last resort: try to extract action from text
    action_match = re.search(r'action\s*[:=]\s*["\']?(\w+)', response, re.IGNORECASE)
    if action_match:
        return {'type': action_match.group(1).lower()}
    
    return None


# Atomic task templates for form filling
ATOMIC_FORM_TASKS = {
    "detect_form": '''
Task: Detect if page has a contact/form to fill
Context: {context}

Question: Is there a form on this page that can be filled?
Answer with: yes/no and form_id if found

Response:
    has_form = True | False
    form_id = "form-id" | None
    form_type = "contact" | "login" | "register" | "search" | "other"
''',
    
    "map_fields": '''
Task: Map user data to form fields
User data: {user_data}
Form fields: {form_fields}

Question: Which form fields should receive which values?

Response:
    mappings = dict(
        email = "field_selector",
        name = "field_selector",
        message = "field_selector"
    )
''',
    
    "fill_field": '''
Task: Fill a single form field
Field: {field_name} ({field_type})
Value to fill: {value}
Selector: {selector}

Question: Should this field be filled with this value?

Response:
    fill = True | False
    reason = "explanation"
''',
    
    "submit_form": '''
Task: Submit the form
Submit button: {submit_selector}
Pre-check: {validation_status}

Question: Is the form ready to submit?

Response:
    ready = True | False
    issues = [] | ["issue1", "issue2"]
'''
}


def get_atomic_prompt(task_type: str, **kwargs) -> str:
    """
    Get atomic task prompt with filled placeholders.
    
    Args:
        task_type: One of ATOMIC_FORM_TASKS keys
        **kwargs: Values to fill in template
        
    Returns:
        Formatted prompt string
    """
    template = ATOMIC_FORM_TASKS.get(task_type, "")
    if not template:
        return ""
    
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
