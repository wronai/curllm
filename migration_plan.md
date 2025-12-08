
# LLM-DSL Migration Plan

**Last Updated: 2025-12-08**
**Status: Phase 1 In Progress**

## Overview
This plan outlines the migration from hardcoded selectors/keywords to LLM-DSL architecture.

## Architecture Changes

### Before (Hardcoded)
```python
# Hardcoded selector
element = document.querySelector('input[name="email"]')

# Hardcoded keyword list
for field in ["name", "email", "phone"]:
    # ...
```

### After (LLM-DSL)
```python
# LLM-driven element finding
element = await dsl.execute("find_element", {
    "purpose": "email_input",
    "context": page_context
})

# LLM-driven field detection
fields = await dsl.execute("analyze_form", {
    "form_context": form_html,
    "detect_purposes": True
})
for field in fields.data:
    # ...
```

## Progress Tracking

| File | Status | Changes |
|------|--------|---------|
| `curllm_core/dsl/executor.py` | ✅ Refactored | `_parse_instruction()` → semantic concept detection |
| `curllm_core/extraction/extractor.py` | ✅ Refactored | `_filter_only()` uses concept groups |
| `curllm_core/iterative_extractor.py` | ⏳ No Changes | Already uses statistical/dynamic detection |
| `curllm_core/form_fill.py` | ✅ Refactored | `field_concepts` dict for semantic matching |
| `curllm_core/form_fill/js_scripts.py` | ✅ Refactored | Added `FIELD_CONCEPTS` constant |
| `curllm_core/hierarchical/planner.py` | ✅ Refactored | `field_concepts` dict for canonical names |
| `curllm_core/field_filling/filler.py` | ✅ Refactored | `consentConcepts` for GDPR detection |
| `curllm_core/dom/helpers.py` | ✅ Refactored | LLM-first link finding strategy |
| `curllm_core/llm_dsl/element_finder.py` | ✅ Created | New LLM-driven element finder |
| `scripts/refactor_to_llm_dsl.py` | ✅ Created | Migration analysis script |

## Files to Migrate (Priority Order)


### 1. `curllm_core/dsl/executor.py` ✅ DONE
- Score: 174
- Hardcoded values: 22
- Changes made:
  - ✅ Line 216: Now uses `_get_default_fields()` instead of hardcoded list
  - ✅ Line 353: Now uses `_get_default_fields()` instead of hardcoded list
  - ✅ Added `_detect_fields_semantic()` for concept-based detection
  - ✅ Added `_detect_filter_semantic()` for filter expression parsing
  - ⏳ Lines 583-590: Table selectors (kept for now - semantic for purpose)

### 2. `curllm_core/extraction/extractor.py` ✅ DONE
- Score: 117
- Hardcoded values: 15
- Changes made:
  - ✅ Lines 168-173: `_filter_only()` now uses semantic concept groups
  - ✅ Lines 191-198: `direct_fastpath()` now uses semantic concept groups
  - ⏳ Lines 25, 83: `'a'` selector kept (semantic - finds anchors)
  - ⏳ Lines 103, 105: `'a[href]'` selector kept (semantic - finds links)

### 3. `curllm_core/iterative_extractor.py` ⏳ NO CHANGES NEEDED
- Score: 104
- Hardcoded values: 13
- Analysis:
  - ✅ Already uses dynamic/statistical detection
  - ⏳ `*` selector is used for statistical DOM analysis (not hardcoded targeting)
  - ⏳ `a[href]`, `img` are semantic element type selectors (correct for purpose)

### 4. `curllm_core/form_fill.py` ✅ DONE
- Score: 92
- Hardcoded values: 12
- Changes made:
  - ✅ Lines 83-86: Dynamic field iteration from canonical dict
  - ✅ Lines 91-110: `field_concepts` dict for semantic matching
  - ⏳ Lines 146, 153, 174: Form/input selectors kept (semantic for purpose)

### 5. `curllm_core/form_fill/js_scripts.py` ✅ DONE
- Score: 70
- Hardcoded values: 9
- Changes made:
  - ✅ Added `FIELD_CONCEPTS` constant for semantic mapping
  - ✅ Documented that keyword lists are semantic concepts
  - ⏳ `label`, `input,textarea`, `form` selectors kept (semantic for purpose)

### 6. `curllm_core/hierarchical/planner.py` ✅ DONE
- Score: 56
- Hardcoded values: 8
- Changes made:
  - ✅ Lines 316-323: `field_concepts` dict for semantic field detection
  - ✅ Lines 447-454: `field_concepts` dict for canonical name mapping

### 7. `curllm_core/field_filling/filler.py` ✅ DONE
- Score: 45
- Hardcoded values: 6
- Changes made:
  - ✅ Lines 402-410: `consentConcepts` for GDPR/consent detection
  - ⏳ Lines 346, 506: Error/success selectors kept (CSS class patterns for form libraries)

