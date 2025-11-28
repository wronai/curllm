"""
BQL Utilities - Helper functions for BQL operations.
"""
import re
from typing import Optional


def parse_bql(query: str) -> str:
    """
    Parse BQL query and convert to natural language instruction.
    
    Args:
        query: BQL query string
        
    Returns:
        Natural language instruction
    """
    if "query" in query and "{" in query:
        return f"Extract the following fields from the page: {query}"
    return query


def normalize_query(query: str) -> str:
    """
    Normalize a BQL query string.
    
    - Remove comments
    - Normalize whitespace
    - Trim
    
    Args:
        query: Raw query string
        
    Returns:
        Normalized query string
    """
    # Remove single-line comments
    query = re.sub(r'#[^\n]*\n', '\n', query)
    # Remove multi-line comments
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    # Normalize whitespace
    query = re.sub(r'\s+', ' ', query)
    return query.strip()


def extract_selectors(query: str) -> list:
    """
    Extract CSS selectors from a BQL query.
    
    Args:
        query: BQL query string
        
    Returns:
        List of CSS selectors found
    """
    selectors = []
    
    # Find css: "..." patterns
    css_pattern = r'css:\s*["\']([^"\']+)["\']'
    matches = re.findall(css_pattern, query)
    selectors.extend(matches)
    
    # Find selector: "..." patterns
    sel_pattern = r'selector:\s*["\']([^"\']+)["\']'
    matches = re.findall(sel_pattern, query)
    selectors.extend(matches)
    
    return selectors


def validate_query(query: str) -> tuple:
    """
    Validate a BQL query syntax.
    
    Args:
        query: BQL query string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    query = normalize_query(query)
    
    if not query:
        return False, "Empty query"
    
    # Check for balanced braces
    brace_count = 0
    for char in query:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        if brace_count < 0:
            return False, "Unbalanced braces: extra closing brace"
    
    if brace_count != 0:
        return False, f"Unbalanced braces: {brace_count} unclosed"
    
    # Check for balanced parentheses
    paren_count = 0
    for char in query:
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        if paren_count < 0:
            return False, "Unbalanced parentheses: extra closing paren"
    
    if paren_count != 0:
        return False, f"Unbalanced parentheses: {paren_count} unclosed"
    
    return True, None


def build_extraction_query(
    url: str,
    container_selector: str,
    fields: dict
) -> str:
    """
    Build a BQL extraction query.
    
    Args:
        url: Page URL
        container_selector: CSS selector for containers
        fields: Dict of field_name -> selector
        
    Returns:
        BQL query string
    """
    field_lines = []
    for name, selector in fields.items():
        field_lines.append(f'        {name}: text(css: "{selector}")')
    
    fields_block = "\n".join(field_lines)
    
    return f'''query {{
    page(url: "{url}") {{
        items: select(css: "{container_selector}") {{
{fields_block}
        }}
    }}
}}'''


def build_mutation_query(actions: list) -> str:
    """
    Build a BQL mutation query.
    
    Args:
        actions: List of action dicts with type, selector, value
        
    Returns:
        BQL mutation string
    """
    action_lines = []
    for action in actions:
        action_type = action.get("type", "click")
        selector = action.get("selector", "")
        
        if action_type == "fill":
            value = action.get("value", "")
            action_lines.append(f'    fill(selector: "{selector}", value: "{value}")')
        elif action_type == "click":
            action_lines.append(f'    click(selector: "{selector}")')
        elif action_type == "navigate":
            url = action.get("url", "")
            action_lines.append(f'    navigate(url: "{url}")')
        elif action_type == "wait":
            duration = action.get("duration", 1000)
            action_lines.append(f'    wait(duration: {duration})')
    
    actions_block = "\n".join(action_lines)
    
    return f'''mutation {{
{actions_block}
}}'''
