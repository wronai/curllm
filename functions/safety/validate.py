"""
Input Validation

Validate inputs before processing to catch errors early.
"""

import re
from typing import Any, Optional, List, Callable, Dict
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of validation."""
    
    valid: bool
    value: Any = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class InputValidator:
    """
    Chainable input validator.
    
    Example:
        validator = InputValidator()
        result = validator.validate(text).not_none().min_length(3).is_string().result()
        
        if result.valid:
            process(result.value)
    """
    
    def __init__(self, value: Any = None):
        self._value = value
        self._errors: List[str] = []
        self._warnings: List[str] = []
        self._valid = True
    
    def validate(self, value: Any) -> "InputValidator":
        """Start validation chain with a value."""
        self._value = value
        self._errors = []
        self._warnings = []
        self._valid = True
        return self
    
    def not_none(self, error_msg: str = "Value cannot be None") -> "InputValidator":
        """Check that value is not None."""
        if self._value is None:
            self._errors.append(error_msg)
            self._valid = False
        return self
    
    def is_string(self, error_msg: str = "Value must be a string") -> "InputValidator":
        """Check that value is a string."""
        if self._value is not None and not isinstance(self._value, str):
            self._errors.append(error_msg)
            self._valid = False
        return self
    
    def not_empty(self, error_msg: str = "Value cannot be empty") -> "InputValidator":
        """Check that value is not empty."""
        if self._value is not None:
            if isinstance(self._value, str) and not self._value.strip():
                self._errors.append(error_msg)
                self._valid = False
            elif hasattr(self._value, '__len__') and len(self._value) == 0:
                self._errors.append(error_msg)
                self._valid = False
        return self
    
    def min_length(self, length: int, error_msg: str = None) -> "InputValidator":
        """Check minimum length."""
        if self._value is not None and hasattr(self._value, '__len__'):
            if len(self._value) < length:
                msg = error_msg or f"Value must be at least {length} characters"
                self._errors.append(msg)
                self._valid = False
        return self
    
    def max_length(self, length: int, error_msg: str = None) -> "InputValidator":
        """Check maximum length."""
        if self._value is not None and hasattr(self._value, '__len__'):
            if len(self._value) > length:
                msg = error_msg or f"Value must be at most {length} characters"
                self._warnings.append(msg)
                # Truncate instead of failing
                if isinstance(self._value, str):
                    self._value = self._value[:length]
        return self
    
    def matches(self, pattern: str, error_msg: str = None) -> "InputValidator":
        """Check that value matches regex pattern."""
        if self._value is not None and isinstance(self._value, str):
            if not re.search(pattern, self._value):
                msg = error_msg or f"Value does not match required pattern"
                self._errors.append(msg)
                self._valid = False
        return self
    
    def not_matches(self, pattern: str, error_msg: str = None) -> "InputValidator":
        """Check that value does NOT match regex pattern."""
        if self._value is not None and isinstance(self._value, str):
            if re.search(pattern, self._value):
                msg = error_msg or f"Value matches forbidden pattern"
                self._errors.append(msg)
                self._valid = False
        return self
    
    def is_numeric(self, error_msg: str = "Value must be numeric") -> "InputValidator":
        """Check that value is numeric or can be converted."""
        if self._value is not None:
            try:
                float(str(self._value).replace(',', '.').replace(' ', ''))
            except (ValueError, TypeError):
                self._errors.append(error_msg)
                self._valid = False
        return self
    
    def custom(self, check: Callable[[Any], bool], error_msg: str) -> "InputValidator":
        """Apply custom validation function."""
        if self._value is not None:
            try:
                if not check(self._value):
                    self._errors.append(error_msg)
                    self._valid = False
            except Exception as e:
                self._errors.append(f"{error_msg}: {e}")
                self._valid = False
        return self
    
    def transform(self, func: Callable[[Any], Any]) -> "InputValidator":
        """Transform value (e.g., strip, lowercase)."""
        if self._value is not None:
            try:
                self._value = func(self._value)
            except Exception as e:
                self._warnings.append(f"Transform failed: {e}")
        return self
    
    def default(self, default_value: Any) -> "InputValidator":
        """Use default value if current value is None or invalid."""
        if self._value is None or not self._valid:
            self._value = default_value
            self._valid = True
            self._errors = []
        return self
    
    def result(self) -> ValidationResult:
        """Get validation result."""
        return ValidationResult(
            valid=self._valid,
            value=self._value,
            errors=self._errors,
            warnings=self._warnings,
        )
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self._valid
    
    @property
    def value(self) -> Any:
        """Get (possibly transformed) value."""
        return self._value


def validate_input(value: Any) -> InputValidator:
    """
    Start input validation chain.
    
    Example:
        result = validate_input(text).not_none().min_length(3).result()
    """
    return InputValidator().validate(value)


def is_valid_text(text: Any, min_length: int = 1, max_length: int = 10000) -> bool:
    """
    Quick check if text is valid for processing.
    
    Args:
        text: Value to check
        min_length: Minimum length
        max_length: Maximum length
        
    Returns:
        True if valid
    """
    if text is None:
        return False
    if not isinstance(text, str):
        return False
    if len(text) < min_length or len(text) > max_length:
        return False
    return True


def is_valid_url(url: Any) -> bool:
    """
    Quick check if URL is valid.
    
    Args:
        url: Value to check
        
    Returns:
        True if looks like valid URL
    """
    if not url or not isinstance(url, str):
        return False
    
    url_pattern = r'^https?://[^\s<>"\'\{\}\|\\\^\[\]`]+'
    return bool(re.match(url_pattern, url))


def is_valid_price(text: Any) -> bool:
    """
    Quick check if text looks like a price.
    
    Args:
        text: Value to check
        
    Returns:
        True if looks like price
    """
    if not text or not isinstance(text, str):
        return False
    
    price_pattern = r'\d+[,\.\s]*\d*\s*(?:zł|PLN|€|EUR|\$|USD)?'
    return bool(re.search(price_pattern, text, re.IGNORECASE))
