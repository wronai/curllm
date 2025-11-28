"""
Semantic Validator - LLM-based understanding of task completion

Uses LLM to understand if the result matches the user's intent,
not just structural matching.
"""

import json
from typing import Any, Dict, Optional
from .composite import ValidationCheck


class SemanticValidator:
    """
    Semantic validation using LLM understanding.
    
    Evaluates:
    - Did the result match user's intent?
    - Is the data quality acceptable?
    - Are there logical inconsistencies?
    """
    
    def __init__(self, llm=None):
        self.llm = llm
    
    async def validate(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]] = None,
        expected: Optional[Dict[str, Any]] = None
    ) -> ValidationCheck:
        """
        Validate result semantically using LLM.
        
        Args:
            instruction: Original user instruction
            result: Task execution result
            page_context: Current page state
            expected: Expected outcome (optional)
            
        Returns:
            ValidationCheck with semantic analysis
        """
        if not self.llm:
            return ValidationCheck(
                name='semantic',
                passed=True,
                score=0.5,
                message="Semantic validation skipped (no LLM)",
                details={'skipped': True}
            )
        
        # Build validation prompt
        prompt = self._build_validation_prompt(
            instruction, result, page_context, expected
        )
        
        try:
            # Call LLM
            response = await self.llm.ainvoke(prompt)
            text = response.get('text', '')
            
            # Parse response
            validation = self._parse_response(text)
            
            return ValidationCheck(
                name='semantic',
                passed=validation['passed'],
                score=validation['score'],
                message=validation['reason'],
                details={
                    'intent_match': validation.get('intent_match', False),
                    'data_quality': validation.get('data_quality', 0.5),
                    'completeness': validation.get('completeness', 0.5),
                    'llm_reasoning': validation.get('reasoning', '')
                }
            )
            
        except Exception as e:
            return ValidationCheck(
                name='semantic',
                passed=False,
                score=0.0,
                message=f"Semantic validation error: {str(e)}",
                details={'error': str(e)}
            )
    
    def _build_validation_prompt(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]],
        expected: Optional[Dict[str, Any]]
    ) -> str:
        """Build LLM prompt for semantic validation"""
        
        result_summary = self._summarize_result(result)
        
        prompt = f"""Analyze if this task was completed successfully.

USER INSTRUCTION:
{instruction}

EXECUTION RESULT:
{result_summary}
"""
        
        if expected:
            prompt += f"""
EXPECTED OUTCOME:
{json.dumps(expected, indent=2, ensure_ascii=False)[:500]}
"""
        
        if page_context:
            url = page_context.get('url', 'unknown')
            title = page_context.get('title', 'unknown')
            prompt += f"""
CURRENT PAGE:
- URL: {url}
- Title: {title}
"""
        
        prompt += """
EVALUATE and respond with JSON:
{
    "passed": true/false,
    "score": 0.0-1.0,
    "reason": "Brief explanation",
    "intent_match": true/false,
    "data_quality": 0.0-1.0,
    "completeness": 0.0-1.0,
    "reasoning": "Detailed analysis"
}

SCORING GUIDELINES:
- 1.0: Perfect match to user intent
- 0.8-0.9: Good result with minor deviations
- 0.6-0.7: Partial success
- 0.3-0.5: Significant issues
- 0.0-0.2: Failed or wrong result

JSON:"""
        
        return prompt
    
    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Create concise result summary for LLM"""
        summary_parts = []
        
        if result.get('success'):
            summary_parts.append("- Status: SUCCESS")
        else:
            summary_parts.append("- Status: FAILED")
            if result.get('error'):
                summary_parts.append(f"- Error: {result.get('error')}")
        
        # Form filling results
        if 'form_fill' in result:
            ff = result['form_fill']
            summary_parts.append(f"- Form submitted: {ff.get('submitted', False)}")
            filled = ff.get('filled', {})
            summary_parts.append(f"- Fields filled: {list(filled.keys())}")
        
        # Extraction results
        for key in ['products', 'links', 'articles', 'emails', 'phones']:
            if key in result and result[key]:
                items = result[key]
                summary_parts.append(f"- {key}: {len(items)} items extracted")
                if items and len(items) > 0:
                    sample = str(items[0])[:100]
                    summary_parts.append(f"  Sample: {sample}...")
        
        # Navigation
        if 'url' in result:
            summary_parts.append(f"- Final URL: {result['url']}")
        
        # Steps taken
        if 'steps' in result or 'steps_taken' in result:
            steps = result.get('steps', result.get('steps_taken', 0))
            summary_parts.append(f"- Steps executed: {steps}")
        
        return "\n".join(summary_parts) if summary_parts else str(result)[:500]
    
    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Parse LLM response to extract validation result"""
        # Try to extract JSON
        try:
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                json_str = text[start:end+1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Fallback: analyze text for keywords
        text_lower = text.lower()
        
        if any(w in text_lower for w in ['success', 'passed', 'correct', 'complete']):
            return {
                'passed': True,
                'score': 0.75,
                'reason': 'LLM indicated success (inferred from text)',
                'intent_match': True,
                'data_quality': 0.7,
                'completeness': 0.7
            }
        elif any(w in text_lower for w in ['fail', 'error', 'wrong', 'incorrect']):
            return {
                'passed': False,
                'score': 0.25,
                'reason': 'LLM indicated failure (inferred from text)',
                'intent_match': False,
                'data_quality': 0.3,
                'completeness': 0.3
            }
        else:
            return {
                'passed': True,
                'score': 0.5,
                'reason': 'Could not determine result (assuming partial)',
                'intent_match': True,
                'data_quality': 0.5,
                'completeness': 0.5
            }


# Task-specific semantic validators
class FormSemanticValidator(SemanticValidator):
    """Specialized semantic validator for form tasks"""
    
    async def validate(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]] = None,
        expected: Optional[Dict[str, Any]] = None
    ) -> ValidationCheck:
        """Validate form-specific semantics"""
        
        # Parse expected values from instruction
        expected_values = self._parse_form_values(instruction)
        
        # Get actual filled values
        actual_values = {}
        if 'form_fill' in result:
            actual_values = result['form_fill'].get('filled', {})
        
        # Check each expected field
        matches = 0
        total = len(expected_values)
        mismatches = []
        
        for field, expected_val in expected_values.items():
            actual_val = actual_values.get(field, '')
            if expected_val.lower() in str(actual_val).lower():
                matches += 1
            else:
                mismatches.append(f"{field}: expected '{expected_val}', got '{actual_val}'")
        
        score = matches / total if total > 0 else 0.5
        passed = score >= 0.7 and result.get('form_fill', {}).get('submitted', False)
        
        return ValidationCheck(
            name='semantic',
            passed=passed,
            score=score,
            message=f"Form validation: {matches}/{total} fields match",
            details={
                'expected_values': expected_values,
                'actual_values': actual_values,
                'mismatches': mismatches,
                'submitted': result.get('form_fill', {}).get('submitted', False)
            }
        )
    
    def _parse_form_values(self, instruction: str) -> Dict[str, str]:
        """Extract expected field values from instruction"""
        import re
        values = {}
        
        # Pattern: field=value or field: value
        patterns = [
            r'(\w+)\s*=\s*["\']?([^,\'"]+)["\']?',
            r'(\w+)\s*:\s*["\']?([^,\'"]+)["\']?'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, instruction):
                field = match.group(1).lower()
                value = match.group(2).strip()
                values[field] = value
        
        return values


