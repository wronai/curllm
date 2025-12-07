"""
Result Validator - Intelligent validation of orchestrator results

This module provides comprehensive validation of task execution results
using multiple verification methods.
"""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation strictness level"""
    LENIENT = "lenient"      # Accept if no errors found
    NORMAL = "normal"        # Require some success indicator OR no errors
    STRICT = "strict"        # Require success indicator AND no errors
    PARANOID = "paranoid"    # Require multiple success indicators


@dataclass
class ValidationResult:
    """Result of validation check"""
    is_valid: bool
    confidence: float
    method: str
    details: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ResultValidator:
    """
    Validates orchestrator execution results.
    
    Uses multiple methods:
    1. Content analysis (success/error indicators)
    2. DOM state verification
    3. URL change detection
    4. Visual confirmation (when available)
    """
    
    # Success indicators (PL + EN)
    SUCCESS_INDICATORS = [
        # Polish
        "dziękujemy", "dziekujemy", "dziękuję", "dziekuje",
        "sukces", "udało się", "udalo sie", "gotowe", "zakończono",
        "wysłano", "wyslano", "przesłano", "przeslano",
        "zapisano", "dodano", "utworzono", "zarejestrowano",
        "wiadomość została wysłana", "wiadomosc zostala wyslana",
        "otrzymaliśmy", "otrzymalismy", "potwierdzenie",
        "skontaktujemy się", "skontaktujemy sie", "odpowiemy",
        # English
        "thank you", "thanks", "success", "successful",
        "sent", "submitted", "saved", "added", "created", "registered",
        "message has been sent", "we received", "confirmation",
        "we will contact", "get back to you", "completed"
    ]
    
    # Error indicators (PL + EN)
    ERROR_INDICATORS = [
        # Polish
        "błąd", "blad", "nieprawidłow", "nieprawidlow",
        "wymagane", "pole wymagane", "proszę wypełnić", "prosze wypelnic",
        "nie udało", "nie udalo", "niepowodzenie",
        "nieprawidłowy", "nieprawidlowy", "niewłaściwy", "niewlasciwy",
        "zbyt krótki", "zbyt krotki", "za krótki", "za krotki",
        "nie można", "nie mozna", "nie udało się", "nie udalo sie",
        # English
        "error", "failed", "failure", "invalid",
        "required", "please fill", "must fill", "please enter",
        "could not", "unable", "cannot", "can not",
        "too short", "too long", "incorrect", "wrong",
        "not valid", "validation failed"
    ]
    
    # Warning indicators (PL + EN)
    WARNING_INDICATORS = [
        "uwaga", "ostrzeżenie", "ostrzezenie", "warning",
        "sprawdź", "sprawdz", "check", "verify",
        "popraw", "correct", "fix"
    ]
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
    
    async def validate_form_submission(
        self,
        page,
        original_url: str,
        expected_fields: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate that a form was successfully submitted.
        
        Checks:
        1. Page content for success/error messages
        2. URL change (some forms redirect on success)
        3. Form visibility (should be hidden/replaced on success)
        4. Thank you message presence
        """
        details = {}
        warnings = []
        errors = []
        
        # 1. Content analysis
        content = await page.evaluate("() => document.body.innerText.toLowerCase()")
        
        success_found = []
        for indicator in self.SUCCESS_INDICATORS:
            if indicator.lower() in content:
                success_found.append(indicator)
        
        error_found = []
        for indicator in self.ERROR_INDICATORS:
            if indicator.lower() in content:
                error_found.append(indicator)
        
        warning_found = []
        for indicator in self.WARNING_INDICATORS:
            if indicator.lower() in content:
                warning_found.append(indicator)
        
        details["success_indicators"] = success_found[:5]
        details["error_indicators"] = error_found[:5]
        details["warning_indicators"] = warning_found[:5]
        
        # 2. URL change check
        current_url = page.url
        url_changed = current_url != original_url
        details["url_changed"] = url_changed
        details["current_url"] = current_url
        
        # 3. Form visibility check
        form_visible = await page.evaluate("""
            () => {
                const forms = document.querySelectorAll('form');
                let visibleForms = 0;
                forms.forEach(f => {
                    if (f.offsetParent !== null) visibleForms++;
                });
                return visibleForms;
            }
        """)
        details["visible_forms"] = form_visible
        
        # 4. Thank you element check
        has_thank_you = await page.evaluate("""
            () => {
                const keywords = ['dziękujemy', 'dziekujemy', 'thank you', 'thanks', 'sukces', 'success'];
                const elements = document.querySelectorAll('h1, h2, h3, .success, .thank-you, [class*="success"], [class*="thank"]');
                for (const el of elements) {
                    const text = el.innerText.toLowerCase();
                    if (keywords.some(kw => text.includes(kw))) {
                        return true;
                    }
                }
                return false;
            }
        """)
        details["has_thank_you_element"] = has_thank_you
        
        # Determine validity based on level
        is_valid = False
        confidence = 0.0
        
        if self.level == ValidationLevel.LENIENT:
            # Accept if no errors
            is_valid = len(error_found) == 0
            confidence = 0.6 if is_valid else 0.2
            
        elif self.level == ValidationLevel.NORMAL:
            # Success OR (no errors AND some positive signal)
            has_positive = len(success_found) > 0 or has_thank_you or url_changed
            has_negative = len(error_found) > 0
            
            if has_positive and not has_negative:
                is_valid = True
                confidence = 0.8
            elif not has_negative and (url_changed or form_visible == 0):
                is_valid = True
                confidence = 0.6
                warnings.append("No explicit success message, but no errors detected")
            else:
                is_valid = False
                confidence = 0.3
                
        elif self.level == ValidationLevel.STRICT:
            # Must have success AND no errors
            is_valid = len(success_found) > 0 and len(error_found) == 0
            confidence = 0.9 if is_valid else 0.2
            if len(error_found) > 0:
                errors.append(f"Error indicators found: {error_found[:3]}")
                
        elif self.level == ValidationLevel.PARANOID:
            # Multiple success indicators AND no errors
            is_valid = len(success_found) >= 2 and len(error_found) == 0 and has_thank_you
            confidence = 0.95 if is_valid else 0.1
        
        # Generate warnings and errors
        if len(error_found) > 0:
            errors.append(f"Page contains error messages: {error_found[:3]}")
        
        if len(warning_found) > 0:
            warnings.append(f"Page contains warnings: {warning_found[:3]}")
        
        if len(success_found) == 0 and not has_thank_you:
            warnings.append("No success confirmation message found")
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            method="form_submission",
            details=details,
            warnings=warnings,
            errors=errors
        )
    
    async def validate_navigation(
        self,
        page,
        expected_url_pattern: Optional[str] = None,
        expected_title_contains: Optional[str] = None
    ) -> ValidationResult:
        """Validate successful navigation"""
        details = {}
        errors = []
        
        current_url = page.url
        title = await page.title()
        
        details["url"] = current_url
        details["title"] = title
        
        is_valid = True
        confidence = 0.8
        
        # Check URL pattern
        if expected_url_pattern:
            if re.search(expected_url_pattern, current_url, re.IGNORECASE):
                details["url_match"] = True
            else:
                details["url_match"] = False
                is_valid = False
                errors.append(f"URL doesn't match pattern: {expected_url_pattern}")
        
        # Check title
        if expected_title_contains:
            if expected_title_contains.lower() in title.lower():
                details["title_match"] = True
            else:
                details["title_match"] = False
                is_valid = False
                errors.append(f"Title doesn't contain: {expected_title_contains}")
        
        # Check for error pages
        error_titles = ["404", "not found", "error", "błąd", "nie znaleziono"]
        if any(err in title.lower() for err in error_titles):
            is_valid = False
            confidence = 0.2
            errors.append(f"Page appears to be an error page: {title}")
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            method="navigation",
            details=details,
            errors=errors
        )
    
    async def validate_extraction(
        self,
        data: Dict[str, Any],
        min_items: int = 1,
        required_fields: Optional[List[str]] = None
    ) -> ValidationResult:
        """Validate data extraction results"""
        details = {}
        warnings = []
        errors = []
        
        # Check for items
        items = data.get("products") or data.get("links") or data.get("items") or []
        item_count = len(items) if isinstance(items, list) else data.get("count", 0)
        
        details["item_count"] = item_count
        
        is_valid = item_count >= min_items
        confidence = min(0.9, 0.3 + (item_count / max(min_items * 2, 10)))
        
        if item_count < min_items:
            errors.append(f"Expected at least {min_items} items, got {item_count}")
        
        # Check required fields
        if required_fields and items:
            sample = items[0] if isinstance(items, list) else {}
            missing = [f for f in required_fields if f not in sample]
            if missing:
                warnings.append(f"Missing fields in items: {missing}")
                confidence -= 0.1
        
        return ValidationResult(
            is_valid=is_valid,
            confidence=max(0.1, confidence),
            method="extraction",
            details=details,
            warnings=warnings,
            errors=errors
        )


# Convenience functions
async def validate_form_result(page, original_url: str) -> ValidationResult:
    """Quick form validation"""
    validator = ResultValidator(ValidationLevel.NORMAL)
    return await validator.validate_form_submission(page, original_url)


async def validate_strict(page, original_url: str) -> ValidationResult:
    """Strict form validation"""
    validator = ResultValidator(ValidationLevel.STRICT)
    return await validator.validate_form_submission(page, original_url)
