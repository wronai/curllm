# Hardcoded Patterns Report

This document lists files containing hardcoded selectors, keywords, or patterns
that should eventually be replaced with LLM-driven detection (v2).

## Files with Hardcoded Patterns

### url_resolution/resolver.py (HIGH)

Contains hardcoded:

- Task goal keywords: `['zaloguj', 'login', 'logowanie', 'konto']`
- CSS selectors: `'a[href*="login"]'`, `'a[href*="signin"]'`
- Navigation keywords

**v2 Alternative**: Use `DSLQueryGenerator` to detect login/navigation links dynamically.

### streamware/components/decision.py (MEDIUM)

Contains hardcoded:

- Field types: `['text', 'email', 'tel', 'textarea']`
- Form field keywords: `['name', 'email', 'phone', 'subject', 'message']`
- Submit selectors: `'button[type="submit"]'`

**v2 Alternative**: Use `AtomicFunctions.find_input_by_context()` for field detection.

### streamware/components/form/submit.py (MEDIUM)

Contains hardcoded:

- Submit button keywords: `'submit'`, `'wyślij'`, `'send'`
- Button class patterns

**v2 Alternative**: Use `AtomicFunctions.find_clickable_by_intent("submit form")`.

### streamware/components/dom_fix.py (LOW)

Contains hardcoded:

- Field name patterns: `['name', 'email', 'phone', 'subject', 'message']`

**v2 Alternative**: Use LLM to infer field purposes from context.

## Migration Strategy

1. **New code**: Use v2 API exclusively
2. **Existing code**: Keep v1 for backward compatibility
3. **Gradual migration**: Replace hardcoded patterns file-by-file
4. **Testing**: Ensure LLM-driven detection matches or exceeds v1 accuracy

## v2 Replacement Patterns

```python
# Instead of hardcoded selector:
selector = 'input[type="email"]'

# Use v2:
from curllm_core.v2 import AtomicFunctions
atoms = AtomicFunctions(page=page, llm=llm)
result = await atoms.find_input_by_context("email address field")
selector = result.data['selector']
```

```python
# Instead of hardcoded keywords:
if any(k in text for k in ['login', 'zaloguj', 'sign in']):
    ...

# Use v2:
from curllm_core.v2 import DSLQueryGenerator
gen = DSLQueryGenerator(llm=llm)
is_login = await gen.classify_intent(text, "login page detection")
```

## Status

| Module | Hardcoded | v2 Alternative | Migrated |
|--------|-----------|----------------|----------|
| url_resolution/resolver.py | Yes | GoalDetectorHybrid | ✅ |
| streamware/decision.py | Yes | decision_llm.py | ✅ |
| streamware/form/submit.py | Yes | submit_llm.py | ✅ |
| orchestrators/form.py | Yes | LLMFormOrchestrator | ✅ |
| orchestrators/auth.py | Yes | LLMAuthOrchestrator | ✅ |
| form_fill.py | Yes | form_fill_llm.py | ✅ |
| dsl/executor.py | Yes | dsl/executor_llm.py | ✅ |
