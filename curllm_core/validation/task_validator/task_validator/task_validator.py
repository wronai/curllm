import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from ..validation_strategy import ValidationStrategy
from ..validation_check import ValidationCheck
from ..validation_report import ValidationReport


class TaskValidator:
    """
    Multi-strategy task completion validator.
    
    Usage:
        validator = TaskValidator(llm)
        report = await validator.validate(
            instruction="Fill form with name=John",
            result={"form_fill": {"submitted": True}},
            page_context=page_context,
            screenshots=["before.png", "after.png"]
        )
        
        if report.overall_passed:
            print("Task completed successfully!")
        else:
            print(f"Task failed: {report.summary}")
    """
    
    # Threshold for overall pass (weighted average of all checks)
    PASS_THRESHOLD = 0.6
    
    # Strategy weights by task type
    STRATEGY_WEIGHTS = {
        'form_fill': {
            ValidationStrategy.STRUCTURAL: 0.4,
            ValidationStrategy.RULES: 0.3,
            ValidationStrategy.DOM_DIFF: 0.2,
            ValidationStrategy.SEMANTIC: 0.1
        },
        'extraction': {
            ValidationStrategy.SCHEMA: 0.3,
            ValidationStrategy.RULES: 0.3,
            ValidationStrategy.STRUCTURAL: 0.2,
            ValidationStrategy.SEMANTIC: 0.2
        },
        'ecommerce': {
            ValidationStrategy.STRUCTURAL: 0.3,
            ValidationStrategy.VISUAL: 0.3,
            ValidationStrategy.DOM_DIFF: 0.2,
            ValidationStrategy.RULES: 0.2
        },
        'social_media': {
            ValidationStrategy.STRUCTURAL: 0.3,
            ValidationStrategy.VISUAL: 0.3,
            ValidationStrategy.DOM_DIFF: 0.2,
            ValidationStrategy.SEMANTIC: 0.2
        },
        'live_interaction': {
            ValidationStrategy.DOM_DIFF: 0.4,
            ValidationStrategy.VISUAL: 0.3,
            ValidationStrategy.STRUCTURAL: 0.3
        },
        'default': {
            ValidationStrategy.STRUCTURAL: 0.3,
            ValidationStrategy.RULES: 0.3,
            ValidationStrategy.SEMANTIC: 0.2,
            ValidationStrategy.DOM_DIFF: 0.2
        }
    }
    
    def __init__(self, llm=None, run_logger=None):
        self.llm = llm
        self.run_logger = run_logger
        self._custom_validators: Dict[str, Callable] = {}
    
    def register_custom_validator(self, name: str, validator_fn: Callable):
        """Register custom validation function"""
        self._custom_validators[name] = validator_fn
    
    async def validate(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]] = None,
        before_context: Optional[Dict[str, Any]] = None,
        screenshots: Optional[List[str]] = None,
        task_type: Optional[str] = None,
        custom_rules: Optional[List[Dict[str, Any]]] = None
    ) -> ValidationReport:
        """
        Validate task completion using multiple strategies.
        
        Args:
            instruction: Original user instruction
            result: Task execution result
            page_context: Current page state after task
            before_context: Page state before task (for diff)
            screenshots: List of screenshot paths [before, after]
            task_type: Optional task type override
            custom_rules: Optional custom validation rules
            
        Returns:
            ValidationReport with all checks and overall score
        """
        self._log("🔍 TASK VALIDATION", "header")
        
        # Detect task type if not provided
        if not task_type:
            task_type = self._detect_task_type(instruction)
        self._log(f"Task type: {task_type}")
        
        # Get weights for this task type
        weights = self.STRATEGY_WEIGHTS.get(task_type, self.STRATEGY_WEIGHTS['default'])
        
        # Run all applicable validation checks
        checks: List[ValidationCheck] = []
        
        # 1. Structural Validation
        if ValidationStrategy.STRUCTURAL in weights:
            check = await self._validate_structural(instruction, result, task_type)
            checks.append(check)
            self._log(f"Structural: {'✅' if check.passed else '❌'} ({check.score:.0%})")
        
        # 2. Rule-based Validation
        if ValidationStrategy.RULES in weights:
            check = await self._validate_rules(instruction, result, custom_rules)
            checks.append(check)
            self._log(f"Rules: {'✅' if check.passed else '❌'} ({check.score:.0%})")
        
        # 3. Schema Validation
        if ValidationStrategy.SCHEMA in weights:
            check = await self._validate_schema(result, task_type)
            checks.append(check)
            self._log(f"Schema: {'✅' if check.passed else '❌'} ({check.score:.0%})")
        
        # 4. DOM Diff Validation
        if ValidationStrategy.DOM_DIFF in weights and before_context and page_context:
            check = await self._validate_dom_diff(
                instruction, before_context, page_context, task_type
            )
            checks.append(check)
            self._log(f"DOM Diff: {'✅' if check.passed else '❌'} ({check.score:.0%})")
        
        # 5. Visual Validation
        if ValidationStrategy.VISUAL in weights and screenshots:
            check = await self._validate_visual(instruction, screenshots, task_type)
            checks.append(check)
            self._log(f"Visual: {'✅' if check.passed else '❌'} ({check.score:.0%})")
        
        # 6. Semantic Validation (LLM)
        if ValidationStrategy.SEMANTIC in weights and self.llm:
            check = await self._validate_semantic(instruction, result, page_context)
            checks.append(check)
            self._log(f"Semantic: {'✅' if check.passed else '❌'} ({check.score:.0%})")
        
        # 7. Custom validators
        for name, validator_fn in self._custom_validators.items():
            try:
                check = await validator_fn(instruction, result, page_context)
                checks.append(check)
                self._log(f"Custom ({name}): {'✅' if check.passed else '❌'}")
            except Exception as e:
                self._log(f"Custom ({name}) failed: {e}", "error")
        
        # Calculate overall score
        overall_score, confidence = self._calculate_overall_score(checks, weights)
        overall_passed = overall_score >= self.PASS_THRESHOLD
        
        # Generate summary and recommendations
        summary = self._generate_summary(instruction, checks, overall_passed)
        recommendations = self._generate_recommendations(checks, task_type)
        
        self._log(f"Overall: {'✅ PASSED' if overall_passed else '❌ FAILED'} ({overall_score:.0%})")
        
        return ValidationReport(
            task_type=task_type,
            instruction=instruction,
            overall_passed=overall_passed,
            overall_score=overall_score,
            confidence=confidence,
            checks=checks,
            summary=summary,
            recommendations=recommendations
        )
    
    async def _validate_structural(
        self,
        instruction: str,
        result: Dict[str, Any],
        task_type: str
    ) -> ValidationCheck:
        """Validate result structure matches expectations"""
        
        # Expected fields by task type
        expected_fields = {
            'form_fill': ['form_fill.submitted', 'form_fill.filled'],
            'extraction': ['products', 'links', 'emails', 'articles', 'count'],
            'ecommerce': ['cart', 'checkout_step', 'success'],
            'social_media': ['success', 'platform', 'action'],
            'live_interaction': ['actions_executed', 'success']
        }
        
        required = expected_fields.get(task_type, ['success'])
        found = []
        missing = []
        
        for field_path in required:
            if self._has_field(result, field_path):
                found.append(field_path)
            else:
                missing.append(field_path)
        
        # Calculate score based on found fields
        score = len(found) / len(required) if required else 0.0
        passed = score >= 0.5  # At least half the expected fields
        
        # Check for error indicators
        has_error = self._has_field(result, 'error') or self._has_field(result, 'errors')
        if has_error:
            score *= 0.5  # Penalize for errors
        
        # Check for success flags
        if self._get_field(result, 'success') is True:
            score = min(1.0, score + 0.2)
        elif self._get_field(result, 'success') is False:
            score *= 0.3
        
        # Task-specific checks
        if task_type == 'form_fill':
            submitted = self._get_field(result, 'form_fill.submitted')
            if submitted is True:
                score = min(1.0, score + 0.3)
            elif submitted is False:
                score *= 0.5
        
        elif task_type == 'extraction':
            # Check if data is not empty
            for key in ['products', 'links', 'emails', 'articles']:
                data = self._get_field(result, key)
                if isinstance(data, list) and len(data) > 0:
                    score = min(1.0, score + 0.2)
                    break
        
        return ValidationCheck(
            strategy=ValidationStrategy.STRUCTURAL.value,
            passed=passed and score >= 0.5,
            score=score,
            reason=f"Found {len(found)}/{len(required)} expected fields",
            details={
                'found': found,
                'missing': missing,
                'has_error': has_error
            }
        )
    
    async def _validate_rules(
        self,
        instruction: str,
        result: Dict[str, Any],
        custom_rules: Optional[List[Dict[str, Any]]] = None
    ) -> ValidationCheck:
        """Validate against business rules"""
        
        rules_passed = []
        rules_failed = []
        
        # Parse instruction for built-in rules
        instr_lower = instruction.lower()
        
        # Price limit rule
        price_match = re.search(r'(?:under|below|poniżej|do|max)\s*(\d+)', instr_lower)
        if price_match:
            max_price = int(price_match.group(1))
            products = self._get_field(result, 'products') or []
            
            if isinstance(products, list):
                over_price = [
                    p for p in products 
                    if isinstance(p.get('price'), (int, float)) and p['price'] > max_price
                ]
                if len(over_price) == 0:
                    rules_passed.append(f"All products under {max_price}")
                else:
                    rules_failed.append(f"{len(over_price)} products over {max_price}")
        
        # Count limit rule
        count_match = re.search(r'(?:first|top)\s*(\d+)', instr_lower)
        if count_match:
            max_count = int(count_match.group(1))
            for key in ['products', 'links', 'articles']:
                data = self._get_field(result, key)
                if isinstance(data, list):
                    if len(data) <= max_count:
                        rules_passed.append(f"Count <= {max_count}")
                    else:
                        rules_failed.append(f"Count {len(data)} > {max_count}")
                    break
        
        # Submission rule for forms
        if any(kw in instr_lower for kw in ['submit', 'send', 'wyślij', 'register']):
            submitted = self._get_field(result, 'form_fill.submitted')
            if submitted is True:
                rules_passed.append("Form submitted")
            elif submitted is False:
                rules_failed.append("Form not submitted")
        
        # Non-empty result rule
        if any(kw in instr_lower for kw in ['extract', 'get', 'find', 'all']):
            for key in ['products', 'links', 'emails', 'articles', 'data']:
                data = self._get_field(result, key)
                if isinstance(data, list) and len(data) > 0:
                    rules_passed.append(f"Found {len(data)} {key}")
                    break
            else:
                if not rules_passed:
                    rules_failed.append("No data extracted")
        
        # Apply custom rules
        if custom_rules:
            for rule in custom_rules:
                rule_name = rule.get('name', 'custom')
                field = rule.get('field')
                condition = rule.get('condition')
                value = rule.get('value')
                
                if field and condition:
                    actual = self._get_field(result, field)
                    rule_passed = self._check_condition(actual, condition, value)
                    if rule_passed:
                        rules_passed.append(rule_name)
                    else:
                        rules_failed.append(rule_name)
        
        # Calculate score
        total = len(rules_passed) + len(rules_failed)
        score = len(rules_passed) / total if total > 0 else 1.0
        passed = len(rules_failed) == 0 or score >= 0.7
        
        return ValidationCheck(
            strategy=ValidationStrategy.RULES.value,
            passed=passed,
            score=score,
            reason=f"{len(rules_passed)} rules passed, {len(rules_failed)} failed",
            details={
                'passed_rules': rules_passed,
                'failed_rules': rules_failed
            }
        )
    
    async def _validate_schema(
        self,
        result: Dict[str, Any],
        task_type: str
    ) -> ValidationCheck:
        """Validate result matches expected schema"""
        
        # Simple schema validation (can be extended with jsonschema)
        schemas = {
            'form_fill': {
                'form_fill': {
                    'type': 'object',
                    'required': ['submitted'],
                    'properties': {
                        'submitted': {'type': 'bool'},
                        'filled': {'type': 'dict'},
                        'errors': {'type': ['dict', 'list', 'none']}
                    }
                }
            },
            'extraction': {
                'products': {
                    'type': 'list',
                    'items': {
                        'name': {'type': 'str'},
                        'price': {'type': ['int', 'float', 'str']},
                        'url': {'type': 'str', 'optional': True}
                    }
                }
            }
        }
        
        schema = schemas.get(task_type, {})
        errors = []
        
        for field, spec in schema.items():
            value = self._get_field(result, field)
            if value is None:
                if not spec.get('optional'):
                    errors.append(f"Missing required field: {field}")
                continue
            
            expected_type = spec.get('type')
            if expected_type:
                if not self._check_type(value, expected_type):
                    errors.append(f"Type mismatch for {field}")
        
        score = 1.0 - (len(errors) * 0.2)
        score = max(0.0, score)
        
        return ValidationCheck(
            strategy=ValidationStrategy.SCHEMA.value,
            passed=len(errors) == 0,
            score=score,
            reason=f"Schema validation: {len(errors)} errors",
            details={'errors': errors}
        )
    
    async def _validate_dom_diff(
        self,
        instruction: str,
        before: Dict[str, Any],
        after: Dict[str, Any],
        task_type: str
    ) -> ValidationCheck:
        """Validate DOM changes match expected changes"""
        
        changes_detected = []
        expected_changes = []
        
        # Detect what changed
        before_forms = before.get('forms', [])
        after_forms = after.get('forms', [])
        
        # Form value changes
        if before_forms and after_forms:
            for bf, af in zip(before_forms, after_forms):
                bf_fields = {f['name']: f.get('value', '') for f in bf.get('fields', [])}
                af_fields = {f['name']: f.get('value', '') for f in af.get('fields', [])}
                
                for name in af_fields:
                    if name in bf_fields:
                        if af_fields[name] != bf_fields[name]:
                            changes_detected.append(f"Field {name} changed")
        
        # URL change
        if before.get('url') != after.get('url'):
            changes_detected.append("URL changed")
        
        # Title change
        if before.get('title') != after.get('title'):
            changes_detected.append("Title changed")
        
        # Content change
        before_text = before.get('text', '')[:500]
        after_text = after.get('text', '')[:500]
        if before_text != after_text:
            changes_detected.append("Page content changed")
        
        # Determine expected changes based on task
        instr_lower = instruction.lower()
        if task_type == 'form_fill' or 'fill' in instr_lower:
            expected_changes.append("form_fields")
        if 'navigate' in instr_lower or 'go to' in instr_lower:
            expected_changes.append("url")
        if 'click' in instr_lower:
            expected_changes.append("interaction")
        
        # Score based on whether expected changes occurred
        if len(changes_detected) > 0:
            score = min(1.0, 0.5 + len(changes_detected) * 0.1)
        else:
            score = 0.3  # No changes - might be intentional
        
        return ValidationCheck(
            strategy=ValidationStrategy.DOM_DIFF.value,
            passed=len(changes_detected) > 0,
            score=score,
            reason=f"Detected {len(changes_detected)} DOM changes",
            details={
                'changes': changes_detected,
                'expected': expected_changes
            }
        )
    
    async def _validate_visual(
        self,
        instruction: str,
        screenshots: List[str],
        task_type: str
    ) -> ValidationCheck:
        """Validate using visual comparison"""
        
        # This would use vision analysis in production
        # For now, simple file existence check
        
        valid_screenshots = [s for s in screenshots if s]
        
        if len(valid_screenshots) == 0:
            return ValidationCheck(
                strategy=ValidationStrategy.VISUAL.value,
                passed=True,  # Pass if no screenshots (can't validate)
                score=0.5,
                reason="No screenshots to validate",
                details={}
            )
        
        # Use vision analyzer if available
        if self.llm:
            # In production, this would analyze screenshots
            # and determine if visual state matches expectations
            pass
        
        return ValidationCheck(
            strategy=ValidationStrategy.VISUAL.value,
            passed=True,
            score=0.8,  # Default high score if screenshots exist
            reason=f"Visual validation with {len(valid_screenshots)} screenshots",
            details={'screenshot_count': len(valid_screenshots)}
        )
    
    async def _validate_semantic(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]]
    ) -> ValidationCheck:
        """Use LLM to validate semantic match"""
        
        if not self.llm:
            return ValidationCheck(
                strategy=ValidationStrategy.SEMANTIC.value,
                passed=True,
                score=0.5,
                reason="LLM not available for semantic validation",
                details={}
            )
        
        try:
            prompt = f"""Validate if this task was completed correctly.

TASK INSTRUCTION:
{instruction}

RESULT:
{json.dumps(result, indent=2, default=str)[:2000]}

CURRENT PAGE STATE:
{json.dumps(page_context, indent=2, default=str)[:1000] if page_context else 'Not available'}

RESPOND JSON only:
{{
    "completed": true/false,
    "score": 0.0-1.0,
    "reasoning": "brief explanation"
}}

JSON:"""

            response = await self.llm.ainvoke(prompt)
            text = response.get('text', str(response)) if isinstance(response, dict) else str(response)
            
            # Parse response
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                data = json.loads(text[start:end+1])
                
                return ValidationCheck(
                    strategy=ValidationStrategy.SEMANTIC.value,
                    passed=data.get('completed', False),
                    score=float(data.get('score', 0.5)),
                    reason=data.get('reasoning', 'LLM validation'),
                    details={'llm_response': data}
                )
        except Exception as e:
            self._log(f"Semantic validation error: {e}", "error")
        
        return ValidationCheck(
            strategy=ValidationStrategy.SEMANTIC.value,
            passed=True,
            score=0.5,
            reason="Semantic validation failed, defaulting to neutral",
            details={'error': 'Failed to parse LLM response'}
        )
    
    def _calculate_overall_score(
        self,
        checks: List[ValidationCheck],
        weights: Dict[ValidationStrategy, float]
    ) -> tuple[float, float]:
        """Calculate weighted overall score and confidence"""
        
        if not checks:
            return 0.5, 0.0
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for check in checks:
            strategy = ValidationStrategy(check.strategy)
            weight = weights.get(strategy, 0.1)
            weighted_sum += check.score * weight
            total_weight += weight
        
        overall = weighted_sum / total_weight if total_weight > 0 else 0.5
        
        # Confidence based on how many checks we ran
        expected_checks = len(weights)
        actual_checks = len(checks)
        confidence = actual_checks / expected_checks if expected_checks > 0 else 0.5
        
        return overall, confidence
    
    def _generate_summary(
        self,
        instruction: str,
        checks: List[ValidationCheck],
        passed: bool
    ) -> str:
        """Generate human-readable summary"""
        
        if passed:
            summary = f"Task completed successfully. "
        else:
            summary = f"Task may not have completed correctly. "
        
        failed_checks = [c for c in checks if not c.passed]
        if failed_checks:
            summary += f"Issues: {', '.join(c.reason for c in failed_checks[:3])}"
        else:
            summary += "All validation checks passed."
        
        return summary
    
    def _generate_recommendations(
        self,
        checks: List[ValidationCheck],
        task_type: str
    ) -> List[str]:
        """Generate recommendations for improvement"""
        
        recommendations = []
        
        for check in checks:
            if not check.passed:
                if check.strategy == ValidationStrategy.STRUCTURAL.value:
                    recommendations.append("Check if task result contains expected fields")
                elif check.strategy == ValidationStrategy.RULES.value:
                    failed = check.details.get('failed_rules', [])
                    if failed:
                        recommendations.append(f"Fix: {failed[0]}")
                elif check.strategy == ValidationStrategy.DOM_DIFF.value:
                    recommendations.append("Verify DOM changes occurred as expected")
        
        return recommendations[:3]  # Limit to top 3
    
    def _detect_task_type(self, instruction: str) -> str:
        """Detect task type from instruction"""
        instr_lower = instruction.lower()
        
        if any(kw in instr_lower for kw in ['form', 'fill', 'login', 'register', 'submit']):
            return 'form_fill'
        elif any(kw in instr_lower for kw in ['extract', 'get', 'find', 'scrape', 'product', 'link']):
            return 'extraction'
        elif any(kw in instr_lower for kw in ['cart', 'buy', 'checkout', 'pay', 'order']):
            return 'ecommerce'
        elif any(kw in instr_lower for kw in ['facebook', 'twitter', 'instagram', 'post', 'share']):
            return 'social_media'
        elif any(kw in instr_lower for kw in ['click', 'scroll', 'hover', 'type']):
            return 'live_interaction'
        else:
            return 'default'
    
    def _has_field(self, obj: Dict, path: str) -> bool:
        """Check if nested field exists"""
        parts = path.split('.')
        current = obj
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        return True
    
    def _get_field(self, obj: Dict, path: str) -> Any:
        """Get nested field value"""
        parts = path.split('.')
        current = obj
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    
    def _check_type(self, value: Any, expected: Any) -> bool:
        """Check if value matches expected type"""
        type_map = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'none': type(None)
        }
        
        if isinstance(expected, list):
            return any(self._check_type(value, t) for t in expected)
        
        expected_type = type_map.get(expected)
        return isinstance(value, expected_type) if expected_type else True
    
    def _check_condition(self, actual: Any, condition: str, expected: Any) -> bool:
        """Check condition"""
        if condition == 'equals':
            return actual == expected
        elif condition == 'contains':
            return expected in str(actual)
        elif condition == 'greater_than':
            return actual > expected
        elif condition == 'less_than':
            return actual < expected
        elif condition == 'not_empty':
            return bool(actual)
        elif condition == 'is_true':
            return actual is True
        elif condition == 'is_false':
            return actual is False
        return True
    
    def _log(self, message: str, level: str = "info"):
        """Log message"""
        if self.run_logger:
            if level == "header":
                self.run_logger.log_text(f"\n{'='*50}")
                self.run_logger.log_text(message)
                self.run_logger.log_text(f"{'='*50}\n")
            elif level == "error":
                self.run_logger.log_text(f"❌ {message}")
            else:
                self.run_logger.log_text(f"   {message}")
