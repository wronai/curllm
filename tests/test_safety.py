"""Tests for safety module."""

import pytest


class TestSafeWrapper:
    """Test safe function wrappers."""
    
    def test_safe_call_success(self):
        from functions.safety.wrapper import safe_call
        
        result = safe_call(lambda x: x * 2, 5, default=0)
        assert result == 10
    
    def test_safe_call_exception(self):
        from functions.safety.wrapper import safe_call
        
        def raises():
            raise ValueError("test error")
        
        result = safe_call(raises, default="fallback")
        assert result == "fallback"
    
    def test_safe_extract_success(self):
        from functions.safety.wrapper import safe_extract
        
        result = safe_extract(lambda: "value")
        assert result.success is True
        assert result.value == "value"
    
    def test_safe_extract_failure(self):
        from functions.safety.wrapper import safe_extract
        
        def raises():
            raise TypeError("type error")
        
        result = safe_extract(raises)
        assert result.success is False
        assert result.error_type == "TypeError"
    
    def test_guard_none(self):
        from functions.safety.wrapper import guard_none
        
        @guard_none
        def process(text):
            return text.upper()
        
        assert process("hello") == "HELLO"
        assert process(None) is None


class TestSanitize:
    """Test sanitization functions."""
    
    def test_sanitize_text_none(self):
        from functions.safety.sanitize import sanitize_text
        
        assert sanitize_text(None) == ""
        assert sanitize_text("") == ""
    
    def test_sanitize_text_whitespace(self):
        from functions.safety.sanitize import sanitize_text
        
        assert "test" in sanitize_text("  test  ")
        assert sanitize_text("\xa0test\xa0") == " test "
    
    def test_normalize_whitespace(self):
        from functions.safety.sanitize import normalize_whitespace
        
        assert normalize_whitespace("  hello   world  ") == "hello world"
        assert normalize_whitespace(None) == ""
    
    def test_strip_html_tags(self):
        from functions.safety.sanitize import strip_html_tags
        
        assert strip_html_tags("<p>Hello</p>") == "Hello"
        assert strip_html_tags("<div><span>Test</span></div>") == "Test"
    
    def test_truncate_smart(self):
        from functions.safety.sanitize import truncate_smart
        
        text = "This is a long text that needs truncation"
        result = truncate_smart(text, 20)
        assert len(result) <= 20
        assert result.endswith("...")


class TestValidate:
    """Test validation functions."""
    
    def test_validator_chain(self):
        from functions.safety.validate import validate_input
        
        result = validate_input("hello").not_none().is_string().min_length(3).result()
        assert result.valid is True
        assert result.value == "hello"
    
    def test_validator_fails(self):
        from functions.safety.validate import validate_input
        
        result = validate_input(None).not_none().result()
        assert result.valid is False
        assert len(result.errors) > 0
    
    def test_validator_transform(self):
        from functions.safety.validate import validate_input
        
        result = validate_input("  HELLO  ").transform(str.strip).transform(str.lower).result()
        assert result.value == "hello"
    
    def test_validator_default(self):
        from functions.safety.validate import validate_input
        
        result = validate_input(None).not_none().default("fallback").result()
        assert result.valid is True
        assert result.value == "fallback"
    
    def test_is_valid_url(self):
        from functions.safety.validate import is_valid_url
        
        assert is_valid_url("https://example.com") is True
        assert is_valid_url("http://test.pl/path") is True
        assert is_valid_url("not-a-url") is False
        assert is_valid_url(None) is False


class TestFallback:
    """Test fallback mechanisms."""
    
    def test_fallback_chain(self):
        from functions.safety.fallback import FallbackChain
        
        chain = FallbackChain("test")
        chain.add("always_fails", lambda x: None)
        chain.add("returns_value", lambda x: x * 2)
        
        result = chain.execute(5)
        assert result.success is True
        assert result.value == 10
        assert result.strategy_used == "returns_value"
    
    def test_fallback_all_fail(self):
        from functions.safety.fallback import FallbackChain
        
        chain = FallbackChain("test")
        chain.add("fail1", lambda: None)
        chain.add("fail2", lambda: None)
        
        result = chain.execute()
        assert result.success is False
        assert len(result.strategies_tried) == 2
    
    def test_with_fallbacks_decorator(self):
        from functions.safety.fallback import with_fallbacks
        
        def fallback1(x):
            return x + 1
        
        @with_fallbacks(fallback1)
        def main_func(x):
            if x < 0:
                return None
            return x
        
        assert main_func(5) == 5
        assert main_func(-1) == 0  # Uses fallback
    
    def test_circuit_breaker(self):
        from functions.safety.fallback import CircuitBreaker
        
        breaker = CircuitBreaker(max_failures=2, reset_timeout=1.0)
        
        assert breaker.is_open is False
        
        breaker.record_failure()
        assert breaker.is_open is False
        
        breaker.record_failure()
        assert breaker.is_open is True
        
        breaker.record_success()
        assert breaker.is_open is False
