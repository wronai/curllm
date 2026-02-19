# LLM-DSL Architecture Documentation

## Overview

Curllm uses an **LLM-driven Domain Specific Language (DSL)** architecture for dynamic element detection and URL resolution. This eliminates hardcoded selectors, keywords, and URL patterns in favor of intelligent, context-aware analysis.

## Core Principle

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRZED → PO                                    │
├─────────────────────────────────────────────────────────────────┤
│ PRZED: if data_key in ['phone', 'tel']:                         │
│ PO:    if data_key in phone_concepts:                           │
│                                                                  │
│ PRZED: PLATFORM_SELECTORS = {'email': '#email'}                 │
│ PO:    ELEMENT_PURPOSES = {'email': 'email input field'}        │
│        + _find_auth_element() with LLM                          │
│                                                                  │
│ PRZED: findField(['email', 'mail'], ...)  // hardcoded JS       │
│ PO:    concepts = await generate_field_concepts_with_llm(page)  │
│        result = await page.evaluate(PARAMETRIZED_JS, concepts)  │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture Components

```
curllm_core/llm_dsl/
├── selector_generator.py   # LLMSelectorGenerator - dynamiczne selektory CSS
├── element_finder.py       # LLMElementFinder - znajdowanie elementów po PURPOSE
├── atoms.py                # AtomicFunctions - małe, wyspecjalizowane funkcje
├── executor.py             # DSLExecutor - wykonawca zapytań DSL
└── generator.py            # DSLQueryGenerator - generator zapytań DSL

curllm_core/form_fill/js_scripts.py
├── generate_field_concepts_with_llm()  # LLM generuje keywords dla pól
├── find_form_fields_with_llm()         # Główny entry point dla formularzy
└── FIND_FORM_FIELDS_PARAMETRIZED_JS    # Sparametryzowany skrypt JS
```

## Three-Tier Detection Strategy

```
┌─────────────────────────────────────────────────────────┐
│              LLM-DSL Detection Strategy                  │
├─────────────────────────────────────────────────────────┤
│  1. LLM Analysis (highest priority)                      │
│     - Analizuje wszystkie linki/elementy na stronie      │
│     - Wybiera najlepszy na podstawie semantyki           │
│     - Generuje CSS selektory dynamicznie                 │
│                                                          │
│  2. Statistical Analysis (fallback)                      │
│     - Word overlap scoring                               │
│     - Location-based scoring                             │
│     - Confidence calculation                             │
│                                                          │
│  3. Semantic Concept Groups (legacy fallback)            │
│     - Zachowane dla kompatybilności                      │
│     - Używane gdy LLM niedostępny                        │
└─────────────────────────────────────────────────────────┘
```

---

## 1. LLMSelectorGenerator

Dynamiczne generowanie CSS selektorów przez LLM.

### Lokalizacja
`curllm_core/llm_dsl/selector_generator.py`

### Klasa główna

```python
from curllm_core.llm_dsl import LLMSelectorGenerator, GeneratedSelector

class LLMSelectorGenerator:
    """
    Generates CSS selectors dynamically using LLM analysis.
    NO HARDCODED KEYWORD LISTS.
    """
    
    async def generate_field_selector(
        self, page, purpose: str, form_context: Optional[str] = None
    ) -> GeneratedSelector:
        """Generate CSS selector for a form field based on PURPOSE."""
        
    async def generate_consent_selector(self, page) -> GeneratedSelector:
        """Generate selector for consent/GDPR checkbox using LLM."""
        
    async def generate_success_indicator_selector(self, page) -> GeneratedSelector:
        """Generate selector for form success indicators."""
        
    async def generate_error_indicator_selector(
        self, page, field_selector: str
    ) -> GeneratedSelector:
        """Generate selector for field error messages."""
```

### Przykład użycia

```python
from curllm_core.llm_dsl import LLMSelectorGenerator

# Inicjalizacja z LLM
generator = LLMSelectorGenerator(llm=my_llm)

# Znajdź checkbox do zgody RODO
result = await generator.generate_consent_selector(page)

print(result.selector)     # "[data-llm-consent='true']"
print(result.confidence)   # 0.9
print(result.method)       # 'llm'
print(result.reasoning)    # "Found checkbox with label containing 'RODO'"
```

### Dataclass wyniku

```python
@dataclass
class GeneratedSelector:
    selector: str           # CSS selector
    purpose: str            # Co element robi
    confidence: float       # 0.0 - 1.0
    method: str             # 'llm', 'statistical', 'fallback'
    reasoning: str = ""     # Uzasadnienie wyboru
```

---

## 2. LLMElementFinder

Znajdowanie elementów na stronie na podstawie ich PURPOSE (nie selektora).

### Lokalizacja
`curllm_core/llm_dsl/element_finder.py`

### Klasa główna

