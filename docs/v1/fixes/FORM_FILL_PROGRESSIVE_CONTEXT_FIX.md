# Fix: Form Fill Progressive Context (2025-11-28)

## Problem

Formularz nie był wysyłany, bo LLM otrzymywał minimalny kontekst BEZ danych formularza:

```
📊 Progressive Context: step=0, size=443 chars (links:0, headings:5, forms:0, has_dom:False)
```

LLM odpowiedział:
> "The provided page context does not contain any form elements" → `type: complete` bez wypełnienia.

## Przyczyna Root Cause

W `progressive_context.py` logika dodawania formularzy była **wewnątrz** bloku `if step <= 2:`, co mogło powodować problemy z kolejnością wykonania i scope'em zmiennych.

## Rozwiązanie

Przeniesiono logikę dodawania formularzy **PRZED** blokiem step-based:

```python
# PRZED: formularze dodawane wewnątrz step-based logic
if step <= 2:
    # ... minimal setup ...
    if is_form_task:
        forms = page_context.get("forms", [])  # <- mogło nie działać
        if forms:
            minimal["forms"] = forms[:3]

# PO: formularze dodawane ZAWSZE dla form tasks, niezależnie od step
if is_form_task:
    forms = page_context.get("forms", [])
    if forms:
        minimal["forms"] = forms[:3]
    # ... interactive, buttons ...

if step <= 2:
    # ... minimal headings/links ...
```

## Zmiany w Pliku

**`curllm_core/progressive_context.py`:**
1. Dodano guard `if not instruction: return False` w `_is_form_task()`
2. Przeniesiono logikę formularzy przed block step-based
3. Dodano więcej keywords: `"wyślij"`, `"kontakt"`, `"rejestr"`
4. Dodano debug flag `_is_form_task` w kontekście
5. Dodano filtrowanie `forminator` w interactive elements

## Weryfikacja

Po poprawce, kontekst powinien zawierać:
```json
{
  "title": "...",
  "url": "...",
  "forms": [{"id": "forminator-module-5574", "fields": [...]}],
  "interactive": [{"tag": "input", "attrs": {"id": "forminator-field-email-1"}}],
  "buttons": [{"text": "WYŚLIJ ZAPYTANIE"}],
  "headings": [...],
  "_is_form_task": true
}
```

## Test

```bash
curllm --visual --stealth "https://www.prototypowanie.pl/" \
  -d "Fill form: name=John Doe, email=john@example.com"
```

Oczekiwany wynik:
- `forms:X` > 0 w Progressive Context
- LLM wykona `type: fill` lub `type: tool` zamiast `type: complete`
