#!/usr/bin/env python3
"""
Hierarchical LLM Planner - 3-level decision tree for reduced token usage.

Instead of sending 50KB+ DOM in one request, we break it into:
1. STRATEGIC level: ~2KB summary → what's on the page?
2. TACTICAL level: ~5KB details → what are the specifics?
3. EXECUTION level: Direct tool call (no LLM)

Example for "Fill contact form":
  Level 1: "Page has contact form with 4 fields" → decision: "use form"
  Level 2: "Form has: name, email, subject, message" → decision: "call form.fill"
  Level 3: Execute form.fill(...) directly (fastpath)
"""

from typing import Dict, Any, Optional, List
import json
from .config import config


def extract_strategic_context(page_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Level 1: Extract only high-level strategic information (~2KB).
    Creates 2-level JSON outline WITHOUT details like fields.
    
    Returns:
        {
            "title": str,
            "url": str,
            "page_type": "form" | "article_list" | "product_list" | "unknown",
            "has_forms": bool,
            "form_count": int,
            "form_outline": [  # 2-level outline without field details
                {
                    "id": str,
                    "field_count": int,
                    "field_types": {"text": int, "email": int, "textarea": int}
                }
            ],
            "has_articles": bool,
            "article_count": int,
            "interactive_count": int,
            "headings": List[str],  # Only h1, h2
        }
    """
    strategic = {
        "title": page_context.get("title", ""),
        "url": page_context.get("url", ""),
        "page_type": "unknown",
        "has_forms": False,
        "form_count": 0,
        "form_outline": [],
        "has_articles": False,
        "article_count": 0,
        "has_products": False,
        "interactive_count": len(page_context.get("interactive", [])),
    }
    
    # Detect page type and create 2-level form outline (without field details)
    forms = page_context.get("forms", [])
    if forms:
        strategic["has_forms"] = True
        strategic["form_count"] = len(forms)
        strategic["page_type"] = "form"
        
        # Create outline: count field types, don't include field details
        for form in forms[:3]:  # Max 3 forms
            field_types = {}
            for field in form.get("fields", []):
                ftype = field.get("type", "unknown")
                field_types[ftype] = field_types.get(ftype, 0) + 1
            
            strategic["form_outline"].append({
                "id": form.get("id", ""),
                "field_count": len(form.get("fields", [])),
                "field_types": field_types,
            })
    
    articles = page_context.get("article_candidates", [])
    if articles and len(articles) > 2:
        strategic["has_articles"] = True
        strategic["article_count"] = len(articles)
        if strategic["page_type"] == "unknown":
            strategic["page_type"] = "article_list"
    
    # Extract only h1 and h2 headings (skip h3-h6)
    headings = page_context.get("headings", [])
    strategic["headings"] = [
        h.get("text", "")[:50]  # Truncate to 50 chars
        for h in headings
        if h.get("tag") in ["h1", "h2"]
    ][:5]  # Max 5 headings
    
    return strategic


def extract_requested_details(page_context: Dict[str, Any], need_details: List[str]) -> Dict[str, Any]:
    """
    Extract only the details that LLM requested.
    
    Args:
        page_context: Full page context
        need_details: List of paths like ["forms[0].fields", "interactive"]
    
    Returns:
        Dict with only requested data
    """
    if not need_details:
        return {}
    
    result = {}
    
    for path in need_details:
        # Parse path like "forms[0].fields"
        if path.startswith("forms[") and "].fields" in path:
            try:
                idx = int(path.split("[")[1].split("]")[0])
                forms = page_context.get("forms", [])
                if idx < len(forms):
                    if "forms" not in result:
                        result["forms"] = []
                    # Include only fields for this form
                    result["forms"].append({
                        "id": forms[idx].get("id", ""),
                        "fields": forms[idx].get("fields", [])
                    })
            except Exception:
                pass
        elif path == "interactive":
            result["interactive"] = page_context.get("interactive", [])
        elif path == "headings":
            result["headings"] = page_context.get("headings", [])
    
    return result


def extract_tactical_form_context(page_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Level 2: Extract tactical details about forms (~5KB).
    
    Returns:
        {
            "forms": [
                {
                    "id": str,
                    "field_summary": {
                        "name": bool,
                        "email": bool,
                        "subject": bool,
                        "phone": bool,
                        "message": bool,
                    },
                    "required_fields": List[str],
                    "has_submit": bool,
                }
            ]
        }
    """
    forms = page_context.get("forms", [])
    tactical_forms = []
    
    for form in forms[:3]:  # Max 3 forms
        field_summary = {
            "name": False,
            "email": False,
            "subject": False,
            "phone": False,
            "message": False,
        }
        required_fields = []
        has_submit = False
        
        for field in form.get("fields", []):
            field_name = field.get("name", "").lower()
            field_type = field.get("type", "").lower()
            
            # Detect canonical fields
            if any(kw in field_name for kw in ["name", "imie", "nazwisko"]):
                field_summary["name"] = True
            elif any(kw in field_name for kw in ["email", "mail"]):
                field_summary["email"] = True
            elif any(kw in field_name for kw in ["subject", "temat"]):
                field_summary["subject"] = True
            elif any(kw in field_name for kw in ["phone", "tel"]):
                field_summary["phone"] = True
            elif any(kw in field_name for kw in ["message", "wiadomosc", "textarea"]):
                field_summary["message"] = True
            
            if field_type == "submit":
                has_submit = True
        
        tactical_forms.append({
            "id": form.get("id", ""),
            "field_summary": field_summary,
            "has_submit": has_submit,
        })
    
    return {"forms": tactical_forms}


def should_use_hierarchical_planner(instruction: str, page_context: Dict[str, Any]) -> bool:
    """
    Decide if hierarchical planner should be used.
    
    Criteria:
    - page_context size exceeds threshold (CURLLM_HIERARCHICAL_PLANNER_CHARS, default 25KB)
    - OR: Instruction contains form keywords AND page has forms
    """
    # Calculate context size
    try:
        context_size = len(json.dumps(page_context, ensure_ascii=False))
    except Exception:
        context_size = len(str(page_context))
    
    # If context is large, always use hierarchical planner
    threshold = config.hierarchical_planner_chars
    if context_size > threshold:
        return True
    
    # Otherwise, check if it's a form-filling task
    instruction_lower = instruction.lower()
    form_keywords = ["fill", "form", "formularz", "submit", "wyślij", "wyslij", "wypełnij", "wypelnij", "contact"]
    has_form_keywords = any(kw in instruction_lower for kw in form_keywords)
    
    has_forms = len(page_context.get("forms", [])) > 0
    
    # Debug info (would be logged if we had logger here)
    # print(f"DEBUG: context_size={context_size}, threshold={threshold}")
    # print(f"DEBUG: has_form_keywords={has_form_keywords}, has_forms={has_forms}")
    
    return has_form_keywords and has_forms


def generate_strategic_prompt(strategic_ctx: Dict[str, Any], instruction: str) -> str:
    """
    Generate Level 1 prompt (strategic decision).
    
    Example output:
        "The page is a contact form page with 1 form containing name, email, message fields."
    """
    # Format form outline for display
    form_summaries = []
    for form in strategic_ctx.get('form_outline', [])[:2]:
        field_types = ', '.join([f"{k}:{v}" for k, v in form['field_types'].items()])
        form_summaries.append(f"  - Form '{form['id']}': {form['field_count']} fields ({field_types})")
    
    prompt = f"""You are a browser automation expert analyzing a web page.

**User instruction:** {instruction}

**Page summary (2-level outline):**
- Title: {strategic_ctx['title']}
- URL: {strategic_ctx['url']}
- Page type: {strategic_ctx['page_type']}
- Has forms: {strategic_ctx['has_forms']} ({strategic_ctx['form_count']} forms)
{chr(10).join(form_summaries) if form_summaries else ''}
- Has articles: {strategic_ctx['has_articles']} ({strategic_ctx['article_count']} articles)
- Interactive elements: {strategic_ctx['interactive_count']}
- Main headings: {', '.join(strategic_ctx['headings'][:3])}

**Question:** What high-level action should be taken? What details do you need?

Return JSON with TWO fields:
{{
    "decision": "use_form" | "extract_articles" | "extract_links" | "complete",
    "need_details": ["forms[0].fields", "forms[1].fields"] | null,
    "reason": "brief explanation"
}}

If decision="use_form", specify which forms need field details in need_details.
If you have enough info, set need_details=null and proceed.
"""
    return prompt


def generate_tactical_prompt(tactical_ctx: Dict[str, Any], instruction: str, strategic_decision: str) -> str:
    """
    Generate Level 2 prompt (tactical decision).
    
    Example output:
        "Call form.fill with args: {{name, email, message}}"
    """
    # Format data based on what LLM received
    forms_summary = []
    for form in tactical_ctx.get("forms", [])[:2]:  # Max 2 forms
        # Check if we have field_summary (tactical) or full fields (requested details)
        if "field_summary" in form:
            fields = [k for k, v in form["field_summary"].items() if v]
            forms_summary.append(f"Form '{form['id']}': fields={fields}")
        elif "fields" in form:
            # LLM requested full field details
            field_names = [f"{f.get('type', 'unknown')}:{f.get('name', 'unnamed')}" for f in form["fields"][:5]]
            forms_summary.append(f"Form '{form['id']}': {len(form['fields'])} fields ({', '.join(field_names)})")
    
    prompt = f"""You are a browser automation expert. Previous decision: {strategic_decision}

**User instruction:** {instruction}

**Requested form details:**
{chr(10).join(forms_summary) if forms_summary else "(You have the outline from Level 1)"}

**Question:** What specific tool should be called?

Available tools:
- form.fill(args: {{name?, email?, subject?, phone?, message?}})

Return JSON:
{{
    "tool_name": "form.fill",
    "args": {{"name": "...", "email": "..."}},
    "reason": "brief explanation"
}}
"""
    return prompt


async def hierarchical_plan(
    instruction: str,
    page_context: Dict[str, Any],
    llm,
    run_logger
) -> Optional[Dict[str, Any]]:
    """
    Execute hierarchical planning with 3 levels.
    
    Returns action dict or None if hierarchical planner should not be used.
    """
    # Calculate original context size
    try:
        original_size = len(json.dumps(page_context, ensure_ascii=False))
    except Exception:
        original_size = len(str(page_context))
    
    if run_logger:
        run_logger.log_text(f"📐 Hierarchical planner evaluation:")
        run_logger.log_text(f"   Context size: {original_size:,} chars")
        run_logger.log_text(f"   Threshold: {config.hierarchical_planner_chars:,} chars")
        run_logger.log_text(f"   Instruction: {instruction[:100]}...")
    
    should_use = should_use_hierarchical_planner(instruction, page_context)
    
    if run_logger:
        run_logger.log_text(f"   Decision: {'✅ USE hierarchical planner' if should_use else '❌ SKIP hierarchical planner'}")
    
    if not should_use:
        return None
    
    if run_logger:
        threshold = config.hierarchical_planner_chars
        run_logger.log_text(f"🎯 Using hierarchical planner (3-level decision tree)")
        run_logger.log_text(f"   Original context: {original_size:,} chars (threshold: {threshold:,})")
    
    # LEVEL 1: Strategic decision (~2KB)
    strategic_ctx = extract_strategic_context(page_context)
    strategic_prompt = generate_strategic_prompt(strategic_ctx, instruction)
    
    if run_logger:
        try:
            strategic_size = len(json.dumps(strategic_ctx, ensure_ascii=False))
            reduction = ((original_size - strategic_size) / original_size * 100) if original_size > 0 else 0
            run_logger.log_text(f"📊 Level 1 (Strategic): {len(strategic_prompt)} chars prompt, {strategic_size:,} chars context ({reduction:.1f}% reduction)")
        except Exception:
            run_logger.log_text(f"📊 Level 1 (Strategic): {len(strategic_prompt)} chars")
    
    try:
        strategic_response = await llm.ainvoke(strategic_prompt)
        strategic_text = strategic_response.get("text", "") if isinstance(strategic_response, dict) else str(strategic_response)
        strategic_decision = json.loads(strategic_text)
        
        if run_logger:
            run_logger.log_text(f"✓ Strategic decision: {strategic_decision.get('decision')}")
            need_details = strategic_decision.get("need_details")
            if need_details:
                run_logger.log_text(f"   LLM requests details: {need_details}")
            else:
                run_logger.log_text(f"   LLM has enough info, proceeding without Level 2")
        
        if strategic_decision.get("decision") != "use_form":
            # Not a form task, fall back to standard planner
            return None
        
        # Check if LLM needs more details
        need_details = strategic_decision.get("need_details")
        skip_level2 = (need_details is None or (isinstance(need_details, list) and len(need_details) == 0))
        
        if skip_level2:
            # LLM has enough info from Level 1, skip Level 2 entirely
            # Parse instruction directly and call form.fill
            if run_logger:
                run_logger.log_text("⚡ Skipping Level 2 - LLM has sufficient info")
            
            # Parse form values from instruction
            from .form_fill import parse_form_pairs
            parsed_values = parse_form_pairs(instruction)
            
            return {
                "type": "tool",
                "tool_name": "form.fill",
                "args": parsed_values,
                "reason": f"Hierarchical planner (Level 1 only): {strategic_decision.get('reason')}",
                "hierarchical": True,
            }
        else:
            # LLM requested specific details - send only what was asked
            tactical_ctx = extract_requested_details(page_context, need_details)
        
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"❌ Strategic level failed: {e}")
        return None
    
    # LEVEL 2: Tactical decision (~5KB or less if LLM was specific)
    tactical_prompt = generate_tactical_prompt(tactical_ctx, instruction, strategic_decision.get("decision"))
    
    if run_logger:
        run_logger.log_text(f"📋 Level 2 (Tactical): {len(tactical_prompt)} chars")
    
    try:
        tactical_response = await llm.ainvoke(tactical_prompt)
        tactical_text = tactical_response.get("text", "") if isinstance(tactical_response, dict) else str(tactical_response)
        tactical_action = json.loads(tactical_text)
        
        if run_logger:
            run_logger.log_text(f"✓ Tactical decision: {tactical_action.get('tool_name')}")
        
        # LEVEL 3: Direct execution (no LLM)
        return {
            "type": "tool",
            "tool_name": tactical_action.get("tool_name"),
            "args": tactical_action.get("args", {}),
            "reason": f"Hierarchical planner: {tactical_action.get('reason')}",
            "hierarchical": True,
        }
        
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"❌ Tactical level failed: {e}")
        return None
