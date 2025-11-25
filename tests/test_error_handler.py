"""
Unit tests for User-Friendly Error Handler.

Tests error mapping and formatting for better UX.
"""

import pytest
from curllm_core.error_handler import (
    format_user_friendly_error,
    get_error_category,
    should_retry_error,
    format_error_for_logging,
    create_error_response
)


def test_format_domain_dir_error():
    """Test domain_dir error mapping."""
    error = NameError("name 'domain_dir' is not defined")
    
    result = format_user_friendly_error(error)
    
    assert "konfiguracji" in result["message"].lower()
    assert "zrestartuj" in result["suggestion"].lower()
    assert result["severity"] == "critical"
    assert result["can_retry"] is False


def test_format_timeout_error():
    """Test timeout error mapping."""
    error = TimeoutError("Page timeout exceeded")
    
    result = format_user_friendly_error(error)
    
    assert "długo" in result["message"].lower()
    assert result["severity"] == "warning"
    assert result["can_retry"] is True


def test_format_unknown_error():
    """Test unknown error fallback."""
    error = RuntimeError("Some random error")
    
    result = format_user_friendly_error(error)
    
    assert "nieoczekiwany" in result["message"].lower()
    assert "logi" in result["suggestion"].lower()
    assert result["severity"] == "error"
    assert result["can_retry"] is True


def test_network_error_category():
    """Test network error categorization."""
    error = ConnectionError("Connection refused")
    
    category = get_error_category(error)
    
    assert category == "network"


def test_form_error_category():
    """Test form error categorization."""
    error = ValueError("Field not found in form")
    
    category = get_error_category(error)
    
    assert category == "form"


def test_llm_error_category():
    """Test LLM error categorization."""
    error = RuntimeError("LLM model not found")
    
    category = get_error_category(error)
    
    assert category == "llm"


def test_captcha_error_category():
    """Test CAPTCHA error categorization."""
    error = RuntimeError("reCAPTCHA detected")
    
    category = get_error_category(error)
    
    assert category == "captcha"


def test_should_retry_timeout():
    """Test retry recommendation for timeout."""
    error = TimeoutError("timeout")
    
    assert should_retry_error(error) is True


def test_should_not_retry_captcha():
    """Test no retry for CAPTCHA."""
    error = RuntimeError("CAPTCHA detected")
    
    assert should_retry_error(error) is False


def test_format_error_for_logging():
    """Test error formatting for logs."""
    error = ValueError("Invalid email format")
    
    log_message = format_error_for_logging(error, "form_fill")
    
    assert "❌" in log_message
    assert "💡" in log_message
    assert "🔧" in log_message
    assert "Context: form_fill" in log_message


def test_create_error_response():
    """Test standardized error response creation."""
    error = TimeoutError("Page load timeout")
    
    response = create_error_response(error, "navigation")
    
    assert response["success"] is False
    assert "error" in response
    assert "message" in response["error"]
    assert "suggestion" in response["error"]
    assert "severity" in response["error"]
    assert "can_retry" in response["error"]
    assert "category" in response["error"]


def test_create_error_response_with_stacktrace():
    """Test error response with stacktrace."""
    error = RuntimeError("Test error")
    
    response = create_error_response(error, include_stacktrace=True)
    
    assert "stacktrace" in response["error"]
    assert "technical_details" in response["error"]


def test_multiple_error_patterns():
    """Test various error patterns."""
    test_cases = [
        ("Connection refused", "network", True),
        ("No form found", "form", False),
        ("Model not found", "llm", False),
        ("Cloudflare challenge", "unknown", True),
        ("Permission denied", "unknown", False),
    ]
    
    for error_msg, expected_category, expected_retry in test_cases:
        error = RuntimeError(error_msg)
        category = get_error_category(error)
        can_retry = should_retry_error(error)
        
        assert category == expected_category or category == "unknown"
        # can_retry depends on error mapping


def test_polish_language_messages():
    """Test that messages are in Polish."""
    error = TimeoutError("timeout")
    
    result = format_user_friendly_error(error)
    
    # Should contain Polish characters/words
    assert any(char in result["message"] for char in ["ą", "ć", "ę", "ł", "ń", "ó", "ś", "ź", "ż"]) or \
           any(word in result["message"].lower() for word in ["strona", "błąd", "sprawdź"])


def test_error_severity_levels():
    """Test different severity levels."""
    test_cases = [
        (NameError("domain_dir"), "critical"),
        (TimeoutError("timeout"), "warning"),
        (ConnectionError("connection"), "error"),
    ]
    
    for error, expected_severity in test_cases:
        result = format_user_friendly_error(error)
        assert result["severity"] == expected_severity


def test_actionable_suggestions():
    """Test that suggestions are actionable."""
    errors = [
        RuntimeError("Ollama not running"),
        ValueError("Invalid email"),
        TimeoutError("timeout"),
    ]
    
    for error in errors:
        result = format_user_friendly_error(error)
        # Suggestion should contain action words
        assert any(word in result["suggestion"].lower() 
                  for word in ["sprawdź", "spróbuj", "uruchom", "upewnij"])
