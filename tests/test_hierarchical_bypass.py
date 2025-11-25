"""
Unit tests for Hierarchical Planner Smart Bypass.

Tests the logic that decides when to use or bypass the hierarchical planner.
"""

import pytest
from curllm_core.hierarchical_planner import (
    should_use_hierarchical,
    is_simple_form_task,
    requires_multi_step,
    estimate_context_size
)


def test_is_simple_form_task_positive():
    """Test simple form detection - positive cases."""
    instruction = "Fill form: name=John, email=john@example.com"
    page_context = {
        "forms": [{
            "id": "contact-form",
            "fields": [
                {"name": "name", "type": "text"},
                {"name": "email", "type": "email"},
                {"name": "message", "type": "textarea"},
            ]
        }]
    }
    
    assert is_simple_form_task(instruction, page_context) is True


def test_is_simple_form_task_no_form_keyword():
    """Test that non-form keywords return False."""
    instruction = "Extract all links from page"
    page_context = {
        "forms": [{"id": "form1", "fields": [{"name": "email"}]}]
    }
    
    assert is_simple_form_task(instruction, page_context) is False


def test_is_simple_form_task_multiple_forms():
    """Test that multiple forms return False (not simple)."""
    instruction = "Fill form"
    page_context = {
        "forms": [
            {"id": "form1", "fields": [{"name": "email"}]},
            {"id": "form2", "fields": [{"name": "name"}]},
        ]
    }
    
    assert is_simple_form_task(instruction, page_context) is False


def test_is_simple_form_task_complex_form():
    """Test that complex forms (>10 fields) return False."""
    instruction = "Fill form"
    page_context = {
        "forms": [{
            "id": "registration",
            "fields": [{"name": f"field{i}", "type": "text"} for i in range(15)]
        }]
    }
    
    assert is_simple_form_task(instruction, page_context) is False


def test_is_simple_form_task_no_forms():
    """Test that pages without forms return False."""
    instruction = "Fill form"
    page_context = {"forms": []}
    
    assert is_simple_form_task(instruction, page_context) is False


def test_requires_multi_step_positive():
    """Test multi-step detection - positive cases."""
    assert requires_multi_step("Click button then fill form") is True
    assert requires_multi_step("Navigate to page after login") is True
    assert requires_multi_step("First click, next fill") is True
    assert requires_multi_step("Step 1: login, step 2: extract") is True


def test_requires_multi_step_negative():
    """Test multi-step detection - negative cases."""
    assert requires_multi_step("Fill contact form") is False
    assert requires_multi_step("Extract all links") is False
    assert requires_multi_step("Click the button") is False
    assert requires_multi_step("") is False
    assert requires_multi_step(None) is False


def test_should_use_hierarchical_simple_form():
    """Test that simple forms bypass hierarchical planner."""
    instruction = "Fill contact form: name=John, email=john@example.com"
    page_context = {
        "forms": [{
            "id": "contact",
            "fields": [
                {"name": "name"},
                {"name": "email"},
                {"name": "message"},
            ]
        }],
        "title": "Contact Us"
    }
    
    # Simple form should bypass hierarchical planner
    assert should_use_hierarchical(instruction, page_context) is False


def test_should_use_hierarchical_multi_step():
    """Test that multi-step tasks use hierarchical planner."""
    instruction = "First login, then extract all products"
    page_context = {
        "forms": [],
        "title": "Products"
    }
    
    # Multi-step should use hierarchical planner
    assert should_use_hierarchical(instruction, page_context) is True


def test_should_use_hierarchical_large_context():
    """Test that large contexts use hierarchical planner."""
    instruction = "Extract data"
    
    # Create large context (>25KB)
    page_context = {
        "dom_preview": [{"tag": "div", "text": "A" * 1000} for _ in range(100)],
        "title": "Large Page"
    }
    
    # Large context should use hierarchical planner
    assert should_use_hierarchical(instruction, page_context) is True


def test_should_use_hierarchical_small_context():
    """Test that small contexts bypass hierarchical planner."""
    instruction = "Extract links"
    page_context = {
        "title": "Small Page",
        "url": "http://example.com",
        "dom_preview": [{"tag": "a", "href": "http://example.com"}]
    }
    
    # Small context + no multi-step = bypass
    assert should_use_hierarchical(instruction, page_context) is False


def test_estimate_context_size_small():
    """Test context size estimation for small context."""
    context = {
        "title": "Test",
        "url": "http://example.com"
    }
    
    size = estimate_context_size(context)
    
    # Should be small (<1000 chars)
    assert size < 1000


def test_estimate_context_size_large():
    """Test context size estimation for large context."""
    context = {
        "title": "Test",
        "dom_preview": [{"tag": "div", "text": "A" * 1000} for _ in range(100)]
    }
    
    size = estimate_context_size(context)
    
    # Should be large (>50KB)
    assert size > 50000


def test_bypass_logic_integration():
    """Test complete bypass logic integration."""
    # Scenario 1: Simple form + small context = BYPASS
    simple_instruction = "Fill form: email=test@example.com"
    simple_context = {
        "forms": [{"id": "simple", "fields": [{"name": "email"}]}],
        "title": "Contact"
    }
    assert should_use_hierarchical(simple_instruction, simple_context) is False
    
    # Scenario 2: Complex task + large context = USE
    complex_instruction = "First login then extract all products"
    large_context = {
        "dom_preview": [{"tag": "div"} for _ in range(1000)],
        "forms": []
    }
    assert should_use_hierarchical(complex_instruction, large_context) is True
    
    # Scenario 3: Simple extract + small context = BYPASS
    extract_instruction = "Extract links"
    extract_context = {"title": "Test", "dom_preview": []}
    assert should_use_hierarchical(extract_instruction, extract_context) is False
