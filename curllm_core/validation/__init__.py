"""
Multi-Strategy Validation System for CurLLM

Provides multiple validation approaches to verify task completion:
1. Semantic Validation - LLM-based understanding of results vs expectations
2. Structural Validation - DOM/data structure comparison
3. Visual Validation - Screenshot comparison and visual element detection
4. Rule-based Validation - Configurable business rules
5. Task Validation - Combined multi-strategy validator with scoring
"""

from .semantic import SemanticValidator
from .structural import StructuralValidator
from .visual import VisualValidator
from .rules import RuleValidator
from .composite import CompositeValidator, ValidationResult
from .task_validator import TaskValidator, ValidationReport, validate_task

__all__ = [
    'SemanticValidator',
    'StructuralValidator', 
    'VisualValidator',
    'RuleValidator',
    'CompositeValidator',
    'ValidationResult',
    'TaskValidator',
    'ValidationReport',
    'validate_task'
]

