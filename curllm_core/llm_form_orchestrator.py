#!/usr/bin/env python3
"""
LLM Form Orchestrator - Deleguje decyzje o wypełnianiu formularza do LLM.

LLM otrzymuje:
1. Listę wykrytych pól formularza (podobnie jak DOM)
2. Listę dostępnych operacji (fill, split_name, check, etc.)
3. Dane z instrukcji użytkownika

LLM zwraca:
- Plan wypełnienia formularza (lista operacji do wykonania)
"""

import json
from typing import Dict, List, Any, Optional


def analyze_form_fields(page_evaluate_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analizuje wyniki page.evaluate() i tworzy strukturę dla LLM.
    
    Zwraca informacje o:
    - Wykrytych polach
    - Ich typach i atrybutach
    - Relacjach (split fields, checkbox + label, etc.)
    """
    selectors = page_evaluate_result
    
    fields_info = {
        "detected_fields": [],
        "field_relationships": [],
        "form_metadata": {}
    }
    
    # Standard fields
    for key in ["name", "email", "phone", "message", "subject"]:
        if selectors.get(key):
            fields_info["detected_fields"].append({
                "id": key,
                "type": "text" if key != "message" else "textarea",
                "selector": selectors[key],
                "required": True if key in ["name", "email", "message"] else False,
                "label_hint": key.title()
            })
    
    # Split name fields
    if selectors.get("_split_name"):
        fields_info["field_relationships"].append({
            "type": "split_name",
            "fields": ["name_first", "name_last"],
            "description": "Name field is split into First and Last name",
            "requires_splitting": True
        })
        
        fields_info["detected_fields"].append({
            "id": "name_first",
            "type": "text",
            "selector": selectors.get("name_first"),
            "required": True,
            "label_hint": "First Name"
        })
        
        fields_info["detected_fields"].append({
            "id": "name_last",
            "type": "text",
            "selector": selectors.get("name_last"),
            "required": True,
            "label_hint": "Last Name"
        })
    
    # Consent checkbox
    if selectors.get("consent"):
        fields_info["detected_fields"].append({
            "id": "consent",
            "type": "checkbox",
            "selector": selectors["consent"],
            "required": True,
            "label_hint": "GDPR/Privacy Consent"
        })
    
    # Submit button
    if selectors.get("submit"):
        fields_info["detected_fields"].append({
            "id": "submit",
            "type": "button",
            "selector": selectors["submit"],
            "required": False,
            "label_hint": "Submit Button"
        })
    
    # Form metadata
    if selectors.get("_formId"):
        fields_info["form_metadata"]["form_id"] = selectors["_formId"]
    
    if selectors.get("_debug_consent"):
        fields_info["form_metadata"]["consent_debug"] = selectors["_debug_consent"]
    
    return fields_info


def get_available_operations() -> List[Dict[str, Any]]:
    """
    Zwraca listę operacji dostępnych dla LLM.
    Format podobny do tool definitions w OpenAI/Anthropic.
    """
    return [
        {
            "operation": "fill_text",
            "description": "Fill a text input or textarea field with a value",
            "parameters": {
                "field_id": "ID of the field to fill (e.g., 'email', 'name_first')",
                "value": "Text value to fill into the field"
            },
            "example": {"operation": "fill_text", "field_id": "email", "value": "john@example.com"}
        },
        {
            "operation": "split_name",
            "description": "Split a full name into first and last name for split name fields",
            "parameters": {
                "full_name": "Full name to split (e.g., 'John Doe')",
                "first_field_id": "ID of the first name field",
                "last_field_id": "ID of the last name field"
            },
            "example": {"operation": "split_name", "full_name": "John Doe", "first_field_id": "name_first", "last_field_id": "name_last"}
        },
        {
            "operation": "check_checkbox",
            "description": "Check a checkbox (e.g., consent, terms agreement)",
            "parameters": {
                "field_id": "ID of the checkbox field"
            },
            "example": {"operation": "check_checkbox", "field_id": "consent"}
        },
        {
            "operation": "click_submit",
            "description": "Click the submit button to send the form",
            "parameters": {
                "field_id": "ID of the submit button (usually 'submit')"
            },
            "example": {"operation": "click_submit", "field_id": "submit"}
        },
        {
            "operation": "validate_field",
            "description": "Check if a field value is valid (e.g., email format)",
            "parameters": {
                "field_id": "ID of the field to validate",
                "expected_format": "Expected format (e.g., 'email', 'phone')"
            },
            "example": {"operation": "validate_field", "field_id": "email", "expected_format": "email"}
        }
    ]


def create_llm_prompt(
    instruction: str,
    llm_context: Dict[str, Any],
    operations: List[Dict[str, Any]],
    user_data: Dict[str, str]
) -> str:
    """
    Tworzy prompt dla LLM do zaplanowania wypełnienia formularza.
    """
    form_type = llm_context.get('form_type', 'Unknown')
    fields = llm_context.get('fields', [])
    
    prompt = f"""You are a form-filling orchestrator. Your task is to create a plan to fill a web form.

USER INSTRUCTION:
{instruction}

USER DATA EXTRACTED:
{json.dumps(user_data, indent=2)}

FORM TYPE: {form_type}
TOTAL FIELDS: {len(fields)}

DETECTED FIELDS:
{json.dumps(fields, indent=2)}

AVAILABLE OPERATIONS:
{json.dumps(operations, indent=2)}

ANALYSIS GUIDELINES:

1. NAME FIELDS:
   - If you see hints=['first_name'] and hints=['last_name'] → Use split_name operation
   - If label contains "First" and another has "Last" → Split the full name
   - If only one name field → Fill with full name as-is

2. EMAIL FIELD:
   - Match by: type='email', hints=['email'], label contains 'email'/'e-mail'/'mail'

3. MESSAGE/COMMENT:
   - Match by: type='textarea', hints=['message'], label contains 'message'/'comment'

4. CHECKBOXES:
   - Consent/GDPR: type='checkbox', hints=['consent'], required=true
   - Always check required checkboxes

5. FIELD MATCHING STRATEGY:
   - Priority 1: hints array (most reliable)
   - Priority 2: label text
   - Priority 3: field id/name

IMPORTANT RULES:
- Use ACTUAL field IDs from detected fields (don't invent IDs)
- If split name detected, split "John Doe" → first="John", last="Doe"
- Fill ALL required fields
- Check all consent checkboxes
- Return ONLY JSON, no explanatory text outside JSON

RESPONSE FORMAT:
```json
{{
  "plan": [
    {{"operation": "fill_text", "field_id": "wpforms-260-field_0", "value": "John", "reasoning": "First name field detected by hints"}},
    {{"operation": "fill_text", "field_id": "wpforms-260-field_0-last", "value": "Doe", "reasoning": "Last name field"}},
    {{"operation": "fill_text", "field_id": "wpforms-260-field_1", "value": "john@example.com", "reasoning": "Email field (type=email)"}},
    {{"operation": "fill_text", "field_id": "wpforms-260-field_2", "value": "Hello test", "reasoning": "Message textarea"}},
    {{"operation": "check_checkbox", "field_id": "wpforms-260-field_3_1", "reasoning": "Required consent checkbox"}}
  ]
}}
```

Generate the plan NOW (JSON only):"""
    
    return prompt


async def execute_form_plan(plan: List[Dict[str, Any]], page, selectors: Dict[str, str], run_logger=None) -> Dict[str, Any]:
    """
    Wykonuje plan wypełnienia formularza wygenerowany przez LLM.
    """
    from .form_fill import _robust_fill_field
    
    result = {
        "executed_operations": [],
        "errors": [],
        "submitted": False
    }
    
    if run_logger:
        run_logger.log_text("🤖 Executing LLM-generated form plan:")
    
    for i, operation in enumerate(plan, 1):
        op_type = operation.get("operation")
        
        if run_logger:
            run_logger.log_text(f"   Step {i}: {op_type}")
        
        try:
            if op_type == "fill_text":
                field_id = operation.get("field_id")
                value = operation.get("value")
                selector = selectors.get(field_id)
                
                if not selector:
                    if run_logger:
                        run_logger.log_text(f"      ⚠️  Field '{field_id}' not found, skipping")
                    continue
                
                if run_logger:
                    run_logger.log_text(f"      ▶️  Filling {field_id}: '{value}' → {selector}")
                
                success = await _robust_fill_field(page, selector, value)
                result["executed_operations"].append({
                    "operation": op_type,
                    "field_id": field_id,
                    "success": success
                })
            
            elif op_type == "split_name":
                full_name = operation.get("full_name", "")
                first_field_id = operation.get("first_field_id")
                last_field_id = operation.get("last_field_id")
                
                # Split name
                parts = full_name.split(None, 1)
                first_name = parts[0] if len(parts) > 0 else ""
                last_name = parts[1] if len(parts) > 1 else ""
                
                if run_logger:
                    run_logger.log_text(f"      🔀 Split '{full_name}' → First: '{first_name}', Last: '{last_name}'")
                
                # Fill first name
                first_selector = selectors.get(first_field_id)
                if first_selector and first_name:
                    await _robust_fill_field(page, first_selector, first_name)
                
                # Fill last name
                last_selector = selectors.get(last_field_id)
                if last_selector and last_name:
                    await _robust_fill_field(page, last_selector, last_name)
                
                result["executed_operations"].append({
                    "operation": op_type,
                    "first_name": first_name,
                    "last_name": last_name,
                    "success": True
                })
            
            elif op_type == "check_checkbox":
                field_id = operation.get("field_id")
                selector = selectors.get(field_id)
                
                if not selector:
                    if run_logger:
                        run_logger.log_text(f"      ⚠️  Checkbox '{field_id}' not found, skipping")
                    continue
                
                if run_logger:
                    run_logger.log_text(f"      ☑️  Checking checkbox: {field_id}")
                
                try:
                    await page.check(selector)
                    result["executed_operations"].append({
                        "operation": op_type,
                        "field_id": field_id,
                        "success": True
                    })
                except Exception:
                    # Try clicking instead
                    try:
                        await page.click(selector)
                        result["executed_operations"].append({
                            "operation": op_type,
                            "field_id": field_id,
                            "success": True,
                            "method": "click"
                        })
                    except Exception as e:
                        result["errors"].append({
                            "operation": op_type,
                            "field_id": field_id,
                            "error": str(e)
                        })
            
            elif op_type == "click_submit":
                field_id = operation.get("field_id", "submit")
                selector = selectors.get(field_id)
                
                if not selector:
                    if run_logger:
                        run_logger.log_text(f"      ⚠️  Submit button not found, skipping")
                    continue
                
                if run_logger:
                    run_logger.log_text(f"      🚀 Clicking submit button")
                
                try:
                    await page.click(selector)
                    result["submitted"] = True
                    result["executed_operations"].append({
                        "operation": op_type,
                        "success": True
                    })
                except Exception as e:
                    result["errors"].append({
                        "operation": op_type,
                        "error": str(e)
                    })
        
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"      ❌ Error: {str(e)}")
            result["errors"].append({
                "step": i,
                "operation": op_type,
                "error": str(e)
            })
    
    return result


async def llm_orchestrated_form_fill(
    instruction: str,
    page,
    llm,
    run_logger=None,
    domain_dir: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Główna funkcja - wypełnia formularz używając LLM jako orkiestratora.
    
    Flow:
    1. Wykryj pola formularza (JavaScript)
    2. Przygotuj dane dla LLM
    3. LLM planuje wypełnienie
    4. System wykonuje plan
    5. Walidacja i raportowanie
    """
    # Import here to avoid circular dependency
    from .form_fill import parse_form_pairs
    from .form_detector import detect_all_form_fields, create_llm_context
    
    try:
        # 1. Parse user data from instruction
        user_data = parse_form_pairs(instruction)
        
        if run_logger:
            run_logger.log_text("🤖 LLM Form Orchestrator - Starting")
            run_logger.log_text(f"   User data: {user_data}")
        
        # 2. Detect all form fields
        detection_result = await detect_all_form_fields(page)
        
        if detection_result.get('error'):
            if run_logger:
                run_logger.log_text(f"   ❌ Error: {detection_result['error']}")
            return None
        
        fields_count = detection_result.get('total_fields', 0)
        form_type = detection_result.get('form_metadata', {}).get('form_type', 'Unknown')
        
        if run_logger:
            run_logger.log_text(f"   📊 Detected: {fields_count} fields, Form type: {form_type}")
        
        # 3. Create context for LLM
        llm_context = create_llm_context(detection_result, user_data)
        
        # 4. Get available operations
        operations = get_available_operations()
        
        # 5. Create prompt for LLM
        prompt = create_llm_prompt(instruction, llm_context, operations, user_data)
        
        if run_logger:
            run_logger.log_text("   🧠 Asking LLM for filling plan...")
        
        # 6. Ask LLM for plan
        llm_response = await llm.generate(prompt, max_tokens=1500, temperature=0.1)
        
        if run_logger:
            run_logger.log_text(f"   ✅ LLM responded ({len(llm_response)} chars)")
        
        # 7. Parse LLM response
        plan = parse_llm_plan(llm_response)
        
        if not plan:
            if run_logger:
                run_logger.log_text("   ⚠️  Could not parse LLM plan, falling back")
            return None
        
        if run_logger:
            run_logger.log_text(f"   📋 Plan has {len(plan)} operations")
        
        # 8. Build selectors map from detected fields
        selectors = {}
        for field in detection_result.get('detected_fields', []):
            if field.get('id'):
                field_id = field['id']
                selectors[field_id] = f"#{field_id}"
        
        # 9. Execute plan
        result = await execute_form_plan(plan, page, selectors, run_logger)
        
        return result
    
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"   ❌ LLM Orchestrator error: {str(e)}")
        return None


def parse_llm_plan(llm_response: str) -> Optional[List[Dict[str, Any]]]:
    """
    Parsuje odpowiedź LLM i wyodrębnia plan.
    """
    try:
        # Try to find JSON in response
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
        if json_match:
            plan_data = json.loads(json_match.group(1))
            return plan_data.get("plan", [])
        
        # Try direct JSON parsing
        plan_data = json.loads(llm_response)
        return plan_data.get("plan", [])
    
    except Exception:
        return None
