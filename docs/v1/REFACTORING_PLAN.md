# Refactoring Plan: Form Fill System

## Status: ✅ Phase 1 Complete

## Problem

`form_fill.py` was 983 lines of monolithic code mixing:
- DOM detection
- Field mapping
- Field filling
- Validation
- Submission
- Error handling

## Solution: Atomic Streamware Components

### New Architecture

```
curllm_core/streamware/components/form/
├── __init__.py         # Exports
├── detect.py           # Form/field detection (~100 lines)
├── map_fields.py       # User data → field mapping (~120 lines)
├── fill_field.py       # Single field filling (~130 lines)
├── validate.py         # Form validation (~130 lines)
├── submit.py           # Form submission (~100 lines)
└── orchestrator.py     # Coordinates all components (~170 lines)
```

**Total: ~750 lines** (vs 983 original), **6 focused modules** (vs 1 monolith)

### Benefits

1. **Atomic Functions**: Each does ONE thing
2. **Testable**: Components can be tested independently
3. **Reusable**: LLM can call individual components
4. **Traceable**: Clear step-by-step logging
5. **Debuggable**: Easy to find issues

### Component API

```python
# Detection
form_info = await detect_form(page)
fields = await detect_fields(page, form_id)

# Mapping
user_data = parse_instruction("Fill form: email=john@example.com")
mappings = map_user_data_to_fields(user_data, fields)

# Filling
result = await fill_field(page, selector, value)

# Validation
validation = await validate_form(page)
required = await check_required_fields(page, form_id)

# Submission
submit_result = await submit_form(page, form_id)
success = await detect_success(page)

# Or use orchestrator for full flow
result = await orchestrate_form_fill(page, instruction, logger)
```

## Phase 2: Integration (TODO)

1. **Update task_runner.py** to use new orchestrator
2. **Update form.fill tool** to use `form_fill_tool()`
3. **Deprecate old form_fill.py** (keep as backup)
4. **Add DSL prompt format** for simpler models

## Phase 3: LLM Decision Paths (TODO)

1. **Extract decision patterns** from successful runs
2. **Create decision tree** from patterns
3. **Allow LLM to choose atomic actions** instead of full orchestration
4. **Log decision paths** for analysis

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Lines of code | 983 | ~750 |
| Functions | 3 large | 15 small |
| Max function length | 800+ lines | ~50 lines |
| Testability | Low | High |
| Reusability | None | Full |

## Usage Example

```python
from curllm_core.streamware.components.form import (
    orchestrate_form_fill,
    form_fill_tool
)

# Full orchestration
result = await orchestrate_form_fill(
    page, 
    "Fill form: email=john@example.com, message=Hello",
    run_logger
)

# Tool interface for LLM
result = await form_fill_tool(
    page,
    {"email": "john@example.com", "message": "Hello"},
    run_logger
)
```
