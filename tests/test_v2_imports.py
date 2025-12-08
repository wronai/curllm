"""
Tests for v2 API imports and basic functionality.
"""

import pytest


class TestV2Imports:
    """Test that all v2 exports are importable."""
    
    def test_v2_package_import(self):
        """Test v2 package imports successfully."""
        from curllm_core import v2
        assert hasattr(v2, '__all__')
        assert len(v2.__all__) >= 15
    
    def test_v2_core_imports(self):
        """Test core LLM-DSL imports."""
        from curllm_core.v2 import (
            AtomicFunctions,
            DSLQueryGenerator,
            DSLQueryExecutor,
        )
        assert AtomicFunctions is not None
        assert DSLQueryGenerator is not None
        assert DSLQueryExecutor is not None
    
    def test_v2_form_fill_imports(self):
        """Test form filling imports."""
        from curllm_core.v2 import (
            llm_form_fill,
            smart_form_fill,
            FormFillResult,
        )
        assert callable(llm_form_fill)
        assert callable(smart_form_fill)
        assert FormFillResult is not None
    
    def test_v2_orchestrator_imports(self):
        """Test orchestrator imports."""
        from curllm_core.v2 import (
            LLMFormOrchestrator,
            LLMAuthOrchestrator,
            LLMSocialOrchestrator,
            LLMECommerceOrchestrator,
        )
        assert LLMFormOrchestrator is not None
        assert LLMAuthOrchestrator is not None
        assert LLMSocialOrchestrator is not None
        assert LLMECommerceOrchestrator is not None
    
    def test_v2_extraction_imports(self):
        """Test extraction imports."""
        from curllm_core.v2 import (
            LLMExtractor,
            llm_extract,
            extract_with_llm,
        )
        assert LLMExtractor is not None
        assert callable(llm_extract)
        assert callable(extract_with_llm)
    
    def test_v2_planning_imports(self):
        """Test planning imports."""
        from curllm_core.v2 import (
            LLMHierarchicalPlanner,
            should_use_hierarchical_llm,
        )
        assert LLMHierarchicalPlanner is not None
        assert callable(should_use_hierarchical_llm)
    
    def test_v2_dsl_imports(self):
        """Test DSL imports."""
        from curllm_core.v2 import (
            LLMDSLExecutor,
            LLMExecutionResult,
        )
        assert LLMDSLExecutor is not None
        assert LLMExecutionResult is not None


class TestV1Imports:
    """Test that v1 (legacy) exports are still importable."""
    
    def test_v1_package_import(self):
        """Test v1 package imports successfully."""
        from curllm_core import v1
        assert hasattr(v1, '__all__')
        assert len(v1.__all__) >= 10
    
    def test_v1_form_imports(self):
        """Test form filling imports."""
        from curllm_core.v1 import (
            deterministic_form_fill,
            FormOrchestrator,
        )
        assert callable(deterministic_form_fill)
        assert FormOrchestrator is not None
    
    def test_v1_orchestrator_imports(self):
        """Test orchestrator imports."""
        from curllm_core.v1 import (
            AuthOrchestrator,
            SocialMediaOrchestrator,
            ECommerceOrchestrator,
        )
        assert AuthOrchestrator is not None
        assert SocialMediaOrchestrator is not None
        assert ECommerceOrchestrator is not None


class TestV2Classes:
    """Test v2 class instantiation (without page/llm)."""
    
    def test_atomic_functions_init(self):
        """Test AtomicFunctions can be instantiated."""
        from curllm_core.v2 import AtomicFunctions
        atoms = AtomicFunctions(page=None, llm=None)
        assert atoms is not None
        assert atoms.page is None
        assert atoms.llm is None
    
    def test_llm_form_orchestrator_init(self):
        """Test LLMFormOrchestrator can be instantiated."""
        from curllm_core.v2 import LLMFormOrchestrator
        orch = LLMFormOrchestrator(llm=None, page=None)
        assert orch is not None
    
    def test_llm_auth_orchestrator_init(self):
        """Test LLMAuthOrchestrator can be instantiated."""
        from curllm_core.v2 import LLMAuthOrchestrator
        orch = LLMAuthOrchestrator(llm=None, page=None)
        assert orch is not None
    
    def test_llm_extractor_init(self):
        """Test LLMExtractor can be instantiated."""
        from curllm_core.v2 import LLMExtractor
        ext = LLMExtractor(page=None, llm=None)
        assert ext is not None
    
    def test_llm_dsl_executor_init(self):
        """Test LLMDSLExecutor can be instantiated."""
        from curllm_core.v2 import LLMDSLExecutor
        exe = LLMDSLExecutor(page=None, llm=None)
        assert exe is not None
    
    def test_llm_hierarchical_planner_init(self):
        """Test LLMHierarchicalPlanner can be instantiated."""
        from curllm_core.v2 import LLMHierarchicalPlanner
        planner = LLMHierarchicalPlanner(llm=None)
        assert planner is not None


class TestFormFillResult:
    """Test FormFillResult dataclass."""
    
    def test_form_fill_result_creation(self):
        """Test FormFillResult can be created."""
        from curllm_core.v2 import FormFillResult
        result = FormFillResult(
            success=True,
            filled_fields={'email': 'test@example.com'},
            submitted=True,
        )
        assert result.success is True
        assert result.filled_fields['email'] == 'test@example.com'
        assert result.submitted is True


class TestCLIV1Flag:
    """Test CLI --v1 flag (v2 is now default)."""
    
    def test_cli_help_contains_v1(self):
        """Test that CLI help mentions --v1 for legacy mode."""
        import subprocess
        result = subprocess.run(
            ['./curllm', '--help'],
            capture_output=True,
            text=True,
            cwd='/home/tom/github/wronai/curllm'
        )
        assert '--v1' in result.stdout
        assert 'legacy' in result.stdout.lower() or 'deprecated' in result.stdout.lower()
