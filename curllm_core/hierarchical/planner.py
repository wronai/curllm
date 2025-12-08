"""
DEPRECATED: This module is deprecated.

Use the LLM-driven version instead:
    from curllm_core.v2 import LLMHierarchicalPlanner

This module will be removed in a future version.
"""

import warnings
warnings.warn(
    "This module is deprecated. Use curllm_core.v2.LLMHierarchicalPlanner instead.",
    DeprecationWarning,
    stacklevel=2
)

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
import logging
from curllm_core.config import config
from curllm_core.vision_form_analysis import (
    analyze_form_fields_vision,
    build_vision_enhanced_field_list,
    create_vision_decision_tree
)

logger = logging.getLogger(__name__)


def should_use_hierarchical(instruction: str, page_context: Dict[str, Any]) -> bool:
    """
    Decide if hierarchical planner is worth the overhead.
    
    Hierarchical planner takes 20-25 seconds but is valuable for:
    - Complex multi-step tasks
    - Large page contexts
    
    For simple form fills with small contexts, skip it and use direct form.fill.
    
    Args:
        instruction: Task instruction
        page_context: Page context dictionary
        
    Returns:
        True if hierarchical planner should be used, False to bypass
    """
    # Check if this is a simple form task
    if is_simple_form_task(instruction, page_context):
        logger.info("✂️ Bypassing hierarchical planner: simple form task detected")
        return False
    
    # Check if multi-step task (keep hierarchical)
    if requires_multi_step(instruction):
        logger.info("🔧 Using hierarchical planner: multi-step task detected")
        return True
    
    # Check context size
    context_size = estimate_context_size(page_context)
    threshold = config.hierarchical_planner_chars if hasattr(config, 'hierarchical_planner_chars') else 25000
    
    if context_size < threshold:
        logger.info(f"✂️ Bypassing hierarchical planner: context too small ({context_size} < {threshold})")
        return False
    
    logger.info(f"🔧 Using hierarchical planner: large context ({context_size} chars)")
    return True


def is_simple_form_task(instruction: str, page_context: Dict[str, Any]) -> bool:
    """
    Check if this is a simple, single-form fill task.
    
    Simple form criteria:
    - Instruction contains form keywords
    - Only 1 form on page
    - Form has <= 10 fields
    
    Args:
        instruction: Task instruction
        page_context: Page context dictionary
        
    Returns:
        True if this is a simple form task
    """
    if not instruction:
        return False
    
    lower = instruction.lower()
    
    # Keywords suggesting simple form
    form_keywords = ["fill form", "fill contact", "wypełnij formularz", "submit form"]
    if not any(k in lower for k in form_keywords):
        return False
    
    # Check if only 1 form present
    forms = page_context.get("forms", [])
    if len(forms) != 1:
        return False
    
    # Check form complexity
    fields = forms[0].get("fields", [])
    if len(fields) <= 10:  # Simple form
        logger.debug(f"Simple form detected: 1 form, {len(fields)} fields")
        return True
    
    return False


def requires_multi_step(instruction: str) -> bool:
    """
    Check if instruction requires multiple steps.
    
    Multi-step indicators:
    - "then", "after", "next"
    - "click and", "navigate and"
    - Multiple actions listed
    
    Args:
        instruction: Task instruction
        
    Returns:
        True if multi-step task detected
    """
    if not instruction:
        return False
    
    lower = instruction.lower()
    
    # Multi-step keywords
    multi_step_keywords = [
        " then ", " after ", " next ",
        "click and", "navigate and",
        "first ", "second ",
        "step 1", "step 2"
    ]
    
    return any(keyword in lower for keyword in multi_step_keywords)


