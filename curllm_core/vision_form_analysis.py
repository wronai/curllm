#!/usr/bin/env python3
"""
Vision-based form field analysis to avoid honeypots and improve field detection accuracy.

Uses LLM with vision capabilities to:
1. Identify visible form fields from screenshot
2. Detect honeypot fields (hidden, off-screen, display:none)
3. Map visual field positions to DOM elements
4. Prioritize fields based on visual appearance
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


async def analyze_form_fields_vision(
    llm,
    screenshot_path: str,
    dom_forms: List[Dict[str, Any]],
    instruction: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Analyze form fields using vision model to detect visible fields and avoid honeypots.
    
    Args:
        llm: LLM client with vision capabilities
        screenshot_path: Path to screenshot image
        dom_forms: Form data extracted from DOM
        instruction: User instruction for form filling
        run_logger: Optional logger
    
    Returns:
        {
            "visible_fields": [{"form_id": str, "field_name": str, "field_type": str, "label": str, "priority": int}],
            "honeypot_fields": [{"form_id": str, "field_name": str, "reason": str}],
            "field_mapping": {field_name: {"canonical": str, "confidence": float}},
            "recommended_fill_order": [field_name, ...]
        }
    """
    if run_logger:
        run_logger.log_text("🔍 Vision form analysis: analyzing screenshot for visible fields")
    
    # Build form summary for LLM
    form_summary = []
    all_fields = []
    for form_idx, form in enumerate(dom_forms[:3]):  # Max 3 forms
        form_id = form.get("id", f"form_{form_idx}")
        fields = form.get("fields", [])
        visible_fields = [f for f in fields if f.get("visible", True) and f.get("type") not in ["hidden", "submit"]]
        
        form_summary.append(f"Form '{form_id}': {len(visible_fields)} visible fields")
        for field in visible_fields:
            field_name = field.get("name", "")
            field_type = field.get("type", "")
            required = field.get("required", False)
            all_fields.append({
                "form_id": form_id,
                "name": field_name,
                "type": field_type,
                "required": required
            })
    
    if not all_fields:
        if run_logger:
            run_logger.log_text("   No visible fields found in DOM")
        return {
            "visible_fields": [],
            "honeypot_fields": [],
            "field_mapping": {},
            "recommended_fill_order": []
        }
    
    # Create vision analysis prompt
    prompt = f"""You are a form field detector. Analyze this screenshot to identify VISIBLE form input fields.

**User instruction:** {instruction}

**DOM-detected fields (may include honeypots):**
{chr(10).join([f"- {f['name']} ({f['type']}){' *required' if f.get('required') else ''}" for f in all_fields[:20]])}

**Your task:**
1. Look at the screenshot and identify ALL VISIBLE text input fields, email fields, phone fields, textareas
2. For each VISIBLE field, identify its label/placeholder text
3. Detect HONEYPOT fields (fields that exist in DOM but are NOT visible on screen):
   - Fields positioned off-screen (negative coordinates, far outside viewport)
   - Fields with zero size (0x0 pixels)
   - Fields hidden by CSS (display:none, visibility:hidden, opacity:0)
   - Fields with no visible label or placeholder
4. Map each visible field to its canonical name (name, email, phone, subject, message)
5. Determine the recommended fill order (top to bottom, left to right)

**CRITICAL:** A field is a HONEYPOT if:
- It exists in DOM list above BUT is NOT visible in the screenshot
- It has no label/placeholder visible to user
- It's positioned outside the visible form area

Return JSON:
{{
    "visible_fields": [
        {{
            "field_name": "name-1",
            "field_type": "text",
            "label": "Name" or "Imię",
            "canonical": "name",
            "confidence": 0.95,
            "position": {{"x": 100, "y": 200}},
            "required": true
        }}
    ],
    "honeypot_fields": [
        {{
            "field_name": "hidden-trap",
            "reason": "Not visible in screenshot but present in DOM"
        }}
    ],
    "recommended_fill_order": ["name-1", "email-1", "phone-1", "message-1"]
}}

**Example honeypot patterns to detect:**
- "email_address_" - suspicious underscore suffix
- "phone_number_confirm" - unusual confirmation field
- Fields with "trap", "bot", "honeypot" in name
- Duplicate email/phone fields (second one often honeypot)
"""
    
    try:
        # Call LLM with vision
        vision_response = await llm.ainvoke_with_image(prompt, screenshot_path)
        
        if isinstance(vision_response, dict):
            response_text = vision_response.get("text", "")
        else:
            response_text = str(vision_response)
        
        # Parse JSON response
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(response_text)
            
            if run_logger:
                visible_count = len(analysis.get("visible_fields", []))
                honeypot_count = len(analysis.get("honeypot_fields", []))
                run_logger.log_text(f"   ✓ Vision analysis: {visible_count} visible fields, {honeypot_count} honeypots detected")
                
                if honeypot_count > 0:
                    run_logger.log_text("   ⚠️  Honeypot fields detected:")
                    for hp in analysis.get("honeypot_fields", [])[:5]:
                        run_logger.log_text(f"      - {hp.get('field_name')}: {hp.get('reason')}")
            
            return analysis
            
        except json.JSONDecodeError as e:
            if run_logger:
                run_logger.log_text(f"   ❌ Failed to parse vision response: {e}")
                run_logger.log_text(f"   Raw response: {response_text[:500]}")
            return {
                "visible_fields": [],
                "honeypot_fields": [],
                "field_mapping": {},
                "recommended_fill_order": [],
                "error": str(e)
            }
    
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"   ❌ Vision analysis failed: {e}")
        return {
            "visible_fields": [],
            "honeypot_fields": [],
            "field_mapping": {},
            "recommended_fill_order": [],
            "error": str(e)
        }


