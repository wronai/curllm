"""Task planner — builds execution plans from parsed commands."""

import logging
from typing import Any, Dict, Optional

from curllm_core.command_parser import ParsedCommand
from curllm_core.url_types import TaskGoal

from .plan_types import StepType, TaskPlan

logger = logging.getLogger(__name__)


class TaskPlanner:
    """Create execution plans from parsed commands."""

    def plan(
        self,
        parsed: ParsedCommand,
        page_context: Optional[Dict[str, Any]] = None,
    ) -> TaskPlan:
        plan = TaskPlan(
            parsed_command=parsed,
            description=f"Execute: {parsed.primary_goal.value}",
        )

        if parsed.get_url():
            plan.add_step(
                StepType.NAVIGATE,
                params={"url": parsed.get_url()},
                description=f"Navigate to {parsed.target_domain}",
            )

        if parsed.primary_goal != TaskGoal.GENERIC:
            nav_step = len(plan.steps) - 1 if plan.steps else -1
            plan.add_step(
                StepType.RESOLVE,
                params={"goal": parsed.primary_goal.value},
                description=f"Find {parsed.primary_goal.value}",
                depends_on=[nav_step] if nav_step >= 0 else [],
            )

        resolve_step = len(plan.steps) - 1
        plan.add_step(
            StepType.ANALYZE,
            params={"expected": self._expected_for_goal(parsed.primary_goal)},
            description="Analyze page structure",
            depends_on=[resolve_step],
        )

        self._add_goal_steps(plan, parsed)

        plan.add_step(
            StepType.VERIFY,
            params={"expected": plan.expected_outcome},
            description="Verify outcome",
            optional=True,
        )
        plan.add_step(
            StepType.SCREENSHOT,
            params={"name": "final_state"},
            description="Capture final state",
            optional=True,
        )

        logger.info("Created plan with %s steps", len(plan.steps))
        return plan

    def _expected_for_goal(self, goal: TaskGoal) -> str:
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

    def _add_goal_steps(self, plan: TaskPlan, parsed: ParsedCommand) -> None:
        goal = parsed.primary_goal
        analyze_step = len(plan.steps) - 1

        if goal == TaskGoal.FIND_CONTACT_FORM:
            self._add_contact_form_steps(plan, parsed, analyze_step)
        elif goal in (TaskGoal.FIND_CART, TaskGoal.FIND_CHECKOUT):
            self._add_cart_steps(plan, parsed, analyze_step)
        elif goal == TaskGoal.EXTRACT_PRODUCTS:
            self._add_extraction_steps(plan, parsed, analyze_step)
        elif goal == TaskGoal.FIND_PRICING:
            self._add_pricing_steps(plan, parsed, analyze_step)
        elif goal in (TaskGoal.FIND_LOGIN, TaskGoal.FIND_REGISTER):
            self._add_auth_steps(plan, parsed, analyze_step)
        else:
            plan.add_step(
                StepType.EXTRACT,
                params={"type": "page_content"},
                description="Extract page content",
                depends_on=[analyze_step],
            )

    def _add_contact_form_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int,
    ) -> None:
        form_data = parsed.form_data
        prev_step = after_step

        has_fill_data = bool(
            form_data.email or form_data.name or form_data.message or form_data.phone
        )
        instr_lower = parsed.original_instruction.lower()
        has_fill_intent = any(
            word in instr_lower
            for word in (
                "wyślij",
                "wyslij",
                "wypełnij",
                "wypelnij",
                "send",
                "submit",
                "fill",
                "napisz",
                "wiadomość",
                "wiadomosc",
            )
        ) and has_fill_data

        if not has_fill_data and not has_fill_intent:
            plan.add_step(
                StepType.EXTRACT,
                params={"type": "forms"},
                description="Extract contact form info",
                depends_on=[prev_step],
            )
            plan.expected_outcome = "form_fields"
            return

        name_value = form_data.name
        if not name_value and form_data.email:
            email_local = form_data.email.split("@")[0]
            name_value = " ".join(
                word.capitalize()
                for word in email_local.replace(".", " ").replace("_", " ").split()
            )
        if not name_value:
            name_value = "Użytkownik"

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
                    'input[placeholder*="name" i]',
                ],
            },
            description=f"Fill name: {name_value}",
            depends_on=[prev_step],
        )

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
                        'input[name*="mail"]',
                    ],
                },
                description=f"Fill email: {form_data.email}",
                depends_on=[prev_step],
            )

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
                        'input[placeholder*="name" i]',
                    ],
                },
                description=f"Fill name: {form_data.name}",
                depends_on=[prev_step],
            )

        if form_data.phone:
            prev_step = plan.add_step(
                StepType.FILL_FIELD,
                params={
                    "field_type": "phone",
                    "value": form_data.phone,
                    "selectors": [
                        'input[type="tel"]',
                        'input[name*="phone"]',
                        'input[name*="telefon"]',
                    ],
                },
                description=f"Fill phone: {form_data.phone}",
                depends_on=[prev_step],
            )

        if form_data.message:
            prev_step = plan.add_step(
                StepType.FILL_FIELD,
                params={
                    "field_type": "message",
                    "value": form_data.message,
                    "selectors": [
                        "textarea",
                        'textarea[name*="message"]',
                        'textarea[name*="wiadomość"]',
                    ],
                },
                description="Fill message",
                depends_on=[prev_step],
            )

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
                ],
            },
            description="Accept consent/RODO",
            depends_on=[prev_step],
        )

        plan.add_step(
            StepType.SUBMIT,
            params={
                "selectors": [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Wyślij")',
                    'button:has-text("Send")',
                ],
                "wait_after_ms": 3000,
            },
            description="Submit form",
            depends_on=[prev_step],
        )
        plan.expected_outcome = "form_submitted"

    def _add_cart_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int,
    ) -> None:
        if parsed.search_query:
            plan.add_step(
                StepType.SEARCH,
                params={"query": parsed.search_query},
                description=f"Search for: {parsed.search_query}",
                depends_on=[after_step],
            )
            after_step = len(plan.steps) - 1

        plan.add_step(
            StepType.EXTRACT,
            params={"type": "cart_items"},
            description="Extract cart contents",
            depends_on=[after_step],
        )
        plan.expected_outcome = "cart_displayed"

    def _add_extraction_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int,
    ) -> None:
        if parsed.search_query:
            plan.add_step(
                StepType.SEARCH,
                params={"query": parsed.search_query},
                description=f"Search for: {parsed.search_query}",
                depends_on=[after_step],
            )
            after_step = len(plan.steps) - 1
            plan.add_step(
                StepType.WAIT,
                params={"ms": 2000, "for": "products"},
                description="Wait for search results",
                depends_on=[after_step],
            )
            after_step = len(plan.steps) - 1

        plan.add_step(
            StepType.EXTRACT,
            params={"type": "products"},
            description="Extract product data",
            depends_on=[after_step],
        )
        plan.expected_outcome = "products_extracted"

    def _add_pricing_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int,
    ) -> None:
        plan.add_step(
            StepType.EXTRACT,
            params={"type": "pricing"},
            description="Extract pricing data",
            depends_on=[after_step],
        )
        plan.expected_outcome = "pricing_extracted"

    def _add_auth_steps(
        self,
        plan: TaskPlan,
        parsed: ParsedCommand,
        after_step: int,
    ) -> None:
        form_data = parsed.form_data
        if form_data.email:
            plan.add_step(
                StepType.FILL_FIELD,
                params={
                    "field_type": "email",
                    "value": form_data.email,
                    "selectors": ['input[type="email"]', 'input[name*="email"]'],
                },
                description=f"Fill email: {form_data.email}",
                depends_on=[after_step],
            )
        plan.expected_outcome = "auth_page_ready"
