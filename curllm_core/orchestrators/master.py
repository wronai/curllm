"""
Master Orchestrator - Intelligent task routing and orchestration

The MasterOrchestrator:
1. Analyzes the user's instruction to detect task type
2. Routes to the appropriate specialized orchestrator
3. Coordinates multi-step workflows
4. Aggregates results and provides validation
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass


class TaskType(Enum):
    """Supported task types"""
    FORM_FILL = "form_fill"
    EXTRACTION = "extraction"
    ECOMMERCE = "ecommerce"
    SOCIAL_MEDIA = "social_media"
    LIVE_INTERACTION = "live_interaction"
    AUTH = "auth"
    NAVIGATION = "navigation"
    UNKNOWN = "unknown"


@dataclass
class TaskAnalysis:
    """Result of task analysis"""
    task_type: TaskType
    confidence: float
    subtasks: List[str]
    required_capabilities: List[str]
    metadata: Dict[str, Any]


class MasterOrchestrator:
    """
    Master orchestrator for routing and coordinating complex tasks.
    
    Features:
    - Intelligent task type detection
    - Multi-step workflow orchestration
    - Parallel subtask execution
    - Result aggregation and validation
    - Error recovery and fallback strategies
    """
    
    # Task detection keywords
    TASK_KEYWORDS = {
        TaskType.FORM_FILL: [
            'fill', 'form', 'submit', 'login', 'register', 'contact', 'signup',
            'formularz', 'wypełnij', 'wyślij', 'zaloguj', 'zarejestruj', 'kontakt'
        ],
        TaskType.EXTRACTION: [
            'extract', 'get', 'find', 'scrape', 'collect', 'list', 'show',
            'wyciągnij', 'pobierz', 'znajdź', 'zbierz', 'pokaż', 'wylistuj'
        ],
        TaskType.ECOMMERCE: [
            'buy', 'purchase', 'add to cart', 'checkout', 'order', 'pay', 
            'product', 'price', 'shop', 'koszyk', 'kup', 'zamów', 'zapłać',
            'dodaj do koszyka', 'sklep', 'cena', 'produkt'
        ],
        TaskType.SOCIAL_MEDIA: [
            'facebook', 'twitter', 'instagram', 'linkedin', 'tiktok', 'youtube',
            'post', 'share', 'like', 'comment', 'follow', 'message', 'dm',
            'udostępnij', 'polub', 'komentarz', 'obserwuj', 'wiadomość'
        ],
        TaskType.LIVE_INTERACTION: [
            'click', 'scroll', 'hover', 'drag', 'type', 'select', 'wait',
            'kliknij', 'przewiń', 'najedź', 'przeciągnij', 'wpisz', 'wybierz'
        ],
        TaskType.AUTH: [
            'login', 'sign in', 'authenticate', 'log in', 'signin',
            'zaloguj', 'zaloguj się', 'uwierzytelnij', 'autoryzacja',
            '2fa', 'two-factor', 'otp', 'verification code'
        ],
        TaskType.NAVIGATION: [
            'go to', 'navigate', 'open', 'visit', 'browse',
            'przejdź', 'otwórz', 'odwiedź'
        ]
    }
    
    def __init__(self, llm=None, page=None, run_logger=None):
        """
        Initialize master orchestrator.
        
        Args:
            llm: LLM client for decision making
            page: Playwright page object
            run_logger: Logger for run documentation
        """
        self.llm = llm
        self.page = page
        self.run_logger = run_logger
        
        # Lazy-load specialized orchestrators
        self._form_orch = None
        self._extraction_orch = None
        self._ecommerce_orch = None
        self._social_orch = None
        self._live_orch = None
        self._auth_orch = None
    
    async def orchestrate(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main orchestration entry point.
        
        Args:
            instruction: User's task instruction
            page_context: Current page state (DOM, forms, etc.)
            
        Returns:
            Orchestration result with data, validation, and metadata
        """
        self._log("🎭 MASTER ORCHESTRATOR", "header")
        self._log(f"Instruction: {instruction[:200]}")
        
        # Phase 1: Analyze task
        analysis = await self.analyze_task(instruction, page_context)
        self._log(f"Task Type: {analysis.task_type.value} (confidence: {analysis.confidence:.0%})")
        
        # Phase 2: Plan execution
        plan = await self.plan_execution(analysis, page_context)
        self._log(f"Execution Plan: {len(plan)} steps")
        
        # Phase 3: Execute with appropriate orchestrator
        result = await self.execute_plan(instruction, analysis, plan, page_context)
        
        # Phase 4: Validate result
        validation = await self.validate_result(instruction, result, analysis)
        
        # Phase 5: Aggregate and return
        return {
            'success': validation.get('passed', False),
            'data': result,
            'task_type': analysis.task_type.value,
            'validation': validation,
            'plan_executed': plan,
            'metadata': analysis.metadata
        }
    
    async def analyze_task(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]] = None
    ) -> TaskAnalysis:
        """
        Analyze instruction to determine task type and requirements.
        
        Uses keyword matching first, then LLM for ambiguous cases.
        """
        # Keyword-based detection
        keyword_result = self._detect_by_keywords(instruction)
        
        # If high confidence, return immediately
        if keyword_result.confidence >= 0.8:
            return keyword_result
        
        # Use LLM for ambiguous cases
        if self.llm and keyword_result.confidence < 0.6:
            llm_result = await self._detect_with_llm(instruction, page_context)
            if llm_result.confidence > keyword_result.confidence:
                return llm_result
        
        return keyword_result
    
    def _detect_by_keywords(self, instruction: str) -> TaskAnalysis:
        """Detect task type using keyword matching"""
        instr_lower = instruction.lower()
        
        scores = {}
        for task_type, keywords in self.TASK_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in instr_lower)
            scores[task_type] = matches / len(keywords) if keywords else 0
        
        # Find best match
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # Determine confidence
        if best_score >= 0.3:
            confidence = min(0.9, 0.5 + best_score)
        elif best_score > 0:
            confidence = 0.4 + best_score
        else:
            confidence = 0.3
            best_type = TaskType.UNKNOWN
        
        # Detect subtasks
        subtasks = self._detect_subtasks(instruction)
        
        # Detect required capabilities
        capabilities = self._detect_capabilities(instruction, best_type)
        
        return TaskAnalysis(
            task_type=best_type,
            confidence=confidence,
            subtasks=subtasks,
            required_capabilities=capabilities,
            metadata={
                'detection_method': 'keywords',
                'keyword_scores': {t.value: s for t, s in scores.items() if s > 0}
            }
        )
    
    async def _detect_with_llm(
        self,
        instruction: str,
        page_context: Optional[Dict[str, Any]]
    ) -> TaskAnalysis:
        """Use LLM to detect task type"""
        
        url = page_context.get('url', 'unknown') if page_context else 'unknown'
        
        prompt = f"""Analyze this web automation task and classify it.

INSTRUCTION: {instruction}
PAGE URL: {url}

TASK TYPES:
- form_fill: Fill and submit forms (contact, registration)
- extraction: Extract data from page (products, links, articles)
- ecommerce: Shopping actions (add to cart, checkout, payment)
- social_media: Social platform actions (post, message, share)
- live_interaction: Direct UI interactions (click, scroll, type)
- auth: Authentication tasks (login, sign in, 2FA, OAuth)
- navigation: Simple page navigation

RESPOND JSON:
{{
    "task_type": "one of the types above",
    "confidence": 0.0-1.0,
    "subtasks": ["list", "of", "subtasks"],
    "reasoning": "brief explanation"
}}

JSON:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            text = response.get('text', '')
            
            # Parse JSON
            start = text.find('{')
            end = text.rfind('}')
            if start >= 0 and end > start:
                data = json.loads(text[start:end+1])
                
                task_type = TaskType[data['task_type'].upper()]
                
                return TaskAnalysis(
                    task_type=task_type,
                    confidence=float(data.get('confidence', 0.7)),
                    subtasks=data.get('subtasks', []),
                    required_capabilities=[],
                    metadata={
                        'detection_method': 'llm',
                        'reasoning': data.get('reasoning', '')
                    }
                )
        except Exception as e:
            self._log(f"LLM detection failed: {e}", "warning")
        
        # Fallback
        return TaskAnalysis(
            task_type=TaskType.UNKNOWN,
            confidence=0.3,
            subtasks=[],
            required_capabilities=[],
            metadata={'detection_method': 'llm_failed'}
        )
    
    def _detect_subtasks(self, instruction: str) -> List[str]:
        """Detect subtasks in instruction"""
        subtasks = []
        instr_lower = instruction.lower()
        
        # Navigation subtask
        if any(kw in instr_lower for kw in ['go to', 'navigate', 'open', 'przejdź']):
            subtasks.append('navigation')
        
        # Captcha subtask
        if any(kw in instr_lower for kw in ['captcha', 'verification', 'verify']):
            subtasks.append('captcha_solve')
        
        # Wait/load subtask
        if any(kw in instr_lower for kw in ['wait', 'load', 'scroll']):
            subtasks.append('wait_for_content')
        
        # Validation subtask
        if any(kw in instr_lower for kw in ['verify', 'check', 'confirm', 'sprawdź']):
            subtasks.append('validation')
        
        return subtasks
    
    def _detect_capabilities(
        self,
        instruction: str,
        task_type: TaskType
    ) -> List[str]:
        """Detect required capabilities for the task"""
        capabilities = []
        instr_lower = instruction.lower()
        
        # Vision capability
        if any(kw in instr_lower for kw in ['image', 'screenshot', 'visual', 'see']):
            capabilities.append('vision')
        
        # Captcha solving
        if 'captcha' in instr_lower:
            capabilities.append('captcha_solver')
        
        # Stealth mode
        if any(kw in instr_lower for kw in ['stealth', 'bypass', 'avoid detection']):
            capabilities.append('stealth')
        
        # Based on task type
        if task_type == TaskType.ECOMMERCE:
            capabilities.extend(['cart_management', 'payment_handling'])
        elif task_type == TaskType.SOCIAL_MEDIA:
            capabilities.extend(['session_management', 'captcha_solver'])
        elif task_type == TaskType.FORM_FILL:
            capabilities.extend(['form_detection', 'field_mapping'])
        elif task_type == TaskType.EXTRACTION:
            capabilities.extend(['dom_analysis', 'data_parsing'])
        
        return list(set(capabilities))
    
    async def plan_execution(
        self,
        analysis: TaskAnalysis,
        page_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create execution plan based on task analysis.
        
        Returns list of steps with actions and parameters.
        """
        plan = []
        
        # Add navigation step if needed
        if 'navigation' in analysis.subtasks:
            plan.append({
                'step': 'navigate',
                'action': 'goto',
                'priority': 1
            })
        
        # Add captcha handling if needed
        if 'captcha_solver' in analysis.required_capabilities:
            plan.append({
                'step': 'captcha',
                'action': 'detect_and_solve',
                'priority': 2
            })
        
        # Add main task step
        plan.append({
            'step': 'main',
            'action': analysis.task_type.value,
            'priority': 3,
            'subtasks': analysis.subtasks
        })
        
        # Add validation step
        if 'validation' in analysis.subtasks:
            plan.append({
                'step': 'validate',
                'action': 'verify_completion',
                'priority': 4
            })
        
        return sorted(plan, key=lambda x: x.get('priority', 99))
    
    async def execute_plan(
        self,
        instruction: str,
        analysis: TaskAnalysis,
        plan: List[Dict[str, Any]],
        page_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Execute the planned steps using appropriate orchestrators.
        """
        result = {}
        
        for step in plan:
            action = step.get('action')
            
            try:
                if action == analysis.task_type.value:
                    # Execute main task with specialized orchestrator
                    result = await self._execute_main_task(
                        instruction, analysis.task_type, page_context
                    )
                elif action == 'goto':
                    # Navigation step
                    if self.page:
                        # Extract URL from instruction if present
                        import re
                        url_match = re.search(r'https?://[^\s"\']+', instruction)
                        if url_match:
                            await self.page.goto(url_match.group())
                            result['navigated'] = True
                elif action == 'detect_and_solve':
                    # Captcha handling
                    result['captcha'] = await self._handle_captcha()
                elif action == 'verify_completion':
                    # Validation step - handled in validate_result
                    pass
                    
            except Exception as e:
                self._log(f"Step '{action}' failed: {e}", "error")
                result['errors'] = result.get('errors', []) + [str(e)]
        
        return result
    
    async def _execute_main_task(
        self,
        instruction: str,
        task_type: TaskType,
        page_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute main task with appropriate orchestrator"""
        
        if task_type == TaskType.FORM_FILL:
            orch = self._get_form_orchestrator()
            return await orch.orchestrate(instruction, page_context)
        
        elif task_type == TaskType.EXTRACTION:
            orch = self._get_extraction_orchestrator()
            return await orch.orchestrate(instruction, page_context)
        
        elif task_type == TaskType.ECOMMERCE:
            orch = self._get_ecommerce_orchestrator()
            return await orch.orchestrate(instruction, page_context)
        
        elif task_type == TaskType.SOCIAL_MEDIA:
            orch = self._get_social_orchestrator()
            return await orch.orchestrate(instruction, page_context)
        
        elif task_type == TaskType.LIVE_INTERACTION:
            orch = self._get_live_orchestrator()
            return await orch.orchestrate(instruction, page_context)
        
        elif task_type == TaskType.AUTH:
            orch = self._get_auth_orchestrator()
            return await orch.orchestrate(instruction, page_context)
        
        else:
            # Fallback to extraction
            orch = self._get_extraction_orchestrator()
            return await orch.orchestrate(instruction, page_context)
    
    async def validate_result(
        self,
        instruction: str,
        result: Dict[str, Any],
        analysis: TaskAnalysis
    ) -> Dict[str, Any]:
        """Validate the execution result"""
        
        from ..validation import CompositeValidator
        
        validator = CompositeValidator(llm=self.llm)
        
        # Get screenshot if page available
        screenshot = None
        if self.page:
            try:
                screenshot = await self.page.screenshot()
            except Exception:
                pass
        
        validation = await validator.validate(
            instruction=instruction,
            result=result,
            screenshot=screenshot
        )
        
        return validation.to_dict()
    
    async def _handle_captcha(self) -> Dict[str, Any]:
        """Detect and solve captcha if present"""
        if not self.page:
            return {'detected': False}
        
        try:
            # Import captcha module
            from ..captcha import detect_captcha, solve_captcha
            
            detected = await detect_captcha(self.page)
            if detected:
                self._log("Captcha detected, attempting to solve...")
                solved = await solve_captcha(self.page, detected)
                return {'detected': True, 'solved': solved}
            
            return {'detected': False}
        except ImportError:
            return {'detected': False, 'note': 'Captcha module not available'}
    
    # Lazy-load orchestrators
    def _get_form_orchestrator(self):
        if self._form_orch is None:
            from .form import FormOrchestrator
            self._form_orch = FormOrchestrator(self.llm, self.page, self.run_logger)
        return self._form_orch
    
    def _get_extraction_orchestrator(self):
        if self._extraction_orch is None:
            from .extraction import ExtractionOrchestrator
            self._extraction_orch = ExtractionOrchestrator(self.llm, self.page, self.run_logger)
        return self._extraction_orch
    
    def _get_ecommerce_orchestrator(self):
        if self._ecommerce_orch is None:
            from .ecommerce import ECommerceOrchestrator
            self._ecommerce_orch = ECommerceOrchestrator(self.llm, self.page, self.run_logger)
        return self._ecommerce_orch
    
    def _get_social_orchestrator(self):
        if self._social_orch is None:
            from .social import SocialMediaOrchestrator
            self._social_orch = SocialMediaOrchestrator(self.llm, self.page, self.run_logger)
        return self._social_orch
    
    def _get_live_orchestrator(self):
        if self._live_orch is None:
            from .live import LiveInteractionOrchestrator
            self._live_orch = LiveInteractionOrchestrator(self.llm, self.page, self.run_logger)
        return self._live_orch
    
    def _get_auth_orchestrator(self):
        if self._auth_orch is None:
            from .auth import AuthOrchestrator
            self._auth_orch = AuthOrchestrator(self.llm, self.page, self.run_logger)
        return self._auth_orch
    
    def _log(self, message: str, level: str = "info"):
        """Log message with formatting"""
        if self.run_logger:
            if level == "header":
                self.run_logger.log_text(f"\n{'='*60}")
                self.run_logger.log_text(message)
                self.run_logger.log_text(f"{'='*60}\n")
            elif level == "error":
                self.run_logger.log_text(f"❌ {message}")
            elif level == "warning":
                self.run_logger.log_text(f"⚠️  {message}")
            else:
                self.run_logger.log_text(f"   {message}")