def build_vision_enhanced_field_list(
    dom_forms: List[Dict[str, Any]],
    vision_analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Build enhanced field list combining DOM data with vision analysis.
    
    Returns fields prioritized by:
    1. Visible in screenshot (not honeypot)
    2. Required fields first
    3. Visual order (top to bottom)
    4. Confidence score from vision
    """
    visible_field_names = set()
    for vf in vision_analysis.get("visible_fields", []):
        visible_field_names.add(vf.get("field_name"))
    
    honeypot_field_names = set()
    for hf in vision_analysis.get("honeypot_fields", []):
        honeypot_field_names.add(hf.get("field_name"))
    
    enhanced_fields = []
    
    for form in dom_forms:
        form_id = form.get("id", "")
        for field in form.get("fields", []):
            field_name = field.get("name", "")
            field_type = field.get("type", "")
            
            # Skip hidden and submit fields
            if field_type in ["hidden", "submit"]:
                continue
            
            # Check if field is honeypot
            is_honeypot = field_name in honeypot_field_names
            
            # Check if field is visible according to vision
            is_visible_in_screenshot = field_name in visible_field_names
            
            # Get vision data for this field
            vision_data = None
            for vf in vision_analysis.get("visible_fields", []):
                if vf.get("field_name") == field_name:
                    vision_data = vf
                    break
            
            # Calculate priority
            priority = 0
            if is_honeypot:
                priority = -100  # Never fill honeypots
            elif is_visible_in_screenshot:
                priority = 100
                if field.get("required"):
                    priority += 50
                if vision_data:
                    priority += int(vision_data.get("confidence", 0) * 20)
            else:
                # Field in DOM but not visible in screenshot - likely honeypot
                priority = -50
            
            enhanced_fields.append({
                "form_id": form_id,
                "name": field_name,
                "type": field_type,
                "required": field.get("required", False),
                "visible_in_dom": field.get("visible", True),
                "visible_in_screenshot": is_visible_in_screenshot,
                "is_honeypot": is_honeypot,
                "priority": priority,
                "canonical": vision_data.get("canonical") if vision_data else None,
                "label": vision_data.get("label") if vision_data else None,
                "confidence": vision_data.get("confidence", 0) if vision_data else 0
            })
    
    # Sort by priority (highest first)
    enhanced_fields.sort(key=lambda x: x["priority"], reverse=True)
    
    return enhanced_fields


def create_vision_decision_tree(
    enhanced_fields: List[Dict[str, Any]],
    instruction: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Create decision tree for field filling based on vision analysis.
    
    Decision tree structure:
    1. Filter out honeypots (priority < 0)
    2. Group by canonical type (name, email, phone, message)
    3. Select highest priority field for each type
    4. Determine fill strategy
    """
    if run_logger:
        run_logger.log_text("🌳 Building vision decision tree...")
    
    # Filter out honeypots and invisible fields
    safe_fields = [f for f in enhanced_fields if f["priority"] > 0]
    
    if run_logger:
        run_logger.log_text(f"   Total fields analyzed: {len(enhanced_fields)}")
        run_logger.log_text(f"   Safe fields (priority > 0): {len(safe_fields)}")
        run_logger.log_text(f"   Honeypots/invisible (priority <= 0): {len(enhanced_fields) - len(safe_fields)}")
    
    # Group by canonical type
    canonical_groups = {
        "name": [],
        "email": [],
        "phone": [],
        "subject": [],
        "message": []
    }
    
    for field in safe_fields:
        canonical = field.get("canonical")
        if canonical in canonical_groups:
            canonical_groups[canonical].append(field)
        else:
            # Try to infer canonical from field name using semantic concept groups
            field_name_lower = field["name"].lower()
            
            # Semantic concept groups (language-agnostic)
            # LLM would determine these dynamically in production
            name_concepts = {"name", "imie", "nazwisko", "fullname", "nombre", "first", "last"}
            email_concepts = {"email", "mail", "e-mail", "correo", "poczta"}
            phone_concepts = {"phone", "tel", "telefon", "mobile", "komórka", "celular"}
            subject_concepts = {"subject", "temat", "asunto", "topic", "title"}
            message_concepts = {"message", "wiadomosc", "textarea", "content", "body", "komentarz"}
            
            if any(kw in field_name_lower for kw in name_concepts):
                canonical_groups["name"].append(field)
            elif any(kw in field_name_lower for kw in email_concepts):
                canonical_groups["email"].append(field)
            elif any(kw in field_name_lower for kw in phone_concepts):
                canonical_groups["phone"].append(field)
            elif any(kw in field_name_lower for kw in subject_concepts):
                canonical_groups["subject"].append(field)
            elif any(kw in field_name_lower for kw in message_concepts):
                canonical_groups["message"].append(field)
    
    # Log canonical grouping
    if run_logger:
        run_logger.log_text("   Grouping fields by canonical type:")
        for canonical_type, fields in canonical_groups.items():
            if fields:
                run_logger.log_text(f"      {canonical_type}: {len(fields)} candidate(s)")
    
    # Select best field for each canonical type (highest priority)
    selected_fields = {}
    for canonical_type, fields in canonical_groups.items():
        if fields:
            # Sort by priority and take first
            fields.sort(key=lambda x: (x["priority"], x["confidence"]), reverse=True)
            selected_fields[canonical_type] = fields[0]
            
            if run_logger:
                selected = fields[0]
                run_logger.log_text(f"   ✓ Selected {canonical_type}: {selected['name']} (priority: {selected['priority']}, confidence: {selected['confidence']:.2f})")
    
    # Build decision tree
    decision_tree = {
        "strategy": "vision_guided",
        "total_fields": len(enhanced_fields),
        "safe_fields": len(safe_fields),
        "honeypots_avoided": len([f for f in enhanced_fields if f["is_honeypot"]]),
        "field_selection": selected_fields,
        "fill_order": [f["name"] for f in safe_fields if f.get("canonical") in selected_fields],
        "warnings": []
    }
    
    # Add warnings
    if not selected_fields.get("email"):
        decision_tree["warnings"].append("No visible email field detected")
    if not selected_fields.get("name"):
        decision_tree["warnings"].append("No visible name field detected")
    
    honeypot_count = decision_tree["honeypots_avoided"]
    if honeypot_count > 0:
        decision_tree["warnings"].append(f"Avoided {honeypot_count} honeypot field(s)")
    
    # Log decision tree summary
    if run_logger:
        run_logger.log_text(f"🌳 Decision tree built:")
        run_logger.log_text(f"   Strategy: {decision_tree['strategy']}")
        run_logger.log_text(f"   Fields selected: {len(selected_fields)}")
        run_logger.log_text(f"   Fill order: {decision_tree['fill_order']}")
        if decision_tree['warnings']:
            run_logger.log_text(f"   Warnings: {len(decision_tree['warnings'])}")
            for warning in decision_tree['warnings']:
                run_logger.log_text(f"      ⚠️  {warning}")
    
    return decision_tree
