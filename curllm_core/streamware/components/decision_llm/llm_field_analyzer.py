from typing import Any, Dict, List, Optional



class LLMFieldAnalyzer:
    """
    LLM-driven field analyzer - no hardcoded field types or names.
    """
    
    def __init__(self, llm=None):
        self.llm = llm
    
    async def is_fillable_field(self, field: Dict) -> bool:
        """
        Use LLM to determine if a field is fillable.
        
        Falls back to simple heuristics when LLM unavailable.
        """
        if not self.llm:
            return self._is_fillable_heuristic(field)
        
        try:
            field_info = {
                'type': field.get('type', 'text'),
                'name': field.get('name', ''),
                'id': field.get('id', ''),
                'placeholder': field.get('placeholder', ''),
            }
            
            prompt = f"""Is this form field meant for user text input?

Field: {field_info}

Respond with just: YES or NO"""

            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return 'YES' in content.upper()
        except Exception:
            return self._is_fillable_heuristic(field)
    
    def _is_fillable_heuristic(self, field: Dict) -> bool:
        """Fallback heuristic for fillable detection."""
        field_type = field.get('type', 'text').lower()
        # Common input types that accept text
        return field_type in ['text', 'email', 'tel', 'textarea', 'password', 
                               'search', 'url', 'number']
    
    async def extract_fields_from_instruction(
        self, 
        instruction: str,
        available_fields: List[Dict]
    ) -> Dict[str, str]:
        """
        Use LLM to extract field values from natural language instruction.
        
        Args:
            instruction: User's instruction (e.g., "Fill with name John, email john@test.com")
            available_fields: List of field dicts from the form
            
        Returns:
            Dict mapping field names to values
        """
        if not self.llm:
            return self._extract_fields_heuristic(instruction)
        
        try:
            field_names = [f.get('name') or f.get('id') or f.get('placeholder', '') 
                          for f in available_fields]
            
            prompt = f"""Extract form field values from this instruction.

Instruction: "{instruction}"

Available form fields: {field_names}

Extract any values the user wants to fill. Respond with JSON:
{{"field_name": "value", ...}}

Only include fields where you can clearly identify a value."""

            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            import json
            import re
            json_match = re.search(r'\{[^}]+\}', content)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.debug(f"LLM field extraction failed: {e}")
        
        return self._extract_fields_heuristic(instruction)
    
    def _extract_fields_heuristic(self, instruction: str) -> Dict[str, str]:
        """Fallback heuristic for field extraction."""
        fields = {}
        
        # Simple key=value parsing
        parts = instruction.replace(':', '=').split(',')
        for part in parts:
            if '=' in part:
                key_val = part.split('=', 1)
                if len(key_val) == 2:
                    key = key_val[0].strip().lower()
                    val = key_val[1].strip()
                    if key and val:
                        fields[key] = val
        
        return fields
