"""
Atomic Form Components for Streamware

Modular components for form detection, filling, and submission.
Each component does ONE thing well. No hardcoded selectors.

Components:
- detect.py: Find forms and fields on page
- fill.py: Fill fields using LLM-provided selectors
- submit.py: Submit form and detect success
- tools.py: Dynamic tool registry from function signatures
- orchestrator.py: Coordinate components for full form fill
"""

from .detect import detect_form, detect_forms, get_field_selectors
from .fill import fill_field, fill_fields
from .submit import (
    submit_form, 
    get_clickable_buttons,
    detect_success,
    capture_page_state,
    detect_success_data,
    evaluate_success_with_llm
)
from .orchestrator import orchestrate_form_fill, form_fill_tool, parse_instruction
from .smart_orchestrator import SmartFormOrchestrator, smart_fill_form
from .tools import (
    execute_tool,
    get_tools_prompt,
    generate_tool_registry,
    FORM_ATOMIC_TOOLS,
    TOOL_FUNCTIONS
)

__all__ = [
    # Detection
    'detect_form', 'detect_forms', 'get_field_selectors',
    # Filling
    'fill_field', 'fill_fields',
    # Submission
    'submit_form', 'get_clickable_buttons', 'detect_success',
    'capture_page_state', 'detect_success_data', 'evaluate_success_with_llm',
    # Orchestrator
    'orchestrate_form_fill', 'form_fill_tool', 'parse_instruction',
    # Smart Orchestrator (LLM-driven with verification)
    'SmartFormOrchestrator', 'smart_fill_form',
    # Tools for LLM
    'execute_tool', 'get_tools_prompt', 'generate_tool_registry',
    'FORM_ATOMIC_TOOLS', 'TOOL_FUNCTIONS'
]
