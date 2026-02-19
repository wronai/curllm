# Migration Guide: v1 → v2

## Overview

**v2 is now the default!** CurLLM v2 uses LLM-driven implementations that replace 
hardcoded selectors, keywords, and patterns with dynamic LLM-based detection.

Use `--v1` flag only if you need legacy behavior.

## Quick Start

```python
# Before (v1 - deprecated)
from curllm_core.form_fill import deterministic_form_fill
from curllm_core.orchestrators import FormOrchestrator

# After (v2 - recommended)
from curllm_core.v2 import llm_form_fill, LLMFormOrchestrator
```

## API Changes

### Form Filling

| v1 | v2 |
|----|-----|
| `deterministic_form_fill(instruction, page)` | `await llm_form_fill(instruction, page, llm)` |
| Uses hardcoded field keywords | Uses LLM to detect fields |

```python
# v1 (deprecated)
result = await deterministic_form_fill(
    "email=test@example.com name=John",
    page
)

# v2 (recommended)
from curllm_core.v2 import llm_form_fill
result = await llm_form_fill(
    "Fill the form with email test@example.com and name John",
    page,
    llm
)
```

### Orchestrators

| v1 | v2 |
|----|-----|
| `FormOrchestrator` | `LLMFormOrchestrator` |
| `AuthOrchestrator` | `LLMAuthOrchestrator` |
| `SocialMediaOrchestrator` | `LLMSocialOrchestrator` |
| `ECommerceOrchestrator` | `LLMECommerceOrchestrator` |

```python
# v1 (deprecated)
from curllm_core.v1 import FormOrchestrator
orch = FormOrchestrator(llm=llm, page=page)
result = await orch.orchestrate(instruction)

# v2 (recommended)
from curllm_core.v2 import LLMFormOrchestrator
orch = LLMFormOrchestrator(llm=llm, page=page)
result = await orch.orchestrate(instruction)
```

### Extraction

```python
# v1 (deprecated)
from curllm_core.extraction import extractor
result = await extractor.generic_fastpath(instruction, page)

# v2 (recommended)
from curllm_core.v2 import llm_extract
result = await llm_extract(page, llm, instruction)
```

### DSL Execution

```python
# v1 (deprecated)
from curllm_core.dsl import DSLExecutor
executor = DSLExecutor(page, llm)
result = await executor.execute(instruction)

# v2 (recommended)
from curllm_core.v2 import LLMDSLExecutor
executor = LLMDSLExecutor(page=page, llm=llm)
result = await executor.execute(instruction)
```

## Core Concepts

### AtomicFunctions

v2 introduces `AtomicFunctions` - low-level LLM-driven DOM operations:

```python
from curllm_core.v2 import AtomicFunctions

atoms = AtomicFunctions(page=page, llm=llm)

# Find input by context (no hardcoded selectors!)
result = await atoms.find_input_by_context("email address field")
if result.success:
    await page.fill(result.data['selector'], "test@example.com")

# Find clickable element by intent
result = await atoms.find_clickable_by_intent("submit the form")
if result.success:
    await page.click(result.data['selector'])

# Detect message type (success/error/captcha)
result = await atoms.detect_message_type()
```

### DSL Query Generator

LLM converts natural language to DSL queries:

```python
from curllm_core.v2 import DSLQueryGenerator

generator = DSLQueryGenerator(llm=llm)
query = await generator.generate(
    "Fill the contact form with my email and submit"
)
# Returns structured DSL query
```

## Benefits of v2

1. **No hardcoded selectors** - Works on any website
2. **Language agnostic** - Understands Polish, English, etc.
3. **Adaptive** - LLM adjusts to page structure
4. **Future-proof** - No maintenance for selector updates

## Deprecation Timeline

- **Now**: v1 modules show deprecation warnings
- **Future release**: v1 modules moved to `deprecated/`
- **Later**: v1 modules removed

## Backward Compatibility

v1 is still available for existing code:

```python
# Still works, but shows deprecation warning
from curllm_core.v1 import FormOrchestrator
```

## Need Help?

- Check `tests/test_v2_imports.py` for usage examples
- See `curllm_core/v2/__init__.py` for available exports
