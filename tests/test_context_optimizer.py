"""
Unit tests for Context Optimizer.

Tests the context size reduction and optimization logic.
"""

import pytest
from curllm_core.context_optimizer import (
    optimize_context,
    truncate_dom,
    deduplicate_iframes,
    prioritize_form_context,
    is_form_task,
    filter_form_elements,
    estimate_context_size
)


def test_optimize_context_step_1_no_changes():
    """Test that step 1 keeps full context."""
    context = {
        "title": "Test Page",
        "dom_preview": [{"tag": "div"} for _ in range(500)],
        "text": "A" * 10000
    }
    
    optimized = optimize_context(context, step=1)
    
    # Step 1 should not modify context
    assert len(optimized["dom_preview"]) == 500
    assert len(optimized["text"]) == 10000


def test_optimize_context_step_2_reduces_dom():
    """Test that step 2+ reduces DOM size."""
    context = {
        "title": "Test Page",
        "dom_preview": [{"tag": "div", "visible": True} for _ in range(500)],
        "text": "A" * 10000
    }
    
    optimized = optimize_context(context, step=2)
    
    # DOM should be reduced
    assert len(optimized["dom_preview"]) <= 300
    assert len(optimized["dom_preview"]) < 500


def test_optimize_context_step_3_further_reduction():
    """Test that step 3+ applies more aggressive reduction."""
    context = {
        "title": "Test Page",
        "dom_preview": [{"tag": "div", "visible": True} for _ in range(500)],
        "text": "A" * 10000
    }
    
    optimized = optimize_context(context, step=3)
    
    # DOM should be further reduced
    assert len(optimized["dom_preview"]) <= 200
    # Text should be truncated
    assert len(optimized["text"]) <= 3000 + 14  # +14 for "[truncated]"


def test_truncate_dom_prioritizes_forms():
    """Test that DOM truncation prioritizes form elements."""
    elements = [
        {"tag": "div", "visible": True},
        {"tag": "input", "type": "email", "visible": True},
        {"tag": "span", "visible": True},
        {"tag": "button", "visible": True},
        {"tag": "p", "visible": True},
    ]
    
    truncated = truncate_dom(elements, max_elements=2)
    
    # Should keep form elements (input, button) over div/span/p
    tags = [elem["tag"] for elem in truncated]
    assert "input" in tags
    assert "button" in tags


def test_truncate_dom_no_change_if_small():
    """Test that small DOM is not truncated."""
    elements = [{"tag": "div"} for _ in range(10)]
    
    truncated = truncate_dom(elements, max_elements=200)
    
    assert len(truncated) == 10


def test_deduplicate_iframes():
    """Test that duplicate iframes are removed."""
    iframes = [
        {"src": "http://example.com/iframe1"},
        {"src": "http://example.com/iframe1"},  # Duplicate
        {"src": "http://example.com/iframe2"},
        {"src": "http://example.com/iframe1"},  # Duplicate
    ]
    
    unique = deduplicate_iframes(iframes)
    
    assert len(unique) == 2
    srcs = [iframe["src"] for iframe in unique]
    assert srcs.count("http://example.com/iframe1") == 1
    assert srcs.count("http://example.com/iframe2") == 1


def test_deduplicate_iframes_keeps_no_src():
    """Test that iframes without src are kept."""
    iframes = [
        {"src": "http://example.com/iframe1"},
        {"name": "iframe2"},  # No src
        {"name": "iframe3"},  # No src
    ]
    
    unique = deduplicate_iframes(iframes)
    
    # Should keep all (2 without src + 1 with src)
    assert len(unique) == 3


def test_is_form_task_positive():
    """Test form task detection - positive cases."""
    assert is_form_task("Fill form: name=John") is True
    assert is_form_task("Fill contact form") is True
    assert is_form_task("Wypełnij formularz") is True
    assert is_form_task("Submit form with data") is True


def test_is_form_task_negative():
    """Test form task detection - negative cases."""
    assert is_form_task("Extract all links") is False
    assert is_form_task("Click on button") is False
    assert is_form_task("") is False
    assert is_form_task(None) is False


def test_filter_form_elements():
    """Test filtering to only form-related elements."""
    elements = [
        {"tag": "div"},
        {"tag": "input", "type": "email"},
        {"tag": "span"},
        {"tag": "button"},
        {"tag": "textarea"},
        {"tag": "p"},
        {"tag": "select"},
    ]
    
    filtered = filter_form_elements(elements)
    
    assert len(filtered) == 4  # input, button, textarea, select
    tags = [elem["tag"] for elem in filtered]
    assert "input" in tags
    assert "button" in tags
    assert "textarea" in tags
    assert "select" in tags
    assert "div" not in tags
    assert "span" not in tags


def test_prioritize_form_context():
    """Test form context prioritization."""
    context = {
        "title": "Contact Page",
        "url": "http://example.com/contact",
        "forms": [{"id": "contact-form", "fields": []}],
        "dom_preview": [
            {"tag": "input", "type": "email"},
            {"tag": "div"},
            {"tag": "button"},
        ],
        "iframes": [],
        "article_candidates": [],
    }
    
    optimized = prioritize_form_context(context, "Fill contact form")
    
    # Should keep only form-related fields
    assert "title" in optimized
    assert "url" in optimized
    assert "forms" in optimized
    assert "dom_preview" in optimized
    
    # article_candidates should be removed
    assert "article_candidates" not in optimized
    
    # DOM should be filtered to form elements only
    assert len(optimized["dom_preview"]) == 2  # input, button (not div)


def test_prioritize_form_context_non_form_task():
    """Test that non-form tasks are not modified."""
    context = {
        "title": "Page",
        "url": "http://example.com",
        "forms": [],
        "dom_preview": [],
    }
    
    result = prioritize_form_context(context, "Extract all links")
    
    # Should return original context unchanged
    assert result == context


def test_estimate_context_size():
    """Test context size estimation."""
    context = {
        "title": "Test",
        "url": "http://example.com",
        "text": "A" * 1000,
    }
    
    size = estimate_context_size(context)
    
    # Size should be roughly 1000+ chars
    assert size > 1000
    assert size < 2000  # Accounting for JSON overhead


def test_optimize_context_with_tool_history():
    """Test that tool history is limited after step 3."""
    tool_history = [
        {"tool": "extract.links", "result": {}},
        {"tool": "extract.emails", "result": {}},
        {"tool": "form.fill", "result": {}},
        {"tool": "click", "result": {}},
        {"tool": "navigate", "result": {}},
    ]
    
    context = {
        "title": "Test",
        "tool_history": tool_history
    }
    
    optimized = optimize_context(context, step=4, tool_history=tool_history)
    
    # Should keep only last 3 entries
    if "tool_history" in optimized:
        assert len(optimized["tool_history"]) == 3
