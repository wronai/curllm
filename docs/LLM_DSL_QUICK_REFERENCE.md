# LLM-DSL Quick Reference

## Import

```python
from curllm_core.llm_dsl import (
    LLMSelectorGenerator,
    LLMElementFinder,
    GeneratedSelector,
    ElementMatch,
    generate_selector
)
from curllm_core.form_fill.js_scripts import (
    generate_field_concepts_with_llm,
    find_form_fields_with_llm
)
```

## 1. Generate CSS Selector

```python
generator = LLMSelectorGenerator(llm=my_llm)

# Consent checkbox
result = await generator.generate_consent_selector(page)

# Any field by purpose
result = await generator.generate_field_selector(page, "email input")

# Check result
if result.confidence > 0.5:
    await page.click(result.selector)
```

## 2. Find Element by Purpose

```python
finder = LLMElementFinder(llm=my_llm, page=page)

result = await finder.find_element("login button")

if result:
    await page.click(result.selector)
```

## 3. Find Form Fields

```python
selectors = await find_form_fields_with_llm(page, llm=my_llm)

# Returns: {'email': '[data-curllm-target="email"]', ...}

await page.fill(selectors['email'], "test@example.com")
await page.fill(selectors['message'], "Hello")
await page.click(selectors['submit'])
```

## 4. Generate Field Keywords

```python
concepts = await generate_field_concepts_with_llm(page, llm=my_llm)

# Returns: {'email': ['email', 'e-mail'], 'phone': ['telefon', 'tel'], ...}
```

## 5. URL Resolution

```python
from curllm_core.url_resolution import UrlResolver
from curllm_core.url_resolution.goals import TaskGoal

resolver = UrlResolver(page=page, llm=my_llm)
result = await resolver.find_url_for_goal(TaskGoal.FIND_CONTACT_FORM)

if result.url:
    await page.goto(result.url)
```

## Result Types

```python
@dataclass
class GeneratedSelector:
    selector: str       # CSS selector
    purpose: str        # What element does
    confidence: float   # 0.0 - 1.0
    method: str         # 'llm', 'statistical', 'fallback'
    reasoning: str      # Why this selector

@dataclass
class ElementMatch:
    selector: str
    confidence: float
    reasoning: str
    element_type: str   # input, button, link, etc.
    attributes: Dict[str, str]
```

## Semantic Concept Pattern

```python
# ❌ Don't do this
if data_key in ['phone', 'tel']:
    ...

# ✅ Do this
phone_concepts = {'phone', 'tel', 'telefon', 'mobile', 'komórka'}
if data_key in phone_concepts:
    ...
```

## Common Concept Groups

```python
email_concepts = {'email', 'mail', 'e-mail', 'correo', 'poczta'}
phone_concepts = {'phone', 'tel', 'telefon', 'mobile', 'komórka'}
name_concepts = {'name', 'imię', 'nazwisko', 'fullname', 'nombre'}
message_concepts = {'message', 'wiadomość', 'treść', 'content'}
```

## What's Allowed

| Type | Example | OK? |
|------|---------|-----|
| Element type | `input[type="email"]` | ✅ |
| Semantic concept | `{'email', 'mail'}` | ✅ |
| Service pattern | `.g-recaptcha` | ✅ |
| Site-specific | `#my-site-login` | ❌ |
| if/elif chain | `if 'email' in x:` | ⚠️ Convert |
