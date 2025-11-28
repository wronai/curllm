"""
Progressive Context Builder - Smart Context Expansion

Instead of sending 60KB from start, we:
1. Step 1-2: Minimal context (~5KB) - title, url, top links
2. Step 3-4: Add interactive (~15KB) - buttons, forms
3. Step 5-6: Add structure (~30KB) - DOM preview
4. Step 7+: Full context (~60KB+) - everything

Only expand when previous attempts failed.
"""

import json
from typing import Dict, Any, Optional


def _is_form_task(instruction: str) -> bool:
    """Check if the instruction is a form-related task"""
    if not instruction:
        return False
    instruction_lower = instruction.lower()
    form_keywords = [
        "fill", "form", "submit", "login", "register", "signup", "sign up",
        "contact", "email", "name=", "formularz", "wypełnij", "logowanie",
        "wyślij", "kontakt", "rejestr"
    ]
    result = any(kw in instruction_lower for kw in form_keywords)
    return result


def build_progressive_context(
    page_context: Dict[str, Any],
    step: int,
    instruction: str
) -> Dict[str, Any]:
    """
    Build progressively larger context based on step number.
    
    Args:
        page_context: Full page context from extract_page_context
        step: Current step number (1-based)
        instruction: User instruction
        
    Returns:
        Filtered page context appropriate for this step
    """
    
    # Always include basics
    minimal = {
        "title": page_context.get("title", ""),
        "url": page_context.get("url", ""),
    }
    
    # Check if this is a form task - if so, ALWAYS include forms data
    is_form_task = _is_form_task(instruction)
    
    # For form tasks: ALWAYS include form data regardless of step
    # This is critical - without forms, LLM cannot fill the form!
    if is_form_task:
        forms = page_context.get("forms", [])
        if forms:
            # Include full form details for form-filling tasks
            minimal["forms"] = forms[:3]
        
        # Also include interactive elements that could be form fields
        interactive = page_context.get("interactive", [])
        if interactive:
            # Filter to form-related elements
            form_elements = [
                el for el in interactive 
                if el.get("tag") in ["input", "textarea", "select", "button", "form"]
                or "form" in str(el.get("attrs", {}).get("class", "")).lower()
                or "forminator" in str(el.get("attrs", {}).get("id", "")).lower()
                or "forminator" in str(el.get("attrs", {}).get("class", "")).lower()
            ]
            if form_elements:
                minimal["interactive"] = form_elements[:30]
        
        # Add buttons for submit detection
        buttons = page_context.get("buttons", [])
        if buttons:
            minimal["buttons"] = buttons[:10]
    
    # Step 1-2: Minimal context (title, url, top links/headings)
    if step <= 2:
        headings = page_context.get("headings", [])
        links = page_context.get("links", [])
        
        minimal["headings"] = headings[:5] if headings else []
        # For form tasks, we don't need links - skip them to save tokens
        if not is_form_task:
            minimal["links"] = links[:10] if links else []
        
        # Add hint about what's available
        minimal["_hint"] = "Minimal context. More details available if needed."
        minimal["_step"] = step
        minimal["_is_form_task"] = is_form_task  # Debug flag
        
        return minimal
    
    # Step 3-4: Add interactive elements (buttons, forms basics)
    elif step <= 4:
        progressive = minimal.copy()
        
        headings = page_context.get("headings", [])
        links = page_context.get("links", [])
        buttons = page_context.get("buttons", [])
        forms = page_context.get("forms", [])
        
        progressive["headings"] = headings[:10] if headings else []
        progressive["links"] = links[:20] if links else []
        progressive["buttons"] = buttons[:10] if buttons else []
        
        # Simplified forms - just actions and field count
        if forms:
            progressive["forms"] = [
                {
                    "action": f.get("action"),
                    "field_count": len(f.get("fields", [])),
                    "has_submit": any(
                        fld.get("type") in ["submit", "button"] 
                        for fld in f.get("fields", [])
                    )
                }
                for f in forms[:3]
            ]
        
        progressive["_hint"] = "Basic context with interactive elements. DOM structure available if needed."
        progressive["_step"] = step
        
        return progressive
    
    # Step 5-6: Add structure (DOM preview, more links)
    elif step <= 6:
        expanded = minimal.copy()
        
        headings = page_context.get("headings", [])
        links = page_context.get("links", [])
        buttons = page_context.get("buttons", [])
        forms = page_context.get("forms", [])
        interactive = page_context.get("interactive", [])
        dom_preview = page_context.get("dom_preview", "")
        
        expanded["headings"] = headings[:15] if headings else []
        expanded["links"] = links[:30] if links else []
        expanded["buttons"] = buttons[:15] if buttons else []
        expanded["forms"] = forms[:3] if forms else []
        expanded["interactive"] = interactive[:20] if interactive else []
        
        # Add DOM preview (limited)
        if dom_preview:
            expanded["dom_preview"] = dom_preview[:15000]  # Max 15KB
        
        expanded["_hint"] = "Expanded context with structure. Full details available if needed."
        expanded["_step"] = step
        
        return expanded
    
    # Step 7+: Full context (fallback to original behavior)
    else:
        full = page_context.copy()
        full["_hint"] = "Full context mode"
        full["_step"] = step
        return full


def estimate_context_size(context: Dict[str, Any]) -> int:
    """Estimate size of context in characters"""
    try:
        return len(json.dumps(context, ensure_ascii=False))
    except Exception:
        return 0


def get_context_stats(context: Dict[str, Any]) -> Dict[str, Any]:
    """Get statistics about context"""
    return {
        "size_chars": estimate_context_size(context),
        "has_headings": bool(context.get("headings")),
        "heading_count": len(context.get("headings", [])),
        "has_links": bool(context.get("links")),
        "link_count": len(context.get("links", [])),
        "has_forms": bool(context.get("forms")),
        "form_count": len(context.get("forms", [])),
        "has_dom": bool(context.get("dom_preview")),
        "has_interactive": bool(context.get("interactive")),
        "step": context.get("_step", 0)
    }


def should_expand_context(
    step: int,
    prev_action_type: Optional[str],
    stall_count: int
) -> bool:
    """
    Decide if we should expand context for next step.
    
    Rules:
    - If stalled 2+ times at same step level → expand
    - If prev action was "wait" or "scroll" → maybe expand
    - Early steps → keep minimal
    - Later steps → expand more aggressively
    
    Args:
        step: Current step number
        prev_action_type: Previous action type (click, wait, etc)
        stall_count: How many times we've made no progress
        
    Returns:
        True if should use larger context
    """
    # If stalling, expand faster
    if stall_count >= 2:
        return True
    
    # If previous action was wait/scroll (no clear progress), consider expanding
    if prev_action_type in ["wait", "scroll"] and step >= 3:
        return True
    
    # Default progression
    return False


# Example usage:
"""
# In task_runner.py:

from .progressive_context import build_progressive_context, get_context_stats

# Before building LLM prompt:
progressive_ctx = build_progressive_context(
    page_context=full_page_context,
    step=current_step,
    instruction=instruction
)

stats = get_context_stats(progressive_ctx)
run_logger.log_text(f"📊 Progressive Context: {stats['size_chars']} chars, step {stats['step']}, {stats['link_count']} links")

# Use progressive_ctx instead of full_page_context in prompt
"""
