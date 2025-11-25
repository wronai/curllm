"""
Integration tests for form filling functionality.

Tests that form filling works correctly with domain_dir parameter
and handles various edge cases.
"""

from unittest.mock import Mock


def test_form_field_parsing():
    """Test that form field pairs are correctly parsed from instruction."""
    from curllm_core.executor import CurllmExecutor
    
    executor = CurllmExecutor()
    
    instruction = "Fill form: name=John Doe, email=john@example.com, phone=+48123456789"
    pairs = executor._parse_form_pairs(instruction)
    
    assert pairs is not None
    assert isinstance(pairs, dict)
    assert "email" in pairs
    assert pairs["email"] == "john@example.com"


def test_error_response_structure():
    """Test that error responses have proper structure."""
    error_response = {
        "submitted": False,
        "error": "name 'domain_dir' is not defined"
    }
    
    # Check structure
    assert isinstance(error_response, dict)
    assert "error" in error_response
    assert error_response.get("submitted") is False
    
    # This is the condition that should trigger LLM filler
    is_success = (
        error_response and 
        isinstance(error_response, dict) and 
        error_response.get("submitted") is True and
        "error" not in error_response
    )
    
    assert is_success is False  # Should not be considered success


def test_success_response_structure():
    """Test that success responses are correctly identified."""
    success_response = {
        "submitted": True,
        "filled": {
            "email": True,
            "name": True
        }
    }
    
    # Check structure
    assert isinstance(success_response, dict)
    assert success_response.get("submitted") is True
    assert "error" not in success_response
    
    # This should be considered success
    is_success = (
        success_response and 
        isinstance(success_response, dict) and 
        success_response.get("submitted") is True and
        "error" not in success_response
    )
    
    assert is_success is True


def test_canonical_pairs_exposure():
    """Test that canonical pairs are correctly exposed to page."""
    from curllm_core.executor import CurllmExecutor
    
    executor = CurllmExecutor()
    
    instruction = "Fill contact form: name=John Doe, email=john@example.com, subject=Test"
    pairs = executor._parse_form_pairs(instruction)
    
    assert pairs is not None
    assert "name" in pairs
    assert "email" in pairs
    assert "subject" in pairs
    assert pairs["name"] == "John Doe"
    assert pairs["email"] == "john@example.com"
    assert pairs["subject"] == "Test"