### 8. `curllm_core/dom/helpers.py` ✅ DONE
- Score: 39
- Hardcoded values: 5
- Changes made:
  - ✅ `find_link_for_goal()` now uses LLM-first strategy
  - ✅ Added `_find_link_with_llm()` for LLM-based link finding
  - ✅ Added `_find_link_statistical()` for word-overlap scoring
  - ✅ `_find_link_keyword_fallback()` preserved as legacy fallback
  - ⏳ `a[href]`, `input`, `form` selectors kept (semantic for purpose)

### 9. `curllm_core/streamware/components/form/smart_orchestrator.py`
- Score: 38
- Hardcoded values: 5
- Key changes needed:
  - Line 121: Hardcoded selector: form
  - Line 124: Hardcoded selector: input, textarea, select
  - Line 333: Hardcoded keyword list - should use LLM to detect field purposes
  - Line 337: Hardcoded keyword list - should use LLM to detect field purposes
  - Line 401: Hardcoded selector: {selector}

### 10. `curllm_core/streamware/components/dom_fix.py`
- Score: 38
- Hardcoded values: 5
- Key changes needed:
  - Line 73: Hardcoded selector: form
  - Line 75: Hardcoded selector: input, textarea, select
  - Line 123: Hardcoded selector: a[href]
  - Line 421: Hardcoded keyword list - should use LLM to detect field purposes
  - Line 423: Hardcoded keyword list - should use LLM to detect field purposes

### 11. `curllm_core/element_finder/finder.py`
- Score: 32
- Hardcoded values: 4
- Key changes needed:
  - Line 78: Hardcoded selector: input, textarea, select
  - Line 107: Hardcoded selector: a[href]
  - Line 117: Hardcoded selector: form
  - Line 122: Hardcoded selector: input, textarea

### 12. `curllm_core/streamware/components/form/orchestrator.py`
- Score: 31
- Hardcoded values: 4
- Key changes needed:
  - Line 248: Hardcoded keyword list - should use LLM to detect field purposes
  - Line 356: Hardcoded selector: {form_selector}
  - Line 509: Hardcoded selector: form
  - Line 607: Hardcoded selector: {form_selector}

### 13. `curllm_core/orchestrators/form.py`
- Score: 31
- Hardcoded values: 4
- Key changes needed:
  - Line 123: Hardcoded keyword list - should use LLM to detect field purposes
  - Line 147: Hardcoded selector: form
  - Line 150: Hardcoded selector: input, textarea, select
  - Line 172: Hardcoded selector: input, textarea, select

### 14. `curllm_core/vision_form_analysis.py`
- Score: 28
- Hardcoded values: 4
- Key changes needed:
  - Line 304: Hardcoded keyword list - should use LLM to detect field purposes
  - Line 306: Hardcoded keyword list - should use LLM to detect field purposes
  - Line 308: Hardcoded keyword list - should use LLM to detect field purposes
  - Line 312: Hardcoded keyword list - should use LLM to detect field purposes

### 15. `curllm_core/orchestrators/ecommerce.py`
- Score: 24
- Hardcoded values: 3
- Key changes needed:
  - Line 348: Hardcoded selector: h2, h3, .name, .title
  - Line 350: Hardcoded selector: a
  - Line 368: Hardcoded selector: .name, .title, h3, h4

### 16. `curllm_core/orchestrators/social.py`
- Score: 16
- Hardcoded values: 2
- Key changes needed:
  - Line 520: Hardcoded selector: .g-recaptcha, [data-sitekey]
  - Line 521: Hardcoded selector: .h-captcha, [data-hcaptcha-sitekey]

### 17. `curllm_core/form_fill/filler.py`
- Score: 14
- Hardcoded values: 2
- Key changes needed:
  - Line 93: Hardcoded keyword list - should use LLM to detect field purposes
  - Line 112: Hardcoded keyword list - should use LLM to detect field purposes

### 18. `curllm_core/orchestrators/auth.py`
- Score: 8
- Hardcoded values: 1
- Key changes needed:
  - Line 495: Hardcoded selector: .slider-captcha, .slide-verify

### 19. `curllm_core/streamware/components/captcha/solve.py`
- Score: 8
- Hardcoded values: 1
- Key changes needed:
  - Line 152: Hardcoded selector: #g-recaptcha-response

### 20. `curllm_core/dynamic/selectors.py`
- Score: 7
- Hardcoded values: 1
- Key changes needed:
  - Line 48: Hardcoded keyword list - should use LLM to detect field purposes

## Migration Steps

1. **Phase 1: Core Modules** (atoms.py, executor.py)
   - Ensure all atomic functions are LLM-queryable
   - Add fallback strategies for each function

2. **Phase 2: Form Handling** (form_fill.py, field_filler.py)
   - Replace hardcoded field keywords with LLM detection
   - Use semantic analysis for form understanding

3. **Phase 3: URL Resolution** (url_resolver.py, dom_helpers.py)
   - Replace hardcoded URL patterns with LLM analysis
   - Use page structure analysis for navigation

4. **Phase 4: Orchestrators** (orchestrator.py, steps.py)
   - Integrate LLM-DSL for all element interactions
   - Add context-aware fallbacks

## Testing

After each phase:
1. Run `make test` to verify no regressions
2. Run example scripts to verify functionality
3. Compare success rates before/after
