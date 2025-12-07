#!/usr/bin/env python3
"""
Result Corrector - LLM-based validation and correction of extraction results.

Detects missing fields from instruction and attempts to fix them.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CorrectionResult:
    """Result of correction attempt."""
    
    corrected: bool = False
    original_data: Any = None
    corrected_data: Any = None
    missing_fields: List[str] = field(default_factory=list)
    added_fields: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# Keywords that indicate required fields in instructions
FIELD_KEYWORDS = {
    "price": ["price", "cena", "ceny", "koszt", "cost", "zł", "pln", "$", "€", "eur", "usd"],
    "name": ["name", "nazwa", "nazwy", "title", "tytuł", "product", "produkt"],
    "url": ["url", "link", "href", "address", "adres"],
    "image": ["image", "img", "photo", "zdjęcie", "obrazek", "picture"],
    "description": ["description", "opis", "details", "szczegóły"],
    "stock": ["stock", "availability", "dostępność", "magazyn", "ilość"],
    "rating": ["rating", "ocena", "stars", "gwiazdki", "review"],
    "category": ["category", "kategoria", "type", "typ"],
    "brand": ["brand", "marka", "manufacturer", "producent"],
    "sku": ["sku", "code", "kod", "id", "numer"],
}


def detect_required_fields(instruction: str) -> List[str]:
    """
    Detect which fields are required based on instruction text.
    
    Args:
        instruction: User instruction
        
    Returns:
        List of required field names
    """
    instruction_lower = instruction.lower()
    required = []
    
    for field_name, keywords in FIELD_KEYWORDS.items():
        for keyword in keywords:
            if keyword in instruction_lower:
                if field_name not in required:
                    required.append(field_name)
                break
    
    # If no specific fields detected, assume minimum required for products
    if not required and any(kw in instruction_lower for kw in ["product", "produkt", "item", "towar"]):
        required = ["name", "price", "url"]
    
    return required


def check_fields_present(data: Any, required_fields: List[str]) -> Tuple[List[str], List[str]]:
    """
    Check which required fields are present and missing.
    
    Args:
        data: Extracted data (dict or list of dicts)
        required_fields: List of required field names
        
    Returns:
        (present_fields, missing_fields)
    """
    if not data:
        return [], required_fields.copy()
    
    # Get sample item
    sample = None
    if isinstance(data, dict):
        if "items" in data:
            sample = data["items"][0] if data["items"] else None
        elif "specifications" in data:
            sample = data["specifications"]
        else:
            sample = data
    elif isinstance(data, list) and data:
        sample = data[0]
    
    if not sample or not isinstance(sample, dict):
        return [], required_fields.copy()
    
    # Check fields
    sample_keys = set(sample.keys())
    present = [f for f in required_fields if f in sample_keys]
    missing = [f for f in required_fields if f not in sample_keys]
    
    return present, missing


def validate_field_values(data: Any, field_name: str) -> List[str]:
    """
    Validate that field values are reasonable.
    
    Returns list of issues found.
    """
    issues = []
    
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and "items" in data:
        items = data["items"]
    elif isinstance(data, dict):
        items = [data]
    
    for i, item in enumerate(items[:10]):  # Check first 10 items
        if not isinstance(item, dict):
            continue
        
        value = item.get(field_name)
        
        if value is None:
            continue
        
        if field_name == "price":
            # Price should be numeric or contain price pattern
            if isinstance(value, str):
                if not re.search(r'\d', value):
                    issues.append(f"Item {i}: price '{value}' has no numeric value")
        
        elif field_name == "url":
            if isinstance(value, str):
                if value.startswith("javascript:"):
                    issues.append(f"Item {i}: url is JavaScript, not real link")
                elif not value.startswith(("http://", "https://", "/")):
                    issues.append(f"Item {i}: url '{value[:50]}' looks invalid")
        
        elif field_name == "name":
            if isinstance(value, str):
                if len(value) < 3:
                    issues.append(f"Item {i}: name '{value}' is too short")
    
    return issues


def generate_correction_prompt(
    instruction: str,
    current_data: Any,
    missing_fields: List[str],
    page_html: Optional[str] = None
) -> str:
    """Generate prompt for LLM to correct/complete extraction."""
    
    sample = None
    if isinstance(current_data, dict):
        sample = current_data.get("items", [current_data])[:2]
    elif isinstance(current_data, list):
        sample = current_data[:2]
    
    prompt = f"""The following data was extracted but is INCOMPLETE.

