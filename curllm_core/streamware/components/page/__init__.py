"""
Page Component - Page utilities and context extraction.
"""

# Lazy imports to avoid circular dependencies
def extract_page_context(*args, **kwargs):
    from curllm_core.page_context import extract_page_context as _extract
    return _extract(*args, **kwargs)

def auto_scroll(*args, **kwargs):
    from curllm_core.page_utils import auto_scroll as _scroll
    return _scroll(*args, **kwargs)

def detect_human_verify(*args, **kwargs):
    from curllm_core.human_verify import detect_and_handle_human_verify as _verify
    return _verify(*args, **kwargs)

__all__ = ['extract_page_context', 'auto_scroll', 'detect_human_verify']