class ExtractionSemanticValidator(SemanticValidator):
    """Specialized semantic validator for extraction tasks"""
    
    async def validate(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]] = None,
        expected: Optional[Dict[str, Any]] = None
    ) -> ValidationCheck:
        """Validate extraction semantics"""
        
        # Detect extraction type from instruction
        extraction_type = self._detect_extraction_type(instruction)
        
        # Get extracted data
        extracted = result.get(extraction_type, [])
        
        # Check constraints
        constraints = self._parse_constraints(instruction)
        
        valid_items = 0
        total_items = len(extracted)
        
        for item in extracted:
            if self._item_matches_constraints(item, constraints):
                valid_items += 1
        
        score = valid_items / total_items if total_items > 0 else 0.0
        passed = total_items > 0 and score >= 0.5
        
        return ValidationCheck(
            name='semantic',
            passed=passed,
            score=score,
            message=f"Extraction: {valid_items}/{total_items} items match constraints",
            details={
                'extraction_type': extraction_type,
                'total_extracted': total_items,
                'valid_items': valid_items,
                'constraints': constraints
            }
        )
    
    def _detect_extraction_type(self, instruction: str) -> str:
        """Detect what type of data to extract"""
        instr_lower = instruction.lower()
        
        if any(w in instr_lower for w in ['product', 'produkt', 'price', 'cena']):
            return 'products'
        elif any(w in instr_lower for w in ['article', 'artykuł', 'news', 'wpis']):
            return 'articles'
        elif 'email' in instr_lower:
            return 'emails'
        elif any(w in instr_lower for w in ['phone', 'telefon']):
            return 'phones'
        else:
            return 'links'
    
    def _parse_constraints(self, instruction: str) -> Dict[str, Any]:
        """Parse extraction constraints from instruction"""
        import re
        constraints = {}
        
        # Price constraints
        price_match = re.search(r'(under|below|max|poniżej|do)\s*(\d+)', instruction, re.I)
        if price_match:
            constraints['max_price'] = int(price_match.group(2))
        
        price_min_match = re.search(r'(above|over|min|powyżej|od)\s*(\d+)', instruction, re.I)
        if price_min_match:
            constraints['min_price'] = int(price_min_match.group(2))
        
        # Count constraints
        count_match = re.search(r'(first|top|pierwsz\w+)\s*(\d+)', instruction, re.I)
        if count_match:
            constraints['max_count'] = int(count_match.group(2))
        
        return constraints
    
    def _item_matches_constraints(self, item: Any, constraints: Dict[str, Any]) -> bool:
        """Check if item matches constraints"""
        if not isinstance(item, dict):
            return True
        
        # Price check
        price = item.get('price')
        if price is not None:
            try:
                # Extract numeric price
                import re
                price_num = float(re.sub(r'[^\d.,]', '', str(price)).replace(',', '.'))
                
                if 'max_price' in constraints and price_num > constraints['max_price']:
                    return False
                if 'min_price' in constraints and price_num < constraints['min_price']:
                    return False
            except (ValueError, TypeError):
                pass
        
        return True

