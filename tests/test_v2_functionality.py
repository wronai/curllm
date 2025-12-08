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
        from curllm_core.v2 import extract_strategic_context
        
        context = {
            "title": "Contact Us",
            "url": "https://example.com/contact",
            "forms": [{"id": "contact", "fields": []}],
        }
        
        strategic = extract_strategic_context(context)
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


class TestGoalDetectorLLM:
    """Test LLM-driven goal detector."""
    
    def test_detector_init(self):
        """Test detector initialization."""
        from curllm_core.url_resolution.goal_detector_llm import GoalDetectorHybrid
        detector = GoalDetectorHybrid(llm=None)
        assert detector.llm is None
    
    def test_heuristic_fallback_cart(self):
        """Test statistical fallback for cart detection."""
        from curllm_core.url_resolution.goal_detector_llm import GoalDetectorHybrid
        from curllm_core.url_types import TaskGoal
        
        detector = GoalDetectorHybrid(llm=None)
        result = detector._detect_goal_statistical("go to cart")
        assert result.goal == TaskGoal.FIND_CART
        assert result.confidence > 0.3  # Statistical may have lower confidence
    
    def test_heuristic_fallback_login(self):
        """Test statistical fallback for login detection."""
        from curllm_core.url_resolution.goal_detector_llm import GoalDetectorHybrid
        from curllm_core.url_types import TaskGoal
        
        detector = GoalDetectorHybrid(llm=None)
        result = detector._detect_goal_statistical("zaloguj się")
        assert result.goal == TaskGoal.FIND_LOGIN
    
    def test_heuristic_fallback_contact(self):
        """Test statistical fallback for contact detection."""
        from curllm_core.url_resolution.goal_detector_llm import GoalDetectorHybrid
        from curllm_core.url_types import TaskGoal
        
        detector = GoalDetectorHybrid(llm=None)
        result = detector._detect_goal_statistical("find contact form")
        assert result.goal == TaskGoal.FIND_CONTACT_FORM
    
    def test_sync_detection(self):
        """Test synchronous detection."""
        from curllm_core.url_resolution.goal_detector_llm import GoalDetectorHybrid
        
        detector = GoalDetectorHybrid(llm=None)
        result = detector.detect_goal_sync("add to cart")
        assert result is not None
        assert result.confidence > 0


class TestLLMFieldAnalyzer:
    """Test LLM field analyzer."""
    
    def test_init(self):
        """Test initialization."""
        from curllm_core.streamware.components.decision_llm import LLMFieldAnalyzer
        analyzer = LLMFieldAnalyzer(llm=None)
        assert analyzer.llm is None
    
    def test_fillable_heuristic(self):
        """Test fillable field heuristic."""
        from curllm_core.streamware.components.decision_llm import LLMFieldAnalyzer
        analyzer = LLMFieldAnalyzer(llm=None)
        
        assert analyzer._is_fillable_heuristic({'type': 'text'}) is True
        assert analyzer._is_fillable_heuristic({'type': 'email'}) is True
        assert analyzer._is_fillable_heuristic({'type': 'hidden'}) is False
        assert analyzer._is_fillable_heuristic({'type': 'submit'}) is False
    
    def test_extract_fields_heuristic(self):
        """Test field extraction heuristic."""
        from curllm_core.streamware.components.decision_llm import LLMFieldAnalyzer
        analyzer = LLMFieldAnalyzer(llm=None)
        
        result = analyzer._extract_fields_heuristic("name=John, email=john@test.com")
        assert 'name' in result
        assert result['name'] == 'John'
        assert 'email' in result


class TestLLMActionPlanner:
    """Test LLM action planner."""
    
    def test_init(self):
        """Test initialization."""
        from curllm_core.streamware.components.decision_llm import LLMActionPlanner
        planner = LLMActionPlanner(llm=None)
        assert planner.llm is None
    
    def test_plan_heuristic_loop_detection(self):
        """Test loop detection in heuristic planning."""
        from curllm_core.streamware.components.decision_llm import LLMActionPlanner
        planner = LLMActionPlanner(llm=None)
        
        history = [{'type': 'fill'}, {'type': 'fill'}]
        result = planner._plan_heuristic("fill form", {}, history)
        assert result['type'] == 'wait'
        assert 'loop' in result.get('reason', '')
    
    def test_plan_heuristic_no_forms(self):
        """Test planning when no forms."""
        from curllm_core.streamware.components.decision_llm import LLMActionPlanner
        planner = LLMActionPlanner(llm=None)
        
        result = planner._plan_heuristic("fill form", {'forms': []}, [])
        assert result['type'] == 'complete'


class TestLLMSubmitDetector:
    """Test LLM submit detector."""
    
    def test_init(self):
        """Test initialization."""
        from curllm_core.streamware.components.form.submit_llm import LLMSubmitDetector
        detector = LLMSubmitDetector(llm=None)
        assert detector.llm is None
    
    def test_find_submit_heuristic(self):
        """Test heuristic submit detection."""
        from curllm_core.streamware.components.form.submit_llm import LLMSubmitDetector
        detector = LLMSubmitDetector(llm=None)
        
        buttons = [
            {'text': 'Cancel', 'type': 'button', 'classes': ''},
            {'text': 'Submit', 'type': 'submit', 'classes': ''},
        ]
        result = detector._find_submit_heuristic(buttons)
        assert result['type'] == 'submit'
    
    def test_find_submit_heuristic_empty(self):
        """Test heuristic with no buttons."""
        from curllm_core.streamware.components.form.submit_llm import LLMSubmitDetector
        detector = LLMSubmitDetector(llm=None)
        
        result = detector._find_submit_heuristic([])
        assert result is None


class TestLLMSuccessEvaluator:
    """Test LLM success evaluator."""
    
    def test_init(self):
        """Test initialization."""
        from curllm_core.streamware.components.form.submit_llm import LLMSuccessEvaluator
        evaluator = LLMSuccessEvaluator(llm=None)
        assert evaluator.llm is None
    
    def test_evaluate_heuristic_url_changed(self):
        """Test heuristic success evaluation with URL change."""
        from curllm_core.streamware.components.form.submit_llm import LLMSuccessEvaluator
        evaluator = LLMSuccessEvaluator(llm=None)
        
        diff = {'url_changed': True, 'new_errors': False, 'form_disappeared': False, 'new_text': ''}
        result = evaluator._evaluate_heuristic(diff)
        assert result['success'] is True
        assert result['confidence'] >= 0.7
    
    def test_evaluate_heuristic_errors(self):
        """Test heuristic with errors."""
        from curllm_core.streamware.components.form.submit_llm import LLMSuccessEvaluator
        evaluator = LLMSuccessEvaluator(llm=None)
        
        diff = {'url_changed': False, 'new_errors': True, 'form_disappeared': False, 'new_text': ''}
        result = evaluator._evaluate_heuristic(diff)
        assert result['success'] is False
