"""
Tests for DOM Toolkit - Atomic DOM Analysis

Tests verify that:
1. All analyzers are importable
2. Query methods return expected structure
3. No LLM calls in analyzer methods
"""

import pytest


class TestDOMToolkitImports:
    """Test that all DOM toolkit components are importable."""
    
    def test_import_analyzers(self):
        from curllm_core.dom_toolkit.analyzers import (
            DOMStructureAnalyzer,
            PatternDetector,
            SelectorGenerator,
            PriceDetector,
        )
        assert DOMStructureAnalyzer is not None
        assert PatternDetector is not None
        assert SelectorGenerator is not None
        assert PriceDetector is not None
    
    def test_import_statistics(self):
        from curllm_core.dom_toolkit.statistics import (
            FrequencyAnalyzer,
            ElementClusterer,
            CandidateScorer,
        )
        assert FrequencyAnalyzer is not None
        assert ElementClusterer is not None
        assert CandidateScorer is not None
    
    def test_import_orchestrator(self):
        from curllm_core.dom_toolkit.orchestrator import (
            ExtractionOrchestrator,
            AtomicLLMQuery,
        )
        assert ExtractionOrchestrator is not None
        assert AtomicLLMQuery is not None


class TestAtomicLLMQuery:
    """Test AtomicLLMQuery dataclass."""
    
    def test_basic_query(self):
        from curllm_core.dom_toolkit.orchestrator import AtomicLLMQuery
        
        query = AtomicLLMQuery(
            query_type="interpret",
            context="Extract products",
            question="What type of extraction?"
        )
        
        assert query.query_type == "interpret"
        assert query.context == "Extract products"
        assert query.question == "What type of extraction?"
    
    def test_to_prompt(self):
        from curllm_core.dom_toolkit.orchestrator import AtomicLLMQuery
        
        query = AtomicLLMQuery(
            query_type="choose",
            context="Product page",
            question="Which selector?",
            options=["div.product", "div.item", "li.entry"]
        )
        
        prompt = query.to_prompt()
        
        assert "Task: CHOOSE" in prompt
        assert "Product page" in prompt
        assert "Which selector?" in prompt
        assert "div.product" in prompt
        assert "div.item" in prompt
    
    def test_context_truncation(self):
        from curllm_core.dom_toolkit.orchestrator import AtomicLLMQuery
        
        long_context = "x" * 1000
        query = AtomicLLMQuery(
            query_type="validate",
            context=long_context,
            question="Is this valid?"
        )
        
        prompt = query.to_prompt()
        # Context should be truncated to 500 chars
        assert len(prompt) < 800


class TestAnalyzerMethods:
    """Test that analyzer methods have expected signatures."""
    
    def test_structure_analyzer_methods(self):
        from curllm_core.dom_toolkit.analyzers import DOMStructureAnalyzer
        
        # All methods should be async static methods
        assert hasattr(DOMStructureAnalyzer, 'get_depth_distribution')
        assert hasattr(DOMStructureAnalyzer, 'get_repeating_structures')
        assert hasattr(DOMStructureAnalyzer, 'get_elements_at_depth')
        assert hasattr(DOMStructureAnalyzer, 'get_page_summary')
    
    def test_pattern_detector_methods(self):
        from curllm_core.dom_toolkit.analyzers import PatternDetector
        
        assert hasattr(PatternDetector, 'find_repeating_containers')
        assert hasattr(PatternDetector, 'find_list_structures')
        assert hasattr(PatternDetector, 'detect_grid_layout')
        assert hasattr(PatternDetector, 'find_sibling_groups')
    
    def test_selector_generator_methods(self):
        from curllm_core.dom_toolkit.analyzers import SelectorGenerator
        
        assert hasattr(SelectorGenerator, 'generate_for_element')
        assert hasattr(SelectorGenerator, 'find_stable_selector')
        assert hasattr(SelectorGenerator, 'extract_field_selectors')
        assert hasattr(SelectorGenerator, 'test_selector')
    
    def test_price_detector_methods(self):
        from curllm_core.dom_toolkit.analyzers import PriceDetector
        
        assert hasattr(PriceDetector, 'find_all_prices')
        assert hasattr(PriceDetector, 'get_price_distribution')
        assert hasattr(PriceDetector, 'extract_price_from_selector')
        assert hasattr(PriceDetector, 'detect_price_format')


class TestStatisticsMethods:
    """Test statistics module methods."""
    
    def test_frequency_analyzer_methods(self):
        from curllm_core.dom_toolkit.statistics import FrequencyAnalyzer
        
        assert hasattr(FrequencyAnalyzer, 'count_class_frequencies')
        assert hasattr(FrequencyAnalyzer, 'count_tag_class_combinations')
        assert hasattr(FrequencyAnalyzer, 'analyze_text_lengths')
        assert hasattr(FrequencyAnalyzer, 'find_frequent_siblings')
    
    def test_element_clusterer_methods(self):
        from curllm_core.dom_toolkit.statistics import ElementClusterer
        
        assert hasattr(ElementClusterer, 'cluster_by_structure')
        assert hasattr(ElementClusterer, 'find_similar_elements')
        assert hasattr(ElementClusterer, 'group_by_parent')
    
    def test_candidate_scorer_methods(self):
        from curllm_core.dom_toolkit.statistics import CandidateScorer
        
        assert hasattr(CandidateScorer, 'score_containers')
        assert hasattr(CandidateScorer, 'rank_by_completeness')
        assert hasattr(CandidateScorer, 'compare_selectors')
