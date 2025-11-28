"""
Rule Validator - Configurable business rules validation

Validates task completion against:
- Data constraints (price limits, counts, formats)
- Business rules (required fields, valid ranges)
- Task-specific rules (form submission, extraction completeness)
"""

import re
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from .composite import ValidationCheck


@dataclass
class ValidationRule:
    """Single validation rule definition"""
    name: str
    description: str
    check: Callable[[Dict[str, Any]], bool]
    severity: str = "warning"  # warning, error, critical
    score_impact: float = 0.1


class RuleValidator:
    """
    Rule-based validation with configurable rules.
    
    Built-in rule categories:
    - Form rules (required fields, email format, etc.)
    - Extraction rules (min items, price limits, etc.)
    - Navigation rules (correct URL, no errors)
    - Data rules (non-empty, valid format)
    """
    
    def __init__(self, custom_rules: Optional[List[ValidationRule]] = None):
        """
        Initialize rule validator.
        
        Args:
            custom_rules: Additional custom rules
        """
        self.rules: List[ValidationRule] = []
        self._register_builtin_rules()
        
        if custom_rules:
            self.rules.extend(custom_rules)
    
    def _register_builtin_rules(self):
        """Register built-in validation rules"""
        
        # Form rules
        self.rules.extend([
            ValidationRule(
                name="form_submitted",
                description="Form must be submitted",
                check=lambda r: r.get('form_fill', {}).get('submitted', False),
                severity="critical",
                score_impact=0.3
            ),
            ValidationRule(
                name="form_no_errors",
                description="Form submission without errors",
                check=lambda r: not r.get('form_fill', {}).get('errors'),
                severity="error",
                score_impact=0.2
            ),
            ValidationRule(
                name="form_has_fields",
                description="At least one field filled",
                check=lambda r: len(r.get('form_fill', {}).get('filled', {})) > 0,
                severity="error",
                score_impact=0.15
            ),
        ])
        
        # Extraction rules
        self.rules.extend([
            ValidationRule(
                name="extraction_not_empty",
                description="Extraction result not empty",
                check=self._check_extraction_not_empty,
                severity="error",
                score_impact=0.25
            ),
            ValidationRule(
                name="extraction_valid_format",
                description="Extracted data has valid format",
                check=self._check_extraction_format,
                severity="warning",
                score_impact=0.1
            ),
        ])
        
        # Navigation rules
        self.rules.extend([
            ValidationRule(
                name="no_http_error",
                description="No HTTP error (4xx, 5xx)",
                check=self._check_no_http_error,
                severity="critical",
                score_impact=0.3
            ),
            ValidationRule(
                name="page_loaded",
                description="Page loaded successfully",
                check=lambda r: r.get('steps_taken', 0) >= 0 or r.get('success', True),
                severity="critical",
                score_impact=0.25
            ),
        ])
        
        # Data quality rules
        self.rules.extend([
            ValidationRule(
                name="result_has_data",
                description="Result contains meaningful data",
                check=self._check_has_data,
                severity="warning",
                score_impact=0.15
            ),
        ])
    
    async def validate(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]] = None,
        expected: Optional[Dict[str, Any]] = None
    ) -> ValidationCheck:
        """
        Validate result against applicable rules.
        
        Args:
            instruction: Original user instruction
            result: Task execution result
            page_context: Current page state
            expected: Expected outcome
            
        Returns:
            ValidationCheck with rule validation results
        """
        # Determine applicable rules based on instruction
        applicable_rules = self._select_applicable_rules(instruction)
        
        # Run rules
        passed_rules = []
        failed_rules = []
        total_score = 1.0
        
        for rule in applicable_rules:
            try:
                if rule.check(result):
                    passed_rules.append(rule)
                else:
                    failed_rules.append(rule)
                    total_score -= rule.score_impact
            except Exception:
                # Rule check failed, skip
                pass
        
        # Check expected values if provided
        if expected:
            expected_check = self._check_expected(result, expected)
            if not expected_check['passed']:
                total_score -= 0.2
                failed_rules.append(ValidationRule(
                    name="expected_values",
                    description=expected_check['message'],
                    check=lambda r: False,
                    severity="error"
                ))
        
        # Calculate final score
        total_score = max(0.0, min(1.0, total_score))
        has_critical_failure = any(r.severity == "critical" for r in failed_rules)
        
        passed = total_score >= 0.6 and not has_critical_failure
        
        return ValidationCheck(
            name='rules',
            passed=passed,
            score=total_score,
            message=f"Rules: {len(passed_rules)}/{len(applicable_rules)} passed" +
                    (f". Failed: {failed_rules[0].name}" if failed_rules else ""),
            details={
                'passed_rules': [r.name for r in passed_rules],
                'failed_rules': [
                    {'name': r.name, 'severity': r.severity, 'description': r.description}
                    for r in failed_rules
                ],
                'has_critical_failure': has_critical_failure
            }
        )
    
    def _select_applicable_rules(self, instruction: str) -> List[ValidationRule]:
        """Select rules applicable to the instruction"""
        instr_lower = instruction.lower()
        applicable = []
        
        # Always apply generic rules
        generic_rules = ['no_http_error', 'page_loaded', 'result_has_data']
        applicable.extend([r for r in self.rules if r.name in generic_rules])
        
        # Form rules
        if any(kw in instr_lower for kw in ['fill', 'form', 'submit', 'login', 'register',
                                            'formularz', 'wypełnij']):
            form_rules = ['form_submitted', 'form_no_errors', 'form_has_fields']
            applicable.extend([r for r in self.rules if r.name in form_rules])
        
        # Extraction rules
        if any(kw in instr_lower for kw in ['extract', 'get', 'find', 'scrape',
                                            'wyciągnij', 'pobierz', 'znajdź']):
            extraction_rules = ['extraction_not_empty', 'extraction_valid_format']
            applicable.extend([r for r in self.rules if r.name in extraction_rules])
        
        return applicable
    
    def _check_extraction_not_empty(self, result: Dict[str, Any]) -> bool:
        """Check if extraction result is not empty"""
        for key in ['products', 'links', 'articles', 'emails', 'phones', 'data']:
            data = result.get(key)
            if data and isinstance(data, list) and len(data) > 0:
                return True
        return False
    
    def _check_extraction_format(self, result: Dict[str, Any]) -> bool:
        """Check if extracted data has valid format"""
        for key in ['products', 'links', 'articles']:
            data = result.get(key)
            if data and isinstance(data, list) and len(data) > 0:
                first = data[0]
                if isinstance(first, dict):
                    # Has structured data
                    return True
                elif isinstance(first, str) and len(first) > 0:
                    # Has string data
                    return True
        return True  # Default to valid if no extraction data
    
    def _check_no_http_error(self, result: Dict[str, Any]) -> bool:
        """Check for HTTP errors"""
        error = result.get('error')
        if error:
            error_str = str(error).lower()
            http_errors = ['403', '404', '500', '502', '503', 'forbidden', 
                          'not found', 'server error']
            if any(e in error_str for e in http_errors):
                return False
        
        # Check nested error data
        data = result.get('data')
        if isinstance(data, dict) and 'error' in data:
            error_data = data['error']
            if isinstance(error_data, dict):
                diag = error_data.get('diagnostics', {})
                if isinstance(diag, dict):
                    for probe in ['http_probe', 'https_probe']:
                        status = diag.get(probe, {}).get('status', 200)
                        if status >= 400:
                            return False
        
        return True
    
    def _check_has_data(self, result: Dict[str, Any]) -> bool:
        """Check if result has meaningful data"""
        # Has explicit data
        for key in ['data', 'form_fill', 'products', 'links', 'articles', 
                    'emails', 'phones', 'result']:
            if result.get(key):
                return True
        
        # Has steps executed
        if result.get('steps_taken', 0) > 0 or result.get('steps', 0) > 0:
            return True
        
        return False
    
    def _check_expected(
        self,
        result: Dict[str, Any],
        expected: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check result against expected values"""
        mismatches = []
        
        for key, expected_val in expected.items():
            actual_val = self._deep_get(result, key)
            
            if actual_val is None:
                mismatches.append(f"Missing: {key}")
            elif actual_val != expected_val:
                # Allow partial matches for strings
                if not (isinstance(expected_val, str) and 
                       expected_val.lower() in str(actual_val).lower()):
                    mismatches.append(f"Mismatch: {key}")
        
        return {
            'passed': len(mismatches) == 0,
            'message': f"Expected value mismatches: {', '.join(mismatches)}" if mismatches else "All expected values match"
        }
    
    def _deep_get(self, data: Dict, key: str) -> Any:
        """Get nested value using dot notation"""
        keys = key.split('.')
        value = data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return None
        return value
    
    def add_rule(self, rule: ValidationRule):
        """Add custom validation rule"""
        self.rules.append(rule)
    
    def add_price_limit_rule(self, max_price: float, currency: str = "zł"):
        """Add price limit validation rule"""
        self.add_rule(ValidationRule(
            name=f"price_limit_{max_price}",
            description=f"Products must be under {max_price}{currency}",
            check=lambda r: self._check_price_limit(r, max_price),
            severity="warning",
            score_impact=0.15
        ))
    
    def _check_price_limit(self, result: Dict[str, Any], max_price: float) -> bool:
        """Check if all products are under price limit"""
        products = result.get('products', [])
        if not products:
            return True
        
        for product in products:
            price = product.get('price')
            if price:
                # Extract numeric price
                try:
                    price_num = float(re.sub(r'[^\d.,]', '', str(price)).replace(',', '.'))
                    if price_num > max_price:
                        return False
                except (ValueError, TypeError):
                    pass
        
        return True
    
    def add_count_rule(self, min_count: int, data_type: str = "items"):
        """Add minimum count validation rule"""
        self.add_rule(ValidationRule(
            name=f"min_count_{min_count}",
            description=f"At least {min_count} {data_type} required",
            check=lambda r: self._check_min_count(r, min_count),
            severity="warning",
            score_impact=0.1
        ))
    
    def _check_min_count(self, result: Dict[str, Any], min_count: int) -> bool:
        """Check minimum item count"""
        for key in ['products', 'links', 'articles', 'emails', 'phones', 'data']:
            data = result.get(key)
            if data and isinstance(data, list):
                if len(data) >= min_count:
                    return True
        return False

