"""
Task Planner - Create execution plans from parsed commands

Takes a ParsedCommand and generates a step-by-step TaskPlan
that the Orchestrator can execute.

Plans include:
- Navigation steps
- URL resolution steps
- Form filling steps
- Extraction steps
- Verification steps
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from curllm_core.command_parser import ParsedCommand, FormData
from curllm_core.url_types import TaskGoal

logger = logging.getLogger(__name__)


class StepType(Enum):
    """Types of execution steps"""
    NAVIGATE = "navigate"           # Go to URL
    RESOLVE = "resolve"             # Use UrlResolver to find page
    ANALYZE = "analyze"             # Analyze page content
    WAIT = "wait"                   # Wait for element/time
    SEARCH = "search"               # Use site search
    FILL_FIELD = "fill_field"       # Fill single form field
    FILL_FORM = "fill_form"         # Fill entire form
    CLICK = "click"                 # Click element
    SUBMIT = "submit"               # Submit form
    EXTRACT = "extract"             # Extract data
    VERIFY = "verify"               # Verify outcome
    SCREENSHOT = "screenshot"       # Take screenshot


class StepStatus(Enum):
    """Status of a step"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskStep:
    """Single execution step"""
    step_type: StepType
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    
    # Execution control
    timeout_ms: int = 30000
    retry_count: int = 2
    optional: bool = False
    
    # Dependencies (step indices that must complete first)
    depends_on: List[int] = field(default_factory=list)
    
    # Fallback step if this fails
    fallback: Optional['TaskStep'] = None
    
    # Runtime state
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class TaskPlan:
    """Complete execution plan"""
    steps: List[TaskStep] = field(default_factory=list)
    
    # Metadata
    description: str = ""
    expected_outcome: str = ""
    
    # Configuration
    total_timeout_seconds: int = 120
    stop_on_failure: bool = True
    
    # Source
    parsed_command: Optional[ParsedCommand] = None
    
    def add_step(
        self,
        step_type: StepType,
        params: Dict[str, Any] = None,
        description: str = "",
        **kwargs
    ) -> int:
        """Add step and return its index"""
        step = TaskStep(
            step_type=step_type,
            params=params or {},
            description=description,
            **kwargs
        )
        self.steps.append(step)
        return len(self.steps) - 1
    
    def get_pending_steps(self) -> List[TaskStep]:
        """Get steps that are ready to execute"""
        pending = []
        for i, step in enumerate(self.steps):
            if step.status == StepStatus.PENDING:
                # Check dependencies
                deps_met = all(
                    self.steps[dep].status == StepStatus.COMPLETED
                    for dep in step.depends_on
                )
                if deps_met:
                    pending.append(step)
        return pending
    
    def is_complete(self) -> bool:
        """Check if all steps are done"""
        return all(
            step.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
            for step in self.steps
        )
    
    def has_failed(self) -> bool:
        """Check if any required step failed"""
        return any(
            step.status == StepStatus.FAILED and not step.optional
            for step in self.steps
        )


