"""
Extraction module - Data extraction from web pages

Functions for extracting structured data from web pages using
various strategies: fastpath, heuristics, LLM validation.
"""

from curllm_core.extraction.extractor import (
    generic_fastpath,
    direct_fastpath,
    extract_links_by_selectors,
    product_heuristics,
    product_heuristics_old,
    fallback_extract,
    extract_articles_eval,
    validate_with_llm,
    refine_instruction_llm,
    # Private functions needed by task_runner
    _extract_emails,
    _extract_phones,
    _extract_all_anchors,
    _extract_anchors_filtered,
    _parse_limit_from_instruction,
    _filter_only,
    _page_context_min,
    _extract_anchors_by_selectors,
)

__all__ = [
    'generic_fastpath',
    'direct_fastpath',
    'extract_links_by_selectors',
    'product_heuristics',
    'product_heuristics_old',
    'fallback_extract',
    'extract_articles_eval',
    'validate_with_llm',
    'refine_instruction_llm',
    '_extract_emails',
    '_extract_phones',
    '_extract_all_anchors',
    '_extract_anchors_filtered',
]
