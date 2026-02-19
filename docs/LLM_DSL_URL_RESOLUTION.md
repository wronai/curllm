# LLM-DSL URL Resolution Architecture

**Status: 🔄 IN PROGRESS**
**Last Updated: 2025-12-08**

## Overview

This document describes the LLM-DSL architecture for dynamic URL resolution and element finding.
The system replaces hardcoded keywords with LLM-driven semantic analysis.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    LLM-DSL URL RESOLUTION                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  User Instruction: "Znajdź formularz kontaktowy"                        │
│                          │                                               │
│                          ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  1. GoalDetector (LLM-first)                                      │   │
│  │     ├── LLM semantic analysis → TaskGoal.FIND_CONTACT_FORM       │   │
│  │     └── Statistical fallback (NO hardcoded keywords)             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                          │                                               │
│                          ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  2. UrlResolver.find_url_for_goal()                               │   │
│  │     ├── _find_url_with_llm()     ← LLM semantic                  │   │
│  │     ├── dom_helpers.find_link()  ← Statistical word-overlap      │   │
│  │     └── _legacy_fallback()       ← Pattern matching (deprecated) │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                          │                                               │
│                          ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  3. LLMElementFinder / LLMSelectorGenerator                       │   │
│  │     ├── find_element(purpose="contact form")                     │   │
│  │     ├── generate_field_selector(purpose="email input")           │   │
│  │     └── generate_consent_selector()                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                          │                                               │
│                          ▼                                               │
│  Result: ResolvedUrl(url="/kontakt", method="llm", confidence=0.9)      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Goal Detection (`goal_detector_llm/`)

**BEFORE (Hardcoded):**
```python
# ❌ Hardcoded keyword lists
if 'kontakt' in instruction or 'contact' in instruction:
    return TaskGoal.FIND_CONTACT_FORM
```

**AFTER (LLM-DSL):**
```python
# ✅ LLM semantic analysis
result = await llm.aquery(f"""
Analyze this instruction and determine user's goal:
"{instruction}"

Goals: FIND_CART, FIND_LOGIN, FIND_CONTACT_FORM, FIND_RETURNS, ...
Return: {{"goal": "GOAL_NAME", "confidence": 0.0-1.0}}
""")
```

### 2. URL Resolution (`url_resolution/resolver.py`)

**Strategy Hierarchy:**
1. **LLM Analysis** - Semantic understanding of page links
2. **Statistical Analysis** - Word overlap scoring (no hardcoded keywords)
3. **Structural Analysis** - DOM patterns (nav, footer, header)
4. **Legacy Fallback** - Pattern matching (being deprecated)

### 3. Element Finding (`llm_dsl/element_finder.py`)

```python
# Find element by PURPOSE, not selector
finder = LLMElementFinder(page=page, llm=llm)
result = await finder.find_element(purpose="contact form submit button")

# Result:
# ElementMatch(
#     found=True,
#     selector="form.contact button[type='submit']",
#     confidence=0.9,
#     method="llm"
# )
```

### 4. Selector Generation (`llm_dsl/selector_generator.py`)

```python
# Generate selector dynamically
generator = LLMSelectorGenerator(llm=llm)
result = await generator.generate_field_selector(
    page=page,
    purpose="email input field"
)

# Result:
# GeneratedSelector(
#     selector="input[type='email'], input[name*='mail']",
#     confidence=0.85,
#     method="llm"
# )
```

## Single Source of Truth

**All semantic concepts are defined in ONE location:**

```
curllm_core/
├── url_types.py              # TaskGoal enum (goals only)
├── llm_dsl/
│   ├── concepts.py           # FIELD_CONCEPTS (NEW - single source)
│   ├── selector_generator.py # Uses concepts from above
│   └── element_finder.py     # Uses concepts from above
└── form_fill/
    └── js_scripts.py         # generate_field_concepts_with_llm()
```

## Migration from Hardcoded

### Keywords → LLM Analysis

| Component | Before | After |
|-----------|--------|-------|
| Goal detection | `if 'kontakt' in text` | `llm.analyze_intent(text)` |
| URL finding | `url_patterns = ['/kontakt']` | `llm.find_url_for_purpose(purpose)` |
| Selector | `'#email, .email-input'` | `generator.generate_field_selector('email')` |
| Form fields | `['email', 'mail', 'adres']` | `generate_field_concepts_with_llm(page)` |

### Statistical Fallback (NO Hardcoded Keywords)

When LLM is unavailable, use statistical analysis:

```python
async def _find_link_statistical(page, goal: str) -> Optional[LinkInfo]:
    """
    Statistical word-overlap scoring.
    NO HARDCODED KEYWORDS - derives keywords from goal description.
    """
    # Extract keywords from goal semantically
    goal_words = set(goal.replace('_', ' ').lower().split())
    
    links = await page.evaluate("() => [...document.querySelectorAll('a')]...")
    
    for link in links:
        # Score based on word overlap
        link_words = set(link.text.lower().split() + link.href.split('/'))
        score = len(goal_words & link_words) / len(goal_words)
        ...
```

## Files to Refactor

| File | Issue | Solution |
|------|-------|----------|
| `goal_detector_hybrid.py` | `GOAL_KEYWORDS` dict | Use LLM analysis, remove dict |
| `resolver.py::_extract_keywords` | `FILTER_WORDS` set | Use LLM to extract search terms |
| `_find_link_keyword_fallback.py` | `goal_config` dict | Use statistical scoring |

## Testing

```bash
# Run URL resolver examples
cd examples/url_resolver
python run_all.py

# Expected results after migration:
# - Goal detection: 90%+ (LLM semantic)
# - URL finding: 80%+ (LLM + statistical)
# - Form filling: 85%+ (LLM selectors)
```

## References

- [LLM_DSL_ARCHITECTURE.md](LLM_DSL_ARCHITECTURE.md) - Full architecture
- [LLM_DSL_QUICK_REFERENCE.md](LLM_DSL_QUICK_REFERENCE.md) - Quick reference
- [migration_plan.md](../migration_plan.md) - Migration progress