def estimate_context_size(page_context: Dict[str, Any]) -> int:
    """
    Estimate the size of page context in characters.
    
    Args:
        page_context: Page context dictionary
        
    Returns:
        Estimated size in characters
    """
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
        
        # Semantic concept groups for field detection (language-agnostic)
        field_concepts = {
            "name": ["name", "imie", "nazwisko", "fullname", "nombre", "first", "last"],
            "email": ["email", "mail", "e-mail", "correo", "poczta"],
            "subject": ["subject", "temat", "asunto", "topic"],
            "phone": ["phone", "tel", "telefon", "mobile", "celular"],
            "message": ["message", "wiadomosc", "textarea", "content", "body", "komentarz"],
        }
        
        for field in form.get("fields", []):
            field_name = (field.get("name") or "").lower()
            field_type = (field.get("type") or "").lower()
            
            # Detect canonical fields using semantic concepts
            for canonical_field, concepts in field_concepts.items():
                if any(kw in field_name for kw in concepts):
                    field_summary[canonical_field] = True
                    break
            
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
            # LLM requested full field details - map to canonical names
            canonical_fields = []
            for f in form["fields"]:
                field_name = (f.get("name") or "").lower()
                field_type = (f.get("type") or "")
                field_visible = f.get("visible", True)
                
                if not field_visible or field_type in ["hidden", "submit"]:
                    continue  # Skip hidden and submit fields
                
                # Semantic concept groups for field mapping (language-agnostic)
                field_concepts = {
                    "name": ["name", "imie", "nazwisko", "full", "nombre", "first", "last"],
                    "email": ["email", "mail", "e-mail", "correo", "poczta"],
                    "subject": ["subject", "temat", "asunto", "topic"],
                    "phone": ["phone", "tel", "telefon", "mobile", "celular"],
                    "message": ["message", "wiadomosc", "textarea", "tresc", "body", "komentarz"],
                }
                
                # Map to canonical names using semantic concepts
                canonical = None
                for field_type_name, concepts in field_concepts.items():
                    if any(kw in field_name for kw in concepts):
                        canonical = field_type_name
                        break
                
                if canonical:
                    required = f.get("required", False)
                    canonical_fields.append(f"{canonical}{'*' if required else ''} ({field_type})")
            
            forms_summary.append(f"Form '{form['id']}': {', '.join(canonical_fields) if canonical_fields else 'no visible fields'}")
    
    prompt = f"""You are a browser automation expert. Previous decision: {strategic_decision}

**User instruction:** {instruction}

**Detected form fields (canonical names, * = required):**
{chr(10).join(forms_summary) if forms_summary else "(You have the outline from Level 1)"}

**CRITICAL RULE:** 
- ONLY include fields that EXIST in the form above!
- If the user instruction mentions a field that does NOT exist in the form (e.g., "subject"), DO NOT include it in args.
- Map instruction values ONLY to available form fields.

**Question:** What specific tool should be called?

Available tools:
- form.fill(args: {{name?, email?, subject?, phone?, message?}})

**Example:** If form has only [name, email, message] but instruction says "subject=Test", IGNORE subject and fill only name, email, message.

Return JSON with ONLY fields that actually exist in the form:
{{
    "tool_name": "form.fill",
    "args": {{"name": "...", "email": "...", "message": "..."}},
    "reason": "brief explanation"
}}
"""
    return prompt


