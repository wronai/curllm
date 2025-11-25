"""
Unit tests for Tool Retry Manager.

Tests the intelligent retry logic to prevent infinite loops
when tools fail repeatedly with the same error.
"""

import pytest
from curllm_core.tool_retry import ToolRetryManager


def test_retry_manager_initialization():
    """Test that retry manager initializes with correct defaults."""
    manager = ToolRetryManager()
    assert manager.max_same_error == 2
    assert manager.tool_failures == {}
    assert manager.total_failures == {}


def test_retry_manager_custom_max_error():
    """Test that retry manager can be initialized with custom max_same_error."""
    manager = ToolRetryManager(max_same_error=3)
    assert manager.max_same_error == 3


def test_should_retry_first_error():
    """Test that first error allows retry."""
    manager = ToolRetryManager()
    
    # First error - should retry
    assert manager.should_retry("form.fill", "error A") is True
    assert manager.total_failures["form.fill"] == 1


def test_should_retry_same_error_within_limit():
    """Test that same error within limit allows retry."""
    manager = ToolRetryManager(max_same_error=2)
    
    # First occurrence
    assert manager.should_retry("form.fill", "error A") is True
    
    # Second occurrence - should still retry (count=1, limit=2)
    assert manager.should_retry("form.fill", "error A") is True


def test_should_not_retry_same_error_exceeds_limit():
    """Test that same error exceeding limit blocks retry."""
    manager = ToolRetryManager(max_same_error=2)
    
    # First error
    assert manager.should_retry("form.fill", "error A") is True
    
    # Second error (same)
    assert manager.should_retry("form.fill", "error A") is True
    
    # Third error (same) - should NOT retry
    assert manager.should_retry("form.fill", "error A") is False


def test_different_errors_allow_retry():
    """Test that different errors are tracked separately."""
    manager = ToolRetryManager(max_same_error=2)
    
    # First error
    assert manager.should_retry("form.fill", "error A") is True
    
    # Same error again
    assert manager.should_retry("form.fill", "error A") is True
    
    # Same error 3rd time - blocked
    assert manager.should_retry("form.fill", "error A") is False
    
    # Different error - should retry
    assert manager.should_retry("form.fill", "error B") is True


def test_different_tools_tracked_separately():
    """Test that different tools are tracked independently."""
    manager = ToolRetryManager(max_same_error=2)
    
    # Tool 1 fails twice
    assert manager.should_retry("form.fill", "error A") is True
    assert manager.should_retry("form.fill", "error A") is True
    assert manager.should_retry("form.fill", "error A") is False
    
    # Tool 2 can still retry
    assert manager.should_retry("extract.emails", "error A") is True


def test_get_alternative_approach_form_fill():
    """Test that alternative approach is suggested for form.fill."""
    manager = ToolRetryManager()
    
    alternative = manager.get_alternative_approach("form.fill")
    assert alternative == "llm_guided_field_fill"


def test_get_alternative_approach_click():
    """Test that alternative approach is suggested for click."""
    manager = ToolRetryManager()
    
    alternative = manager.get_alternative_approach("click")
    assert alternative == "navigate"


def test_get_alternative_approach_no_alternative():
    """Test that None is returned when no alternative exists."""
    manager = ToolRetryManager()
    
    alternative = manager.get_alternative_approach("unknown.tool")
    assert alternative is None


def test_get_failure_summary_no_failures():
    """Test failure summary when tool has no failures."""
    manager = ToolRetryManager()
    
    summary = manager.get_failure_summary("form.fill")
    assert summary["total_failures"] == 0
    assert summary["unique_errors"] == 0
    assert summary["errors"] == []


def test_get_failure_summary_with_failures():
    """Test failure summary with multiple failures."""
    manager = ToolRetryManager()
    
    # Generate some failures
    manager.should_retry("form.fill", "error A")
    manager.should_retry("form.fill", "error A")
    manager.should_retry("form.fill", "error B")
    
    summary = manager.get_failure_summary("form.fill")
    assert summary["total_failures"] == 3
    assert summary["unique_errors"] == 2
    assert "error A" in summary["errors"]
    assert "error B" in summary["errors"]
    assert summary["most_common_error"] == "error A"


def test_reset():
    """Test that reset clears all failure tracking."""
    manager = ToolRetryManager()
    
    # Add some failures
    manager.should_retry("form.fill", "error A")
    manager.should_retry("extract.emails", "error B")
    
    # Reset
    manager.reset()
    
    assert manager.tool_failures == {}
    assert manager.total_failures == {}


def test_is_repetitive_failure_not_enough_errors():
    """Test that repetitive failure detection requires multiple errors."""
    manager = ToolRetryManager()
    
    manager.should_retry("form.fill", "error A")
    
    # Only 1 error - not repetitive
    assert manager.is_repetitive_failure("form.fill") is False


def test_is_repetitive_failure_same_errors():
    """Test that repetitive failure is detected for same errors."""
    manager = ToolRetryManager()
    
    manager.should_retry("form.fill", "error A")
    manager.should_retry("form.fill", "error A")
    
    # Same error twice - is repetitive
    assert manager.is_repetitive_failure("form.fill") is True


def test_is_repetitive_failure_different_errors():
    """Test that repetitive failure is not detected for different errors."""
    manager = ToolRetryManager()
    
    manager.should_retry("form.fill", "error A")
    manager.should_retry("form.fill", "error B")
    
    # Different errors - not repetitive
    assert manager.is_repetitive_failure("form.fill") is False


def test_is_repetitive_failure_no_tool():
    """Test that repetitive failure check on unknown tool returns False."""
    manager = ToolRetryManager()
    
    assert manager.is_repetitive_failure("unknown.tool") is False


def test_complex_scenario():
    """Test a complex scenario with multiple tools and errors."""
    manager = ToolRetryManager(max_same_error=2)
    
    # form.fill fails with domain_dir error 3 times
    assert manager.should_retry("form.fill", "name 'domain_dir' is not defined") is True
    assert manager.should_retry("form.fill", "name 'domain_dir' is not defined") is True
    assert manager.should_retry("form.fill", "name 'domain_dir' is not defined") is False
    
    # Get alternative
    alternative = manager.get_alternative_approach("form.fill")
    assert alternative == "llm_guided_field_fill"
    
    # Check it's repetitive
    assert manager.is_repetitive_failure("form.fill") is True
    
    # Get summary (note: 3rd call returned False, so only 2 failures recorded)
    summary = manager.get_failure_summary("form.fill")
    assert summary["total_failures"] == 2
    assert summary["unique_errors"] == 1
    assert summary["most_common_error"] == "name 'domain_dir' is not defined"
    
    # Another tool can still work
    assert manager.should_retry("extract.links", "timeout") is True