class TaskPlanner:
    """
    Create execution plans from parsed commands.
    
    Usage:
        planner = TaskPlanner()
        plan = planner.plan(parsed_command)
        
        for step in plan.steps:
            print(f"{step.step_type}: {step.description}")
    """
    
    def plan(
        self,
        parsed: ParsedCommand,
        page_context: Optional[Dict[str, Any]] = None
    ) -> TaskPlan:
        """
        Create execution plan for a parsed command.
        
        Args:
            parsed: Parsed command with goals and data
            page_context: Optional current page state
            
        Returns:
            TaskPlan with ordered steps
        """
        plan = TaskPlan(
            parsed_command=parsed,
            description=f"Execute: {parsed.primary_goal.value}"
        )
        
        # 1. Navigation step (if we have a target)
        if parsed.get_url():
            plan.add_step(
                StepType.NAVIGATE,
                params={"url": parsed.get_url()},
                description=f"Navigate to {parsed.target_domain}"
            )
        
        # 2. URL Resolution based on goal
        if parsed.primary_goal != TaskGoal.GENERIC:
            nav_step = len(plan.steps) - 1 if plan.steps else -1
            plan.add_step(
                StepType.RESOLVE,
                params={"goal": parsed.primary_goal.value},
                description=f"Find {parsed.primary_goal.value}",
                depends_on=[nav_step] if nav_step >= 0 else []
            )
        
        # 3. Page analysis
        resolve_step = len(plan.steps) - 1
        plan.add_step(
            StepType.ANALYZE,
            params={"expected": self._expected_for_goal(parsed.primary_goal)},
            description="Analyze page structure",
            depends_on=[resolve_step]
        )
        
        # 4. Goal-specific steps
        self._add_goal_steps(plan, parsed)
        
        # 5. Verification
        plan.add_step(
            StepType.VERIFY,
            params={"expected": plan.expected_outcome},
            description="Verify outcome",
            optional=True
        )
        
        # 6. Screenshot (optional)
        plan.add_step(
            StepType.SCREENSHOT,
            params={"name": "final_state"},
            description="Capture final state",
            optional=True
        )
        
        logger.info(f"Created plan with {len(plan.steps)} steps")
        return plan
    
    def _expected_for_goal(self, goal: TaskGoal) -> str:
        """Get expected page content for a goal"""
        expectations = {
            TaskGoal.FIND_CONTACT_FORM: "form_fields",
            TaskGoal.FIND_CART: "cart_items",
            TaskGoal.FIND_CHECKOUT: "checkout_form",
            TaskGoal.FIND_LOGIN: "login_form",
            TaskGoal.FIND_REGISTER: "register_form",
            TaskGoal.EXTRACT_PRODUCTS: "product_list",
            TaskGoal.FIND_PRICING: "pricing_info",
            TaskGoal.FIND_FAQ: "faq_content",
            TaskGoal.FIND_RETURNS: "returns_info",
        }
        return expectations.get(goal, "page_content")
    
    def _add_goal_steps(self, plan: TaskPlan, parsed: ParsedCommand):
        """Add goal-specific steps to plan"""
        
        goal = parsed.primary_goal
        analyze_step = len(plan.steps) - 1
        
        if goal == TaskGoal.FIND_CONTACT_FORM:
            self._add_contact_form_steps(plan, parsed, analyze_step)
        
        elif goal in [TaskGoal.FIND_CART, TaskGoal.FIND_CHECKOUT]:
            self._add_cart_steps(plan, parsed, analyze_step)
        
        elif goal == TaskGoal.EXTRACT_PRODUCTS:
            self._add_extraction_steps(plan, parsed, analyze_step)
        
        elif goal == TaskGoal.FIND_PRICING:
            self._add_pricing_steps(plan, parsed, analyze_step)
        
        elif goal in [TaskGoal.FIND_LOGIN, TaskGoal.FIND_REGISTER]:
            self._add_auth_steps(plan, parsed, analyze_step)
        
        else:
            # Generic - just extract
            plan.add_step(
                StepType.EXTRACT,
                params={"type": "page_content"},
                description="Extract page content",
                depends_on=[analyze_step]
            )
    
    def _add_contact_form_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int
    ):
        """Add steps for filling contact form"""
        
        form_data = parsed.form_data
        prev_step = after_step
        
        # Check if user wants to fill the form or just find it
        has_fill_data = (
            form_data.email or 
            form_data.name or 
            form_data.message or 
            form_data.phone
        )
        
        # Check instruction for fill intent
        instr_lower = parsed.original_instruction.lower()
        has_fill_intent = any(word in instr_lower for word in [
            'wyślij', 'wyslij', 'wypełnij', 'wypelnij', 'send', 'submit', 
            'fill', 'napisz', 'wiadomość', 'wiadomosc'
        ]) and has_fill_data
        
        # If no form data and no fill intent, just extract form info
        if not has_fill_data and not has_fill_intent:
            plan.add_step(
                StepType.EXTRACT,
                params={"type": "forms"},
                description="Extract contact form info",
                depends_on=[prev_step]
            )
            plan.expected_outcome = "form_fields"  # Mark as find operation
            return
        
        # Generate name if not provided (required for most forms)
        name_value = form_data.name
        if not name_value and form_data.email:
            # Extract name from email (before @)
            email_local = form_data.email.split('@')[0]
            # Clean up: test.user -> Test User
            name_value = ' '.join(word.capitalize() for word in email_local.replace('.', ' ').replace('_', ' ').split())
        if not name_value:
            name_value = "Użytkownik"  # Default placeholder
        
        # Fill name first (usually required)
        prev_step = plan.add_step(
            StepType.FILL_FIELD,
            params={
                "field_type": "name",
                "value": name_value,
                "selectors": [
                    'input[name*="name"]',
                    'input[name*="imie"]',
                    'input[name*="nazwisko"]',
                    'input[placeholder*="imię" i]',
                    'input[placeholder*="name" i]'
                ]
            },
            description=f"Fill name: {name_value}",
            depends_on=[prev_step]
        )
        
        # Fill email
        if form_data.email:
            prev_step = plan.add_step(
                StepType.FILL_FIELD,
                params={
                    "field_type": "email",
                    "value": form_data.email,
                    "selectors": [
                        'input[type="email"]',
                        'input[name*="email"]',
                        'input[placeholder*="email" i]',
                        'input[name*="mail"]'
                    ]
                },
                description=f"Fill email: {form_data.email}",
                depends_on=[prev_step]
            )
        
        # Fill name again only if explicitly different from auto-generated
        if form_data.name and form_data.name != name_value:
            prev_step = plan.add_step(
                StepType.FILL_FIELD,
                params={
                    "field_type": "name",
                    "value": form_data.name,
                    "selectors": [
                        'input[name*="name"]',
                        'input[name*="nazwisko"]',
                        'input[placeholder*="imię" i]',
                        'input[placeholder*="name" i]'
                    ]
                },
                description=f"Fill name: {form_data.name}",
                depends_on=[prev_step]
            )
        
        # Fill phone
        if form_data.phone:
            prev_step = plan.add_step(
                StepType.FILL_FIELD,
                params={
                    "field_type": "phone",
                    "value": form_data.phone,
                    "selectors": [
                        'input[type="tel"]',
                        'input[name*="phone"]',
                        'input[name*="telefon"]'
                    ]
                },
                description=f"Fill phone: {form_data.phone}",
                depends_on=[prev_step]
            )
        
        # Fill message
        if form_data.message:
            prev_step = plan.add_step(
                StepType.FILL_FIELD,
                params={
                    "field_type": "message",
                    "value": form_data.message,
                    "selectors": [
                        'textarea',
                        'textarea[name*="message"]',
                        'textarea[name*="wiadomość"]'
                    ]
                },
                description=f"Fill message",
                depends_on=[prev_step]
            )
        
        # Try to accept consent/RODO checkbox (if present)
        prev_step = plan.add_step(
            StepType.FILL_FIELD,
            params={
                "field_type": "consent",
                "value": "true",
                "selectors": [
                    'input[type="checkbox"][name*="consent"]',
                    'input[type="checkbox"][name*="zgoda"]',
                    'input[type="checkbox"][name*="rodo"]',
                    'input[type="checkbox"][id*="consent"]',
                    'input[type="checkbox"][id*="zgoda"]',
                ]
            },
            description="Accept consent/RODO",
            depends_on=[prev_step]
        )
        
        # Submit form
        plan.add_step(
            StepType.SUBMIT,
            params={
                "selectors": [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Wyślij")',
                    'button:has-text("Send")'
                ],
                "wait_after_ms": 3000
            },
            description="Submit form",
            depends_on=[prev_step]
        )
        
        plan.expected_outcome = "form_submitted"
    
    def _add_cart_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int
    ):
        """Add steps for cart/checkout flow"""
        
        # If we have a search query, search first
        if parsed.search_query:
            plan.add_step(
                StepType.SEARCH,
                params={"query": parsed.search_query},
                description=f"Search for: {parsed.search_query}",
                depends_on=[after_step]
            )
            after_step = len(plan.steps) - 1
        
        # Extract cart contents
        plan.add_step(
            StepType.EXTRACT,
            params={"type": "cart_items"},
            description="Extract cart contents",
            depends_on=[after_step]
        )
        
        plan.expected_outcome = "cart_displayed"
    
    def _add_extraction_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int
    ):
        """Add steps for data extraction"""
        
        # Search if we have a query
        if parsed.search_query:
            plan.add_step(
                StepType.SEARCH,
                params={"query": parsed.search_query},
                description=f"Search for: {parsed.search_query}",
                depends_on=[after_step]
            )
            after_step = len(plan.steps) - 1
            
            # Wait for results
            plan.add_step(
                StepType.WAIT,
                params={"ms": 2000, "for": "products"},
                description="Wait for search results",
                depends_on=[after_step]
            )
            after_step = len(plan.steps) - 1
        
        # Extract products
        plan.add_step(
            StepType.EXTRACT,
            params={"type": "products"},
            description="Extract product data",
            depends_on=[after_step]
        )
        
        plan.expected_outcome = "products_extracted"
    
    def _add_pricing_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int
    ):
        """Add steps for pricing/price list extraction"""
        
        # Extract pricing information
        plan.add_step(
            StepType.EXTRACT,
            params={"type": "pricing"},
            description="Extract pricing data",
            depends_on=[after_step]
        )
        
        plan.expected_outcome = "pricing_extracted"
    
    def _add_auth_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int
    ):
        """Add steps for login/register"""
        
        form_data = parsed.form_data
        
        if form_data.email:
            plan.add_step(
                StepType.FILL_FIELD,
                params={
                    "field_type": "email",
                    "value": form_data.email,
                    "selectors": ['input[type="email"]', 'input[name*="email"]']
                },
                description=f"Fill email: {form_data.email}",
                depends_on=[after_step]
            )
        
        # Note: password would come from secure source, not command
        plan.expected_outcome = "auth_page_ready"


def create_plan(parsed: ParsedCommand) -> TaskPlan:
    """Convenience function for creating plans"""
    planner = TaskPlanner()
    return planner.plan(parsed)
