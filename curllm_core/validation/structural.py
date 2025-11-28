"""
Structural Validator - DOM and data structure validation

Validates task completion by analyzing:
- DOM structure changes
- Form field states
- Data extraction completeness
- Page state transitions
"""

from typing import Any, Dict, List, Optional
from .composite import ValidationCheck


class StructuralValidator:
    """
    Structural validation based on DOM and data analysis.
    
    Checks:
    - Form fields filled correctly
    - Expected elements present/absent
    - Data extraction structure validity
    - Page state changes
    """
    
    def __init__(self):
        pass
    
    async def validate(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]] = None,
        expected: Optional[Dict[str, Any]] = None
    ) -> ValidationCheck:
        """
        Validate result structurally.
        
        Args:
            instruction: Original user instruction
            result: Task execution result
            page_context: Current page state
            expected: Expected outcome
            
        Returns:
            ValidationCheck with structural analysis
        """
        checks_passed = 0
        checks_total = 0
        issues = []
        details = {}
        
        # 1. Check basic result structure
        struct_check = self._check_result_structure(result, instruction)
        checks_total += 1
        if struct_check['passed']:
            checks_passed += 1
        else:
            issues.append(struct_check['issue'])
        details['structure'] = struct_check
        
        # 2. Check form-specific structure if applicable
        if self._is_form_task(instruction):
            form_check = self._check_form_structure(result, page_context)
            checks_total += 1
            if form_check['passed']:
                checks_passed += 1
            else:
                issues.append(form_check['issue'])
            details['form'] = form_check
        
        # 3. Check extraction structure if applicable
        if self._is_extraction_task(instruction):
            extract_check = self._check_extraction_structure(result, instruction)
            checks_total += 1
            if extract_check['passed']:
                checks_passed += 1
            else:
                issues.append(extract_check['issue'])
            details['extraction'] = extract_check
        
        # 4. Check expected values if provided
        if expected:
            expected_check = self._check_expected_values(result, expected)
            checks_total += 1
            if expected_check['passed']:
                checks_passed += 1
            else:
                issues.append(expected_check['issue'])
            details['expected'] = expected_check
        
        # 5. Check page context if provided
        if page_context:
            page_check = self._check_page_context(page_context, instruction)
            checks_total += 1
            if page_check['passed']:
                checks_passed += 1
            else:
                issues.append(page_check['issue'])
            details['page'] = page_check
        
        score = checks_passed / checks_total if checks_total > 0 else 0.5
        passed = score >= 0.6
        
        return ValidationCheck(
            name='structural',
            passed=passed,
            score=score,
            message=f"Structural: {checks_passed}/{checks_total} checks passed" + 
                    (f". Issues: {', '.join(issues[:2])}" if issues else ""),
            details=details
        )
    
    def _check_result_structure(
        self,
        result: Dict[str, Any],
        instruction: str
    ) -> Dict[str, Any]:
        """Check basic result structure"""
        issues = []
        
        # Must have some result data
        if not result:
            return {
                'passed': False,
                'issue': 'Empty result',
                'details': {'reason': 'Result is None or empty'}
            }
        
        # Check for error indicators
        if result.get('error'):
            return {
                'passed': False,
                'issue': f"Error in result: {result.get('error')}",
                'details': {'error': result.get('error')}
            }
        
        # Check success flag if present
        if 'success' in result and not result['success']:
            return {
                'passed': False,
                'issue': 'Success flag is False',
                'details': {'success': False}
            }
        
        # Check for meaningful data
        has_data = any(
            result.get(key) 
            for key in ['data', 'form_fill', 'products', 'links', 
                        'articles', 'emails', 'phones', 'result']
        )
        
        if not has_data and result.get('steps_taken', 0) == 0:
            return {
                'passed': False,
                'issue': 'No data and no steps taken',
                'details': {'empty_result': True}
            }
        
        return {
            'passed': True,
            'issue': None,
            'details': {'valid_structure': True}
        }
    
    def _check_form_structure(
        self,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check form-specific structure"""
        
        form_fill = result.get('form_fill', {})
        
        if not form_fill:
            return {
                'passed': False,
                'issue': 'No form_fill data in result',
                'details': {'missing': 'form_fill'}
            }
        
        # Check if form was submitted
        submitted = form_fill.get('submitted', False)
        
        # Check filled fields
        filled = form_fill.get('filled', {})
        errors = form_fill.get('errors', {})
        
        if errors:
            return {
                'passed': False,
                'issue': f"Form errors: {list(errors.keys())}",
                'details': {
                    'submitted': submitted,
                    'filled_count': len(filled),
                    'errors': errors
                }
            }
        
        if not submitted:
            return {
                'passed': False,
                'issue': 'Form not submitted',
                'details': {
                    'submitted': False,
                    'filled_count': len(filled)
                }
            }
        
        return {
            'passed': True,
            'issue': None,
            'details': {
                'submitted': True,
                'filled_count': len(filled),
                'fields': list(filled.keys())
            }
        }
    
    def _check_extraction_structure(
        self,
        result: Dict[str, Any],
        instruction: str
    ) -> Dict[str, Any]:
        """Check extraction-specific structure"""
        
        # Find extracted data
        extracted_data = None
        extraction_type = None
        
        for key in ['products', 'links', 'articles', 'emails', 'phones', 'data']:
            if result.get(key):
                extracted_data = result[key]
                extraction_type = key
                break
        
        if not extracted_data:
            return {
                'passed': False,
                'issue': 'No extracted data found',
                'details': {'extraction_type': None}
            }
        
        # Check data is a list
        if not isinstance(extracted_data, list):
            return {
                'passed': False,
                'issue': f'{extraction_type} is not a list',
                'details': {
                    'extraction_type': extraction_type,
                    'actual_type': type(extracted_data).__name__
                }
            }
        
        # Check non-empty
        if len(extracted_data) == 0:
            return {
                'passed': False,
                'issue': f'Empty {extraction_type} list',
                'details': {
                    'extraction_type': extraction_type,
                    'count': 0
                }
            }
        
        # Check item structure
        first_item = extracted_data[0]
        if extraction_type == 'products':
            required_fields = ['name', 'price']
            missing = [f for f in required_fields if f not in first_item]
            if missing:
                return {
                    'passed': False,
                    'issue': f'Products missing fields: {missing}',
                    'details': {
                        'extraction_type': extraction_type,
                        'count': len(extracted_data),
                        'missing_fields': missing
                    }
                }
        
        return {
            'passed': True,
            'issue': None,
            'details': {
                'extraction_type': extraction_type,
                'count': len(extracted_data),
                'sample_keys': list(first_item.keys()) if isinstance(first_item, dict) else None
            }
        }
    
    def _check_expected_values(
        self,
        result: Dict[str, Any],
        expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check against expected values"""
        
        mismatches = []
        matches = 0
        total = 0
        
        for key, expected_val in expected.items():
            total += 1
            actual_val = self._deep_get(result, key)
            
            if actual_val == expected_val:
                matches += 1
            elif isinstance(expected_val, (int, float)) and isinstance(actual_val, (int, float)):
                if abs(actual_val - expected_val) / max(abs(expected_val), 1) < 0.1:
                    matches += 1
            elif str(expected_val).lower() in str(actual_val).lower():
                matches += 1
            else:
                mismatches.append({
                    'key': key,
                    'expected': expected_val,
                    'actual': actual_val
                })
        
        passed = matches / total >= 0.7 if total > 0 else True
        
        return {
            'passed': passed,
            'issue': f'{len(mismatches)} value mismatches' if mismatches else None,
            'details': {
                'matches': matches,
                'total': total,
                'mismatches': mismatches[:3]  # Limit details
            }
        }
    
    def _check_page_context(
        self,
        page_context: Dict[str, Any],
        instruction: str
    ) -> Dict[str, Any]:
        """Check page context state"""
        
        issues = []
        
        # Check for error page indicators
        title = page_context.get('title', '')
        url = page_context.get('url', '')
        
        error_indicators = ['404', '500', 'error', 'not found', 'forbidden']
        for indicator in error_indicators:
            if indicator in title.lower() or indicator in url.lower():
                issues.append(f'Error indicator in page: {indicator}')
        
        # Check if on expected page type
        if 'form' in instruction.lower():
            forms = page_context.get('forms', [])
            if not forms:
                issues.append('No forms found on page')
        
        return {
            'passed': len(issues) == 0,
            'issue': issues[0] if issues else None,
            'details': {
                'url': url,
                'title': title[:50],
                'issues': issues
            }
        }
    
    def _is_form_task(self, instruction: str) -> bool:
        """Check if instruction is form-related"""
        keywords = ['fill', 'form', 'submit', 'login', 'register', 
                    'formularz', 'wypełnij', 'wyślij']
        return any(kw in instruction.lower() for kw in keywords)
    
    def _is_extraction_task(self, instruction: str) -> bool:
        """Check if instruction is extraction-related"""
        keywords = ['extract', 'get', 'find', 'scrape', 'collect',
                    'wyciągnij', 'pobierz', 'znajdź']
        return any(kw in instruction.lower() for kw in keywords)
    
    def _deep_get(self, data: Dict, key: str) -> Any:
        """Get nested value from dict using dot notation"""
        keys = key.split('.')
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value

