"""
Hierarchical Planning module - Multi-level task planning

Functions for hierarchical planning with strategic
and tactical decision layers.
"""

from curllm_core.hierarchical.planner import (
    should_use_hierarchical,
    is_simple_form_task,
    requires_multi_step,
    estimate_context_size,
    extract_strategic_context,
    extract_requested_details,
    extract_tactical_form_context,
    should_use_hierarchical_planner,
    generate_strategic_prompt,
    generate_tactical_prompt,
    hierarchical_plan_with_vision,
    hierarchical_plan,
)

__all__ = [
    'should_use_hierarchical',
    'is_simple_form_task',
    'requires_multi_step',
    'estimate_context_size',
    'should_use_hierarchical_planner',
    'hierarchical_plan_with_vision',
    'hierarchical_plan',
]
