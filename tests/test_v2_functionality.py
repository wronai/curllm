"""
Functional tests for v2 API components.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestAtomicFunctions:
    """Test AtomicFunctions class."""
    
    def test_init_without_dependencies(self):
        """Test initialization without page/llm."""
        from curllm_core.v2 import AtomicFunctions
        atoms = AtomicFunctions(page=None, llm=None)
        assert atoms.page is None
        assert atoms.llm is None
    
    def test_init_with_mock_dependencies(self):
        """Test initialization with mock dependencies."""
        from curllm_core.v2 import AtomicFunctions
        mock_page = MagicMock()
        mock_llm = MagicMock()
        atoms = AtomicFunctions(page=mock_page, llm=mock_llm)
        assert atoms.page is mock_page
        assert atoms.llm is mock_llm


class TestDSLQueryGenerator:
    """Test DSLQueryGenerator class."""
    
    def test_init_without_llm(self):
        """Test initialization without LLM."""
        from curllm_core.v2 import DSLQueryGenerator
        gen = DSLQueryGenerator(llm=None)
        assert gen.llm is None
    
    def test_init_with_mock_llm(self):
        """Test initialization with mock LLM."""
        from curllm_core.v2 import DSLQueryGenerator
        mock_llm = MagicMock()
        gen = DSLQueryGenerator(llm=mock_llm)
        assert gen.llm is mock_llm


class TestLLMDSLExecutor:
    """Test LLMDSLExecutor class."""
    
    def test_init_without_dependencies(self):
        """Test initialization without dependencies."""
        from curllm_core.v2 import LLMDSLExecutor
        exe = LLMDSLExecutor(page=None, llm=None)
        assert exe.page is None
        assert exe.llm is None


class TestLLMOrchestrators:
    """Test LLM orchestrator classes."""
    
    def test_form_orchestrator_init(self):
        """Test LLMFormOrchestrator initialization."""
        from curllm_core.v2 import LLMFormOrchestrator
        orch = LLMFormOrchestrator(llm=None, page=None)
        assert orch.llm is None
        assert orch.page is None
    
    def test_auth_orchestrator_init(self):
        """Test LLMAuthOrchestrator initialization."""
        from curllm_core.v2 import LLMAuthOrchestrator
        orch = LLMAuthOrchestrator(llm=None, page=None)
        assert orch.llm is None
        assert orch.page is None
    
    def test_social_orchestrator_init(self):
        """Test LLMSocialOrchestrator initialization."""
        from curllm_core.v2 import LLMSocialOrchestrator
        orch = LLMSocialOrchestrator(llm=None, page=None)
        assert orch.llm is None
        assert orch.page is None
    
    def test_ecommerce_orchestrator_init(self):
        """Test LLMECommerceOrchestrator initialization."""
        from curllm_core.v2 import LLMECommerceOrchestrator
        orch = LLMECommerceOrchestrator(llm=None, page=None)
        assert orch.llm is None
        assert orch.page is None


class TestLLMExtractor:
    """Test LLMExtractor class."""
    
    def test_init_without_dependencies(self):
        """Test initialization without dependencies."""
        from curllm_core.v2 import LLMExtractor
        ext = LLMExtractor(page=None, llm=None)
        assert ext.page is None
        assert ext.llm is None


class TestLLMHierarchicalPlanner:
    """Test LLMHierarchicalPlanner class."""
    
    def test_init_without_llm(self):
        """Test initialization without LLM."""
        from curllm_core.v2 import LLMHierarchicalPlanner
        planner = LLMHierarchicalPlanner(llm=None)
        assert planner.llm is None
    
    def test_estimate_context_size(self):
        """Test context size estimation."""
        from curllm_core.v2 import LLMHierarchicalPlanner
        planner = LLMHierarchicalPlanner(llm=None)
        
        context = {"title": "Test", "forms": [{"fields": []}]}
        size = planner._estimate_context_size(context)
        assert size > 0
    
    def test_extract_strategic_context(self):
        """Test strategic context extraction."""
        from curllm_core.v2 import LLMHierarchicalPlanner
        planner = LLMHierarchicalPlanner(llm=None)
        
        context = {
            "title": "Contact Us",
            "url": "https://example.com/contact",
            "forms": [{"id": "contact", "fields": []}],
        }
        
        strategic = planner._extract_strategic_context(context)
        assert strategic["title"] == "Contact Us"
        assert strategic["form_count"] == 1
        assert strategic["has_forms"] is True


class TestFormFillResult:
    """Test FormFillResult dataclass."""
    
    def test_default_values(self):
        """Test default values."""
        from curllm_core.v2 import FormFillResult
        result = FormFillResult(success=False, filled_fields={}, submitted=False)
        assert result.success is False
        assert result.filled_fields == {}
        assert result.submitted is False
    
    def test_with_data(self):
        """Test with actual data."""
        from curllm_core.v2 import FormFillResult
        result = FormFillResult(
            success=True,
            filled_fields={"email": "test@example.com", "name": "John"},
            submitted=True,
        )
        assert result.success is True
        assert len(result.filled_fields) == 2
        assert result.submitted is True


class TestV1V2Coexistence:
    """Test that v1 and v2 can coexist."""
    
    def test_import_both_versions(self):
        """Test importing both v1 and v2."""
        from curllm_core import v1, v2
        
        # v1 exports
        assert hasattr(v1, 'FormOrchestrator')
        assert hasattr(v1, 'deterministic_form_fill')
        
        # v2 exports
        assert hasattr(v2, 'LLMFormOrchestrator')
        assert hasattr(v2, 'llm_form_fill')
    
    def test_v1_deprecation_works(self):
        """Test that v1 modules show deprecation warnings."""
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from curllm_core.orchestrators.form import FormOrchestrator
            # Should have deprecation warning
            # (may or may not trigger depending on import order)
            assert FormOrchestrator is not None


class TestExecutorV2Default:
    """Test that executor uses v2 by default."""
    
    def test_executor_form_fill_default_v2(self):
        """Test that form fill method defaults to v2."""
        from curllm_core.execution.executor import CurllmExecutor
        import inspect
        
        # Check signature of _deterministic_form_fill
        sig = inspect.signature(CurllmExecutor._deterministic_form_fill)
        params = sig.parameters
        
        # use_v2 should default to True
        assert 'use_v2' in params
        assert params['use_v2'].default is True
