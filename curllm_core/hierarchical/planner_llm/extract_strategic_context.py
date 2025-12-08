import json
import logging
from typing import Any, Dict, List, Optional

def extract_strategic_context(page_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract strategic context (stateless, no LLM needed).
    """
    forms = page_context.get("forms", [])
    
    return {
        "title": page_context.get("title", ""),
        "url": page_context.get("url", ""),
        "page_type": _detect_page_type(page_context),
        "form_count": len(forms),
        "interactive_count": len(page_context.get("interactive", [])),
        "has_forms": len(forms) > 0,
    }

def _detect_page_type(page_context: Dict[str, Any]) -> str:
    """Detect page type from context structure."""
    if page_context.get("forms"):
        return "form"
    if page_context.get("article_candidates"):
        return "article_list"
    if page_context.get("products"):
        return "product_list"
    return "unknown"