```python
from curllm_core.llm_dsl import LLMElementFinder, ElementMatch

class LLMElementFinder:
    """
    Find elements on page based on PURPOSE, not hardcoded selectors.
    
    Instead of:
        'input[type="email"]', 'input[name*="email"]'
    
    We ask LLM:
        "Find the email input field on this page"
    """
    
    async def find_element(
        self, purpose: str, context: Optional[str] = None
    ) -> Optional[ElementMatch]:
        """Find element matching the given purpose."""
        
    async def find_all_elements(
        self, purpose: str
    ) -> List[ElementMatch]:
        """Find all elements matching purpose."""
```

### Przykład użycia

```python
from curllm_core.llm_dsl import LLMElementFinder

finder = LLMElementFinder(llm=my_llm, page=page)

# Znajdź pole email na dowolnej stronie
result = await finder.find_element(purpose="email input field")

if result and result.confidence > 0.7:
    await page.fill(result.selector, "test@example.com")
```

---

## 3. Dynamic Field Concepts Generation

LLM analizuje formularz i generuje odpowiednie keywords dla każdego typu pola.

### Lokalizacja
`curllm_core/form_fill/js_scripts.py`

### Funkcje

```python
async def generate_field_concepts_with_llm(page, llm=None) -> Dict[str, List[str]]:
    """
    Generate field concepts dynamically using LLM analysis.
    
    LLM analyzes the actual form on the page and generates
    appropriate keywords for each field type.
    
    Returns:
        Dict mapping field purpose to keywords that LLM detected
        Example: {
            "name": ["imię", "nazwisko", "full name"],
            "email": ["email", "e-mail", "adres"],
            "message": ["wiadomość", "treść", "komentarz"]
        }
    """

async def find_form_fields_with_llm(page, llm=None) -> Dict[str, str]:
    """
    Find form fields using LLM-generated concepts.
    
    Returns:
        Dict with field selectors:
        {
            "email": "[data-curllm-target='email']",
            "name": "[data-curllm-target='name']",
            "message": "[data-curllm-target='message']",
            "submit": "[data-curllm-target='submit']"
        }
    """
```

### Przykład użycia

```python
from curllm_core.form_fill.js_scripts import find_form_fields_with_llm

# LLM analizuje formularz i generuje selektory
selectors = await find_form_fields_with_llm(page, llm=my_llm)

# Wypełnij formularz
if selectors.get('email'):
    await page.fill(selectors['email'], "jan@example.pl")
if selectors.get('message'):
    await page.fill(selectors['message'], "Wiadomość testowa")
if selectors.get('submit'):
    await page.click(selectors['submit'])
```

---

## 4. URL Resolution with LLM

Dynamiczne znajdowanie URL do podstron na podstawie celu.

### Lokalizacja
`curllm_core/url_resolution/resolver.py`
`curllm_core/dom/helpers.py`

### Flow

```
User: "Znajdź formularz kontaktowy"
              ↓
┌─────────────────────────────────────────────────────────┐
│  1. _find_link_with_llm()                                │
│     - Pobiera wszystkie linki ze strony                  │
│     - Wysyła do LLM z promptem                           │
│     - LLM wybiera najlepszy link semantycznie            │
├─────────────────────────────────────────────────────────┤
│  2. _find_link_statistical()                             │
│     - Word overlap scoring                               │
│     - URL pattern matching                               │
│     - Location-based bonuses                             │
├─────────────────────────────────────────────────────────┤
│  3. _find_link_keyword_fallback()                        │
│     - Legacy keyword matching                            │
│     - Zachowane dla kompatybilności                      │
└─────────────────────────────────────────────────────────┘
              ↓
Result: "https://example.pl/kontakt"
```

### Przykład użycia

```python
from curllm_core.url_resolution import UrlResolver
from curllm_core.url_resolution.goals import TaskGoal

resolver = UrlResolver(page=page, llm=my_llm)

# Znajdź stronę kontaktową
result = await resolver.find_url_for_goal(TaskGoal.FIND_CONTACT_FORM)

if result.url:
    await page.goto(result.url)
```

---

## 5. Semantic Concept Groups (Fallback)

Gdy LLM niedostępny, używamy semantic concept groups zamiast hardcoded if/elif.

### Wzorzec

```python
# ❌ PRZED (hardcoded)
if data_key in ['phone', 'tel', 'telephone']:
    field_type = 'phone'
elif data_key in ['email', 'mail']:
    field_type = 'email'

# ✅ PO (semantic concepts)
phone_concepts = {'phone', 'tel', 'telephone', 'mobile', 'telefon', 'komórka'}
email_concepts = {'email', 'mail', 'e-mail', 'correo', 'poczta'}

if data_key in phone_concepts:
    field_type = 'phone'
elif data_key in email_concepts:
    field_type = 'email'
```

### Pełna lista semantic concept groups

