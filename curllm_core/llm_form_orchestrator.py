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
    fields_info: Dict[str, Any],
    operations: List[Dict[str, Any]],
    user_data: Dict[str, str]
) -> str:
    """
    Tworzy prompt dla LLM do zaplanowania wypełnienia formularza.
    """
    prompt = f"""You are a form-filling orchestrator. Your task is to create a plan to fill a web form based on the user's instruction and detected form fields.

USER INSTRUCTION:
{instruction}

USER DATA EXTRACTED:
{json.dumps(user_data, indent=2)}

DETECTED FORM FIELDS:
{json.dumps(fields_info["detected_fields"], indent=2)}

FIELD RELATIONSHIPS (if any):
{json.dumps(fields_info.get("field_relationships", []), indent=2)}

AVAILABLE OPERATIONS:
{json.dumps(operations, indent=2)}

TASK:
Create a step-by-step plan to fill this form. Return your plan as a JSON array of operations.

RULES:
1. Use "split_name" operation if you detect split name fields (name_first + name_last)
2. Always check consent checkboxes if present and required
3. Fill all required fields before submitting
4. Use "fill_text" for standard text inputs and textareas
5. Always end with "click_submit" operation
6. If a field is not available, skip it (don't include in plan)

EXAMPLE RESPONSE FORMAT:
```json
{{
  "plan": [
    {{"operation": "split_name", "full_name": "John Doe", "first_field_id": "name_first", "last_field_id": "name_last"}},
    {{"operation": "fill_text", "field_id": "email", "value": "john@example.com"}},
    {{"operation": "fill_text", "field_id": "message", "value": "Hello test"}},
    {{"operation": "check_checkbox", "field_id": "consent"}},
    {{"operation": "click_submit", "field_id": "submit"}}
  ],
  "reasoning": "Brief explanation of the plan"
}}
```

Generate the plan now:"""
    
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
    
    # 1. Parse user data from instruction
    user_data = parse_form_pairs(instruction)
    
    if run_logger:
        run_logger.log_text("🤖 LLM Form Orchestrator - Starting")
        run_logger.log_text(f"   User data: {user_data}")
    
    # 2. Detect form fields (using existing JavaScript code)
    # This would use the same page.evaluate() from form_fill.py
    # For now, we'll integrate with existing deterministic_form_fill
    
    # 3. Get available operations
    operations = get_available_operations()
    
    # 4. Create prompt for LLM
    # Note: This requires integration with existing form detection
    # For MVP, we can create a simplified version
    
    if run_logger:
        run_logger.log_text("   ℹ️  LLM orchestration is in BETA - falling back to hybrid mode")
    
    return None  # Will be implemented in integration


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
