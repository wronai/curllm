"""
Composite Validator - Combines multiple validation strategies

Provides a unified interface for running multiple validators
and aggregating their results with configurable weights.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import json


class ValidationStatus(Enum):
    """Validation result status"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ValidationCheck:
    """Single validation check result"""
    name: str
    passed: bool
    score: float  # 0.0 to 1.0
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Aggregated validation result"""
    status: ValidationStatus
    overall_score: float  # 0.0 to 1.0
    passed: bool
    checks: List[ValidationCheck] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'status': self.status.value,
            'overall_score': self.overall_score,
            'passed': self.passed,
            'checks': [
                {
                    'name': c.name,
                    'passed': c.passed,
                    'score': c.score,
                    'message': c.message,
                    'details': c.details
                }
                for c in self.checks
            ],
            'summary': self.summary,
            'recommendations': self.recommendations,
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class CompositeValidator:
    """
    Composite validator that combines multiple validation strategies.
    
    Supports:
    - Weighted scoring from multiple validators
    - Configurable thresholds
    - Early exit on critical failures
    - Detailed reporting with recommendations
    """
    
    def __init__(
        self,
        llm=None,
        success_threshold: float = 0.7,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize composite validator.
        
        Args:
            llm: LLM client for semantic validation
            success_threshold: Minimum score to pass (0.0 to 1.0)
            weights: Validator weights (default: equal weights)
        """
        self.llm = llm
        self.success_threshold = success_threshold
        self.weights = weights or {
            'semantic': 0.3,
            'structural': 0.3,
            'visual': 0.2,
            'rules': 0.2
        }
        
        # Initialize validators lazily
        self._semantic = None
        self._structural = None
        self._visual = None
        self._rules = None
    
    @property
    def semantic(self):
        """Lazy-load semantic validator"""
        if self._semantic is None:
            from .semantic import SemanticValidator
            self._semantic = SemanticValidator(self.llm)
        return self._semantic
    
    @property
    def structural(self):
        """Lazy-load structural validator"""
        if self._structural is None:
            from .structural import StructuralValidator
            self._structural = StructuralValidator()
        return self._structural
    
    @property
    def visual(self):
        """Lazy-load visual validator"""
        if self._visual is None:
            from .visual import VisualValidator
            self._visual = VisualValidator()
        return self._visual
    
    @property
    def rules(self):
        """Lazy-load rule validator"""
        if self._rules is None:
            from .rules import RuleValidator
            self._rules = RuleValidator()
        return self._rules
    
    async def validate(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]] = None,
        screenshot: Optional[bytes] = None,
        expected: Optional[Dict[str, Any]] = None,
        validators: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Run validation using multiple strategies.
        
        Args:
            instruction: Original user instruction
            result: Task execution result
            page_context: Current page state (DOM, forms, etc.)
            screenshot: Screenshot bytes for visual validation
            expected: Expected outcome for comparison
            validators: List of validators to use (default: all applicable)
            
        Returns:
            ValidationResult with aggregated scores and recommendations
        """
        checks = []
        
        # Determine which validators to run
        if validators is None:
            validators = self._select_validators(instruction, result, page_context, screenshot)
        
        # Run selected validators
        for validator_name in validators:
            try:
                check = await self._run_validator(
                    validator_name,
                    instruction,
                    result,
                    page_context,
                    screenshot,
                    expected
                )
                if check:
                    checks.append(check)
            except Exception as e:
                checks.append(ValidationCheck(
                    name=validator_name,
                    passed=False,
                    score=0.0,
                    message=f"Validator error: {str(e)}",
                    details={'error': str(e)}
                ))
        
        # Calculate weighted score
        total_weight = 0.0
        weighted_score = 0.0
        
        for check in checks:
            weight = self.weights.get(check.name, 0.1)
            weighted_score += check.score * weight
            total_weight += weight
        
        overall_score = weighted_score / total_weight if total_weight > 0 else 0.0
        
        # Determine status
        passed = overall_score >= self.success_threshold
        failed_critical = any(
            not c.passed and c.details.get('critical', False)
            for c in checks
        )
        
        if failed_critical:
            status = ValidationStatus.FAILURE
            passed = False
        elif passed:
            status = ValidationStatus.SUCCESS
        elif overall_score >= 0.5:
            status = ValidationStatus.PARTIAL
        else:
            status = ValidationStatus.FAILURE
        
        # Generate summary and recommendations
        summary = self._generate_summary(instruction, checks, overall_score)
        recommendations = self._generate_recommendations(checks, result)
        
        return ValidationResult(
            status=status,
            overall_score=overall_score,
            passed=passed,
            checks=checks,
            summary=summary,
            recommendations=recommendations,
            metadata={
                'instruction': instruction,
                'validators_used': validators,
                'threshold': self.success_threshold
            }
        )
    
    def _select_validators(
        self,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]],
        screenshot: Optional[bytes]
    ) -> List[str]:
        """Select applicable validators based on context"""
        validators = []
        
        # Always use structural validation if we have result data
        if result:
            validators.append('structural')
        
        # Use semantic validation if LLM is available
        if self.llm:
            validators.append('semantic')
        
        # Use visual validation if screenshot provided
        if screenshot:
            validators.append('visual')
        
        # Always use rule-based validation
        validators.append('rules')
        
        return validators
    
    async def _run_validator(
        self,
        name: str,
        instruction: str,
        result: Dict[str, Any],
        page_context: Optional[Dict[str, Any]],
        screenshot: Optional[bytes],
        expected: Optional[Dict[str, Any]]
    ) -> Optional[ValidationCheck]:
        """Run a single validator"""
        
        if name == 'semantic' and self.llm:
            return await self.semantic.validate(
                instruction, result, page_context, expected
            )
        elif name == 'structural':
            return await self.structural.validate(
                instruction, result, page_context, expected
            )
        elif name == 'visual' and screenshot:
            return await self.visual.validate(
                instruction, result, screenshot, expected
            )
        elif name == 'rules':
            return await self.rules.validate(
                instruction, result, page_context, expected
            )
        
        return None
    
    def _generate_summary(
        self,
        instruction: str,
        checks: List[ValidationCheck],
        score: float
    ) -> str:
        """Generate human-readable summary"""
        passed = sum(1 for c in checks if c.passed)
        total = len(checks)
        
        if score >= 0.9:
            quality = "excellent"
        elif score >= 0.7:
            quality = "good"
        elif score >= 0.5:
            quality = "partial"
        else:
            quality = "poor"
        
        return (
            f"Validation {quality} ({score:.0%}). "
            f"{passed}/{total} checks passed for: {instruction[:100]}"
        )
    
    def _generate_recommendations(
        self,
        checks: List[ValidationCheck],
        result: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        for check in checks:
            if not check.passed:
                if check.name == 'structural':
                    recommendations.append(
                        f"Structural issue: {check.message}. "
                        "Try adjusting selectors or waiting for dynamic content."
                    )
                elif check.name == 'semantic':
                    recommendations.append(
                        f"Semantic mismatch: {check.message}. "
                        "Verify instruction clarity and page state."
                    )
                elif check.name == 'visual':
                    recommendations.append(
                        f"Visual issue: {check.message}. "
                        "Check for overlays, modals, or page layout changes."
                    )
                elif check.name == 'rules':
                    recommendations.append(
                        f"Rule violation: {check.message}. "
                        "Review business rules and constraints."
                    )
        
        return recommendations


# Convenience function
async def validate_task_result(
    instruction: str,
    result: Dict[str, Any],
    llm=None,
    page_context: Optional[Dict[str, Any]] = None,
    screenshot: Optional[bytes] = None,
    expected: Optional[Dict[str, Any]] = None
) -> ValidationResult:
    """
    Quick validation of task execution result.
    
    Example:
        result = await run_task("Fill form with name=John")
        validation = await validate_task_result(
            "Fill form with name=John",
            result,
            llm=llm_client
        )
        if validation.passed:
            print("Task completed successfully!")
        else:
            print(f"Issues: {validation.recommendations}")
    """
    validator = CompositeValidator(llm=llm)
    return await validator.validate(
        instruction, result, page_context, screenshot, expected
    )

