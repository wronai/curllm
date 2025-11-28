"""
Vision Form Analysis - Detect visible form fields and honeypots.
"""
import json
import re
from typing import Dict, List, Any, Optional


async def analyze_form_fields_vision(
    llm,
    screenshot_path: str,
    dom_forms: List[Dict[str, Any]],
    instruction: str,
    run_logger=None
) -> Dict[str, Any]:
    """
    Analyze form fields using vision model to detect visible fields and honeypots.
    
    Args:
        llm: LLM client with vision capabilities
        screenshot_path: Path to screenshot image
        dom_forms: Form data extracted from DOM
        instruction: User instruction for form filling
        run_logger: Optional logger
    
    Returns:
        {
            "visible_fields": [...],
            "honeypot_fields": [...],
            "field_mapping": {...},
            "recommended_fill_order": [...]
        }
    """
    if run_logger:
        run_logger.log_text("🔍 Vision form analysis: analyzing screenshot")
    
    # Build form summary
    all_fields = []
    for form_idx, form in enumerate(dom_forms[:3]):
        form_id = form.get("id", f"form_{form_idx}")
        fields = form.get("fields", [])
        visible_fields = [
            f for f in fields 
            if f.get("visible", True) and f.get("type") not in ["hidden", "submit"]
        ]
        
        for field in visible_fields:
            all_fields.append({
                "form_id": form_id,
                "name": field.get("name", ""),
                "type": field.get("type", ""),
                "required": field.get("required", False)
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
    prompt = _build_form_analysis_prompt(instruction, all_fields)
    
    try:
        if hasattr(llm, 'ainvoke_with_image'):
            result = await llm.ainvoke_with_image(prompt, screenshot_path)
            response_text = result.get("text", "")
        else:
            if run_logger:
                run_logger.log_text("   LLM does not support vision")
            return _fallback_result(all_fields)
        
        # Parse response
        parsed = _parse_vision_response(response_text)
        
        if run_logger:
            run_logger.log_text(f"   Found {len(parsed.get('visible_fields', []))} visible fields")
            if parsed.get('honeypot_fields'):
                run_logger.log_text(f"   Detected {len(parsed['honeypot_fields'])} honeypots")
        
        return parsed
        
    except Exception as e:
        if run_logger:
            run_logger.log_text(f"   Vision analysis error: {e}")
        return _fallback_result(all_fields)


def _build_form_analysis_prompt(
    instruction: str,
    all_fields: List[Dict]
) -> str:
    """Build prompt for form field analysis."""
    fields_list = "\n".join([
        f"- {f['name']} ({f['type']}){' *required' if f.get('required') else ''}" 
        for f in all_fields[:20]
    ])
    
    return f"""Analyze this form screenshot to identify VISIBLE fields and detect honeypots.

**User instruction:** {instruction}

**DOM-detected fields (may include honeypots):**
{fields_list}

**Your task:**
1. Identify ALL VISIBLE form fields in the screenshot
2. Detect HONEYPOT fields (exist in DOM but NOT visible):
   - Fields positioned off-screen
   - Fields with zero size
   - Fields hidden by CSS
   - Fields with no visible label
3. Map visible fields to canonical names (name, email, phone, message)
4. Determine fill order (top to bottom)

Return JSON:
{{
    "visible_fields": [
        {{"name": "field_name", "type": "text/email/etc", "label": "visible label", "priority": 1}}
    ],
    "honeypot_fields": [
        {{"name": "field_name", "reason": "why it's a honeypot"}}
    ],
    "field_mapping": {{
        "dom_field_name": {{"canonical": "email", "confidence": 0.9}}
    }},
    "recommended_fill_order": ["email", "name", "message"]
}}

JSON:"""


def _parse_vision_response(response: str) -> Dict[str, Any]:
    """Parse vision LLM response."""
    try:
        # Find JSON in response
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception:
        pass
    
    return {
        "visible_fields": [],
        "honeypot_fields": [],
        "field_mapping": {},
        "recommended_fill_order": []
    }


def _fallback_result(all_fields: List[Dict]) -> Dict[str, Any]:
    """Generate fallback result when vision analysis fails."""
    visible_fields = []
    for i, field in enumerate(all_fields):
        visible_fields.append({
            "name": field["name"],
            "type": field["type"],
            "label": field["name"],
            "priority": i + 1
        })
    
    return {
        "visible_fields": visible_fields,
        "honeypot_fields": [],
        "field_mapping": {},
        "recommended_fill_order": [f["name"] for f in visible_fields]
    }


class VisionFormAnalyzer:
    """
    Stateful form analyzer using vision.
    
    Caches analysis results for efficiency.
    """
    
    def __init__(self, llm=None):
        self.llm = llm
        self._cache: Dict[str, Dict] = {}
    
    async def analyze(
        self,
        screenshot_path: str,
        dom_forms: List[Dict],
        instruction: str,
        run_logger=None
    ) -> Dict[str, Any]:
        """
        Analyze form with caching.
        
        Args:
            screenshot_path: Path to screenshot
            dom_forms: DOM form data
            instruction: User instruction
            run_logger: Optional logger
            
        Returns:
            Analysis result
        """
        # Simple cache key
        cache_key = f"{screenshot_path}:{len(dom_forms)}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = await analyze_form_fields_vision(
            llm=self.llm,
            screenshot_path=screenshot_path,
            dom_forms=dom_forms,
            instruction=instruction,
            run_logger=run_logger
        )
        
        self._cache[cache_key] = result
        return result
    
    def clear_cache(self):
        """Clear analysis cache."""
        self._cache = {}
    
    def filter_honeypots(
        self,
        fields: List[Dict],
        analysis: Dict[str, Any]
    ) -> List[Dict]:
        """
        Filter out honeypot fields.
        
        Args:
            fields: All detected fields
            analysis: Vision analysis result
            
        Returns:
            Fields without honeypots
        """
        honeypot_names = {
            h["name"] for h in analysis.get("honeypot_fields", [])
        }
        
        return [f for f in fields if f.get("name") not in honeypot_names]
    
    def get_fill_order(
        self,
        fields: List[Dict],
        analysis: Dict[str, Any]
    ) -> List[Dict]:
        """
        Get fields in recommended fill order.
        
        Args:
            fields: Available fields
            analysis: Vision analysis result
            
        Returns:
            Fields ordered for filling
        """
        order = analysis.get("recommended_fill_order", [])
        if not order:
            return fields
        
        # Create lookup
        field_map = {f.get("name"): f for f in fields}
        
        # Order fields
        ordered = []
        for name in order:
            if name in field_map:
                ordered.append(field_map.pop(name))
        
        # Add remaining
        ordered.extend(field_map.values())
        
        return ordered