```python
SEMANTIC_CONCEPTS = {
    "name": ['name', 'fullname', 'full name', 'imi', 'imię', 'nazw', 'nombre'],
    "email": ['email', 'e-mail', 'mail', 'adres', 'correo', 'poczta'],
    "phone": ['phone', 'telefon', 'tel', 'mobile', 'komórka', 'celular'],
    "message": ['message', 'wiadomo', 'treść', 'tresc', 'content', 'komentarz'],
    "subject": ['subject', 'temat', 'asunto', 'topic', 'title'],
    "address": ['address', 'addr', 'street', 'ulica', 'adres'],
    "city": ['city', 'miasto', 'town'],
    "country": ['country', 'kraj', 'nation', 'państwo'],
    "company": ['company', 'firma', 'organization', 'org'],
}
```

---

## 6. Integration Example

Kompletny przykład użycia LLM-DSL do wypełnienia formularza:

```python
import asyncio
from playwright.async_api import async_playwright
from curllm_core.llm_dsl import LLMSelectorGenerator
from curllm_core.form_fill.js_scripts import find_form_fields_with_llm
from curllm_core.llm import create_llm

async def fill_contact_form(url: str, data: dict):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        
        # Initialize LLM
        llm = create_llm()
        
        # 1. Find form fields using LLM
        selectors = await find_form_fields_with_llm(page, llm=llm)
        
        # 2. Fill fields
        for field, value in data.items():
            if field in selectors and selectors[field]:
                await page.fill(selectors[field], value)
        
        # 3. Find and check consent checkbox
        generator = LLMSelectorGenerator(llm=llm)
        consent = await generator.generate_consent_selector(page)
        if consent.confidence > 0.5:
            await page.check(consent.selector)
        
        # 4. Submit
        if selectors.get('submit'):
            await page.click(selectors['submit'])
        
        # 5. Check for success
        success = await generator.generate_success_indicator_selector(page)
        return success.confidence > 0.5

# Usage
asyncio.run(fill_contact_form(
    "https://example.pl/kontakt",
    {"name": "Jan Kowalski", "email": "jan@example.pl", "message": "Test"}
))
```

---

## 7. Migration Status

| Component | Status | Description |
|-----------|--------|-------------|
| `LLMSelectorGenerator` | ✅ Complete | Dynamic CSS selector generation |
| `LLMElementFinder` | ✅ Complete | Purpose-based element finding |
| `generate_field_concepts_with_llm` | ✅ Complete | LLM generates field keywords |
| `find_form_fields_with_llm` | ✅ Complete | Main entry point for forms |
| URL Resolution | ✅ Complete | LLM-first link finding |
| Orchestrators | ✅ Complete | LLM element detection |
| Legacy Fallbacks | ✅ Preserved | Semantic concept groups |

---

## 8. Testing

```bash
# Run all tests
make test

# Expected result
335 passed, 1 skipped, 20 warnings
```

---

## 9. What IS and ISN'T a Hardcoded Value

### ❌ Hardcoded (BAD)

```python
# Site-specific CSS selector
element = page.querySelector('#login-form-email-field')

# Hardcoded if/elif chain
if 'email' in field_name:
    do_email()
elif 'phone' in field_name:
    do_phone()
```

### ✅ Semantic Concepts (GOOD)

```python
# Semantic element type (finds ANY email input)
element = page.querySelector('input[type="email"]')

# Semantic concept groups
email_concepts = {'email', 'mail', 'e-mail', 'correo'}
if any(c in field_name for c in email_concepts):
    do_email()

# Task-to-fields mapping (expected OUTPUT, not DOM selector)
task_field_map = {
    'product': ['name', 'price', 'url'],
    'contact': ['name', 'email', 'phone'],
}
```

### ✅ CAPTCHA Service Patterns (ACCEPTABLE)

```python
# Standard CAPTCHA service class patterns
# These are defined by the service, not site-specific
'.g-recaptcha'        # Google reCAPTCHA
'.h-captcha'          # hCaptcha
'[data-sitekey]'      # Generic sitekey attribute
```

### Rule of Thumb

| Type | Description | Action |
|------|-------------|--------|
| Site-specific selector | `#my-site-login-btn` | ❌ Remove, use LLM |
| Element type selector | `input[type="email"]` | ✅ Keep |
| Semantic concept | `{'email', 'mail'}` | ✅ Keep |
| Service pattern | `.g-recaptcha` | ✅ Keep |
| Hardcoded keyword list in if/elif | `if 'email' in x:` | ⚠️ Convert to concept group |

---

## 10. Files Changed

See `migration_plan.md` for complete list of refactored files.

### Key files:
- `curllm_core/llm_dsl/selector_generator.py` - **NEW**
- `curllm_core/llm_dsl/element_finder.py` - **NEW**
- `curllm_core/form_fill/js_scripts.py` - **REFACTORED**
- `curllm_core/dom/helpers.py` - **REFACTORED**
- `curllm_core/orchestrators/auth.py` - **REFACTORED**
- `curllm_core/orchestrators/social.py` - **REFACTORED**