Original instruction: "{instruction}"

Current extracted data (sample):
```json
{json.dumps(sample, indent=2, ensure_ascii=False)[:1500]}
```

MISSING REQUIRED FIELDS: {', '.join(missing_fields)}

The user asked for data including {', '.join(missing_fields)} but these fields are not in the results.

Please analyze why these fields might be missing and suggest:
1. CSS selectors to extract the missing fields
2. If the page doesn't contain this data, explain why
3. Alternative approach to get this data

Respond in JSON format:
```json
{{
  "missing_field_analysis": {{
    "field_name": {{
      "likely_reason": "why this field is missing",
      "suggested_selector": "CSS selector to extract it",
      "alternative_approach": "what else to try"
    }}
  }},
  "can_be_fixed": true/false,
  "requires_page_navigation": true/false
}}
```
"""
    return prompt


async def correct_with_llm(
    instruction: str,
    data: Any,
    missing_fields: List[str],
    llm_client: Any,
    page_html: Optional[str] = None
) -> CorrectionResult:
    """
    Use LLM to analyze and suggest corrections for missing fields.
    
    Args:
        instruction: Original user instruction
        data: Current extracted data
        missing_fields: List of missing field names
        llm_client: LLM client for corrections
        page_html: Optional page HTML for context
        
    Returns:
        CorrectionResult with analysis and suggestions
    """
    result = CorrectionResult(
        original_data=data,
        missing_fields=missing_fields.copy(),
    )
    
    if not missing_fields:
        return result
    
    prompt = generate_correction_prompt(instruction, data, missing_fields, page_html)
    
    try:
        response = await llm_client.generate(prompt)
        
        # Parse response
        try:
            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(1))
            else:
                analysis = json.loads(response)
            
            # Extract suggestions
            for field, info in analysis.get("missing_field_analysis", {}).items():
                if isinstance(info, dict):
                    selector = info.get("suggested_selector", "")
                    if selector:
                        result.suggestions.append(f"For {field}: try selector '{selector}'")
                    
                    reason = info.get("likely_reason", "")
                    if reason:
                        result.issues.append(f"{field}: {reason}")
            
            if analysis.get("requires_page_navigation"):
                result.suggestions.append("May need to navigate to detail pages to get missing data")
                
        except json.JSONDecodeError:
            result.issues.append(f"Could not parse LLM response")
            
    except Exception as e:
        logger.warning(f"LLM correction failed: {e}")
        result.issues.append(f"LLM analysis failed: {str(e)}")
    
    return result


def analyze_and_report(
    instruction: str,
    data: Any,
    run_logger=None
) -> CorrectionResult:
    """
    Analyze extraction results against instruction and report issues.
    
    This is a synchronous version that doesn't use LLM.
    
    Args:
        instruction: User instruction
        data: Extracted data
        run_logger: Optional logger
        
    Returns:
        CorrectionResult with analysis
    """
    result = CorrectionResult(original_data=data)
    
    # Detect required fields from instruction
    required = detect_required_fields(instruction)
    
    if not required:
        return result
    
    # Check which fields are present/missing
    present, missing = check_fields_present(data, required)
    result.missing_fields = missing
    
    if run_logger and missing:
        run_logger.log_text(f"\n⚠️ **Missing fields detected:**")
        run_logger.log_text(f"   Instruction mentions: {', '.join(required)}")
        run_logger.log_text(f"   Present in results: {', '.join(present) or 'none'}")
        run_logger.log_text(f"   **Missing: {', '.join(missing)}**")
    
    # Validate present fields
    for field in present:
        issues = validate_field_values(data, field)
        result.issues.extend(issues)
    
    if run_logger and result.issues:
        run_logger.log_text(f"\n⚠️ **Field value issues:**")
        for issue in result.issues[:5]:
            run_logger.log_text(f"   - {issue}")
    
    # Generate suggestions
    if "price" in missing:
        result.suggestions.append("Add price selector to DSL strategy (e.g., '.price', '[class*=price]')")
    if "description" in missing:
        result.suggestions.append("Add description selector (e.g., '.description', 'p.desc')")
    
    if run_logger and result.suggestions:
        run_logger.log_text(f"\n💡 **Suggestions:**")
        for suggestion in result.suggestions:
            run_logger.log_text(f"   - {suggestion}")
    
    return result