async def hierarchical_plan_with_vision(
    instruction: str,
    page_context: Dict[str, Any],
    screenshot_path: str,
    llm,
    run_logger
) -> Optional[Dict[str, Any]]:
    """
    Execute hierarchical planning WITH vision analysis to detect honeypots and prioritize fields.
    
    This is an enhanced version that uses computer vision to:
    1. Verify which fields are actually visible
    2. Detect honeypot fields (hidden but present in DOM)
    3. Prioritize fields based on visual layout
    4. Map visual labels to field names
    
    Args:
        instruction: User instruction
        page_context: Full page context from DOM
        screenshot_path: Path to screenshot for vision analysis
        llm: LLM client (must support vision if available)
        run_logger: Logger
    
    Returns:
        Action dict with enhanced field selection, or None if not applicable
    """
    if run_logger:
        run_logger.log_text("🔍 Vision-enhanced hierarchical planner starting...")
    
    # Check if this looks like a form task
    if not should_use_hierarchical_planner(instruction, page_context):
        return None
    
    forms = page_context.get("forms", [])
    if not forms:
        if run_logger:
            run_logger.log_text("   No forms detected in page context")
        return None
    
    # Step 1: Run vision analysis on screenshot
    try:
        vision_analysis = await analyze_form_fields_vision(
            llm,
            screenshot_path,
            forms,
            instruction,
            run_logger
        )
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"   ⚠️  Vision analysis failed: {e}, falling back to standard hierarchical planner")
        # Fall back to standard hierarchical planner
        return await hierarchical_plan(instruction, page_context, llm, run_logger)
    
    # Step 2: Build enhanced field list with honeypot detection
    enhanced_fields = build_vision_enhanced_field_list(forms, vision_analysis)
    
    if run_logger:
        safe_count = len([f for f in enhanced_fields if f["priority"] > 0])
        honeypot_count = len([f for f in enhanced_fields if f["is_honeypot"]])
        run_logger.log_text(f"   Enhanced field list: {safe_count} safe fields, {honeypot_count} honeypots avoided")
    
    # Step 3: Create decision tree
    decision_tree = create_vision_decision_tree(enhanced_fields, instruction, run_logger)
    
    # Step 4: Extract values from instruction
    from .form_fill import parse_form_pairs
    parsed_values = parse_form_pairs(instruction)
    
    # Step 5: Map parsed values to safe fields only
    safe_args = {}
    field_selection = decision_tree.get("field_selection", {})
    
    for canonical_type, field_data in field_selection.items():
        if canonical_type in parsed_values:
            safe_args[canonical_type] = parsed_values[canonical_type]
            if run_logger:
                run_logger.log_text(f"   ✓ Mapping {canonical_type}: {field_data['name']} (priority: {field_data['priority']})")
    
    if not safe_args:
        if run_logger:
            run_logger.log_text("   ❌ No safe fields matched instruction values")
        return None
    
    # Step 6: Return action with vision metadata
    action = {
        "type": "tool",
        "tool_name": "form.fill",
        "args": safe_args,
        "reason": f"Vision-guided hierarchical planner: Detected {len(safe_args)} fields, avoided {decision_tree['honeypots_avoided']} honeypots",
        "hierarchical": True,
        "vision_enhanced": True,
        "vision_metadata": {
            "honeypots_avoided": decision_tree["honeypots_avoided"],
            "safe_fields": decision_tree["safe_fields"],
            "warnings": decision_tree.get("warnings", [])
        }
    }
    
    if run_logger:
        run_logger.log_text(f"✓ Vision-enhanced action generated: {action['tool_name']}")
        run_logger.log_text(f"   Args: {safe_args}")
        run_logger.log_text(f"   Honeypots avoided: {decision_tree['honeypots_avoided']}")
    
    return action


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
            
            if run_logger:
                try:
                    tactical_size = len(json.dumps(tactical_ctx, ensure_ascii=False))
                    run_logger.log_text(f"📋 Level 2 (Tactical): {tactical_size:,} chars context")
                    # Log what fields LLM sees
                    for form in tactical_ctx.get("forms", []):
                        field_count = len(form.get("fields", []))
                        field_names = [(f.get("name") or "") for f in form.get("fields", [])[:10]]
                        run_logger.log_text(f"   Form '{form.get('id', 'unknown')}': {field_count} fields")
                        if field_names:
                            run_logger.log_text(f"   Fields: {', '.join(field_names)}")
                except Exception:
                    pass
        
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"❌ Strategic level failed: {e}")
        return None
    
    # LEVEL 2: Tactical decision (~5KB or less if LLM was specific)
    tactical_prompt = generate_tactical_prompt(tactical_ctx, instruction, strategic_decision.get("decision"))
    
    if run_logger:
        run_logger.log_text(f"📋 Level 2 (Tactical) prompt ({len(tactical_prompt)} chars):")
        run_logger.log_text(f"```\n{tactical_prompt}\n```")
    
    try:
        tactical_response = await llm.ainvoke(tactical_prompt)
        tactical_text = tactical_response.get("text", "") if isinstance(tactical_response, dict) else str(tactical_response)
        tactical_action = json.loads(tactical_text)
        
        if run_logger:
            run_logger.log_text(f"✓ Tactical decision: {tactical_action.get('tool_name')}")
            run_logger.log_text(f"   Args: {tactical_action.get('args', {})}")
        
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
