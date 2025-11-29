# LLM Form Orchestrator - Delegacja Decyzji do LLM

## 🎯 Koncepcja

Zamiast hardcodować logikę wypełniania formularzy, **LLM podejmuje decyzje** na podstawie:
- Wykrytych pól formularza (jak DOM tree)
- Dostępnych operacji (fill, split, check, etc.)
- Instrukcji użytkownika

**LLM = Mózg (planowanie)**
**Python Functions = Ręce (wykonanie)**

---

## 📊 Architektura

```
┌─────────────────────────────────────────────────────────────┐
│  1. FORM ANALYSIS (JavaScript w przeglądarce)               │
│     ↓ Wykrywa pola, typy, relacje                           │
├─────────────────────────────────────────────────────────────┤
│  2. CONTEXT PREPARATION (Python)                            │
│     ↓ Przygotowuje dane dla LLM                             │
├─────────────────────────────────────────────────────────────┤
│  3. LLM PLANNING (qwen2.5, GPT-4, etc.)                     │
│     ↓ LLM tworzy plan wypełnienia                           │
├─────────────────────────────────────────────────────────────┤
│  4. PLAN EXECUTION (Python + Playwright)                    │
│     ↓ Wykonuje operacje z planu                             │
├─────────────────────────────────────────────────────────────┤
│  5. VALIDATION & REPORTING                                  │
│     ✅ Raportuje wyniki                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 Przykład Flow

### Krok 1: Analiza Formularza

JavaScript wykrywa pola i zwraca strukturę:

```json
{
  "detected_fields": [
    {
      "id": "name_first",
      "type": "text",
      "selector": "[data-curllm-target='name_first']",
      "required": true,
      "label_hint": "First Name"
    },
    {
      "id": "name_last",
      "type": "text",
      "selector": "[data-curllm-target='name_last']",
      "required": true,
      "label_hint": "Last Name"
    },
    {
      "id": "email",
      "type": "text",
      "selector": "[data-curllm-target='email']",
      "required": true,
      "label_hint": "Email"
    },
    {
      "id": "message",
      "type": "textarea",
      "selector": "[data-curllm-target='message']",
      "required": true,
      "label_hint": "Message"
    },
    {
      "id": "consent",
      "type": "checkbox",
      "selector": "[data-curllm-target='consent']",
      "required": true,
      "label_hint": "GDPR/Privacy Consent"
    }
  ],
  "field_relationships": [
    {
      "type": "split_name",
      "fields": ["name_first", "name_last"],
      "description": "Name field is split into First and Last name",
      "requires_splitting": true
    }
  ]
}
```

### Krok 2: Dostępne Operacje

System udostępnia LLM listę operacji (jak narzędzia):

```json
[
  {
    "operation": "fill_text",
    "description": "Fill a text input or textarea field with a value",
    "parameters": {
      "field_id": "ID of the field to fill",
      "value": "Text value to fill"
    }
  },
  {
    "operation": "split_name",
    "description": "Split a full name into first and last name",
    "parameters": {
      "full_name": "Full name to split (e.g., 'John Doe')",
      "first_field_id": "ID of first name field",
      "last_field_id": "ID of last name field"
    }
  },
  {
    "operation": "check_checkbox",
    "description": "Check a checkbox (consent, terms, etc.)",
    "parameters": {
      "field_id": "ID of checkbox field"
    }
  },
  {
    "operation": "click_submit",
    "description": "Click the submit button",
    "parameters": {
      "field_id": "ID of submit button"
    }
  }
]
```

### Krok 3: LLM Prompt

```
USER INSTRUCTION:
Fill contact form: name=John Doe, email=john@example.com, message=Hello test

USER DATA EXTRACTED:
{
  "name": "John Doe",
  "email": "john@example.com",
  "message": "Hello test"
}

DETECTED FORM FIELDS:
[... fields from step 1 ...]

AVAILABLE OPERATIONS:
[... operations from step 2 ...]

TASK:
Create a step-by-step plan to fill this form.
```

### Krok 4: LLM Response (Plan)

```json
{
  "plan": [
    {
      "operation": "split_name",
      "full_name": "John Doe",
      "first_field_id": "name_first",
      "last_field_id": "name_last"
    },
    {
      "operation": "fill_text",
      "field_id": "email",
      "value": "john@example.com"
    },
    {
      "operation": "fill_text",
      "field_id": "message",
      "value": "Hello test"
    },
    {
      "operation": "check_checkbox",
      "field_id": "consent"
    },
    {
      "operation": "click_submit",
      "field_id": "submit"
    }
  ],
  "reasoning": "The form has split name fields (first/last), so I'll use split_name operation. Email and message are standard text fields. Consent checkbox is required. Finally, submit the form."
}
```

### Krok 5: Wykonanie Planu

```
🤖 Executing LLM-generated form plan:
   Step 1: split_name
      🔀 Split 'John Doe' → First: 'John', Last: 'Doe'
      ▶️  Filling name_first: 'John'
      ▶️  Filling name_last: 'Doe'
   
   Step 2: fill_text
      ▶️  Filling email: 'john@example.com'
   
   Step 3: fill_text
      ▶️  Filling message: 'Hello test'
   
   Step 4: check_checkbox
      ☑️  Checking checkbox: consent
   
   Step 5: click_submit
      🚀 Clicking submit button
   
✅ Plan executed successfully: 5/5 operations completed
```

---

## 🚀 Zalety Rozwiązania

### 1. **Elastyczność**
LLM może obsłużyć niestandardowe formularze bez zmian w kodzie:
- Formularze z 3 polami name (First, Middle, Last)
- Formularze z polami Title/Suffix
- Nietypowe kombinacje pól

### 2. **Samodokumentacja**
LLM dodaje `reasoning` - widzimy DLACZEGO wybrał daną strategię:
```json
{
  "reasoning": "Detected WPForms split name pattern. Will use split_name operation to handle First/Last fields separately."
}
```

### 3. **Łatwe Debugowanie**
Gdy coś nie działa, widzimy:
- Co LLM wykrył
- Jaką strategię wybrał
- Która operacja zawiodła

### 4. **Rozszerzalność**
Nowe operacje dodajesz tylko w jednym miejscu:
```python
operations.append({
    "operation": "fill_date",
    "description": "Fill a date picker field",
    "parameters": {...}
})
```

LLM automatycznie zacznie ich używać!

### 5. **Inteligentne Fallbacki**
LLM może sam decydować o strategii:
```json
{
  "reasoning": "Email field not detected by selector. Will try filling 'name' field with email as fallback.",
  "plan": [
    {"operation": "fill_text", "field_id": "name", "value": "john@example.com"}
  ]
}
```

---

## 🔧 Integracja z Istniejącym Kodem

### Wariant 1: Full LLM Orchestration

```python
from curllm_core.llm_form_orchestrator import llm_orchestrated_form_fill

# LLM kontroluje cały proces
result = await llm_orchestrated_form_fill(
    instruction="Fill contact form: name=John Doe, email=john@example.com",
    page=page,
    llm=executor.llm,
    run_logger=run_logger
)
```

### Wariant 2: Hybrid (Istniejący + LLM)

```python
from curllm_core.form_fill import deterministic_form_fill
from curllm_core.llm_form_orchestrator import (
    analyze_form_fields,
    get_available_operations,
    create_llm_prompt
)

# 1. Wykryj pola (istniejący kod)
selectors = await page.evaluate("""...""")  # Existing JS

# 2. Jeśli złożony formularz, pytaj LLM
if selectors.get("_split_name") or len(selectors) > 10:
    fields_info = analyze_form_fields(selectors)
    operations = get_available_operations()
    prompt = create_llm_prompt(instruction, fields_info, operations, user_data)
    
    # LLM planuje
    llm_response = await llm.generate(prompt)
    plan = parse_llm_plan(llm_response)
    
    # Wykonaj plan
    result = await execute_form_plan(plan, page, selectors, run_logger)
else:
    # Prosty formularz - użyj istniejącego kodu
    result = await deterministic_form_fill(instruction, page, run_logger)
```

### Wariant 3: LLM jako Validator

```python
# 1. Wypełnij formularz (istniejący kod)
result = await deterministic_form_fill(...)

# 2. Jeśli błąd, pytaj LLM o strategię naprawy
if not result.get("submitted"):
    # LLM proponuje alternatywną strategię
    plan = await llm_suggest_alternative(errors, fields_info)
    result = await execute_form_plan(plan, page, selectors)
```

---

## 📝 Definicja Operacji

System używa formatu podobnego do **OpenAI Function Calling**:

```python
{
    "operation": "operation_name",
    "description": "What this operation does",
    "parameters": {
        "param1": "description",
        "param2": "description"
    },
    "example": {...}
}
```

### Dostępne Operacje (MVP)

1. **fill_text** - Wypełnia pole tekstowe
2. **split_name** - Dzieli nazwę na First/Last
3. **check_checkbox** - Zaznacza checkbox
4. **click_submit** - Klika submit
5. **validate_field** - Waliduje wartość pola

### Przyszłe Operacje

6. **fill_date** - Wypełnia date picker
7. **select_option** - Wybiera z dropdown
8. **upload_file** - Upload pliku
9. **fill_captcha** - Rozwiązuje CAPTCHA (z zewnętrznym API)
10. **conditional_fill** - Wypełnia pole tylko jeśli warunek spełniony

---

## 🎓 Przykłady Użycia

### Przykład 1: WPForms Split Name

**Instrukcja:**
```
Fill contact form: name=John Doe, email=john@example.com
```

**LLM Plan:**
```json
{
  "plan": [
    {"operation": "split_name", "full_name": "John Doe", "first_field_id": "name_first", "last_field_id": "name_last"},
    {"operation": "fill_text", "field_id": "email", "value": "john@example.com"},
    {"operation": "check_checkbox", "field_id": "consent"},
    {"operation": "click_submit", "field_id": "submit"}
  ]
}
```

### Przykład 2: Formularz z Title

**Wykryte pola:**
```json
["title", "first_name", "last_name", "email"]
```

**LLM Plan:**
```json
{
  "plan": [
    {"operation": "select_option", "field_id": "title", "value": "Mr."},
    {"operation": "fill_text", "field_id": "first_name", "value": "John"},
    {"operation": "fill_text", "field_id": "last_name", "value": "Doe"},
    {"operation": "fill_text", "field_id": "email", "value": "john@example.com"}
  ],
  "reasoning": "Detected a title/prefix field. Will fill it with 'Mr.' based on the first name 'John'."
}
```

### Przykład 3: Brak Pola Email

**Wykryte pola:**
```json
["name", "message", "consent"]
```

**User data:**
```json
{"name": "John Doe", "email": "john@example.com", "message": "Hello"}
```

**LLM Plan:**
```json
{
  "plan": [
    {"operation": "fill_text", "field_id": "name", "value": "John Doe"},
    {"operation": "fill_text", "field_id": "message", "value": "Hello\n\nEmail: john@example.com"},
    {"operation": "check_checkbox", "field_id": "consent"},
    {"operation": "click_submit", "field_id": "submit"}
  ],
  "reasoning": "Email field not detected in form. Adding email address to the message field as a workaround."
}
```

**To pokazuje inteligencję LLM!** 🧠

---

## 🔮 Przyszłe Usprawnienia

### 1. **Learning from Failures**
```python
# Zapisuj nieudane próby
if not result["submitted"]:
    save_failure_case(form_structure, llm_plan, errors)

# Przy następnej próbie, LLM uczy się z historii
prompt += f"\n\nPrevious attempts that failed:\n{get_similar_failures()}"
```

### 2. **Multi-step Forms**
```json
{
  "plan": [
    {"operation": "fill_text", "field_id": "email", "value": "john@example.com"},
    {"operation": "click_button", "field_id": "next_step"},
    {"operation": "wait", "duration_ms": 2000},
    {"operation": "fill_text", "field_id": "password", "value": "..."},
    {"operation": "click_submit"}
  ]
}
```

### 3. **Conditional Logic**
```json
{
  "operation": "conditional_fill",
  "condition": "if field 'company' exists",
  "then": {"operation": "fill_text", "field_id": "company", "value": "..."},
  "else": {"operation": "skip"}
}
```

### 4. **Error Recovery**
```python
try:
    result = execute_plan(plan)
except FormError as e:
    # LLM tworzy plan naprawy
    recovery_plan = llm.create_recovery_plan(e, current_state)
    result = execute_plan(recovery_plan)
```

---

## 🧪 Testowanie

```bash
# Test z logowaniem decyzji LLM
curllm --visual --stealth \
  --llm-orchestrator \
  --log-llm-decisions \
  "https://softreck.com/contact/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com"
  }' -v
```

**Log pokaże:**
```
🤖 LLM Form Orchestrator - Starting
   User data: {'name': 'John Doe', 'email': 'john@example.com'}
   
📊 Detected fields: 4 fields, 1 relationship (split_name)
   
🧠 LLM Planning...
   Prompt tokens: 1234
   Response tokens: 234
   
📋 Generated plan: 5 operations
   1. split_name: 'John Doe' → First/Last
   2. fill_text: email
   3. fill_text: message
   4. check_checkbox: consent
   5. click_submit
   
🤖 Executing plan...
   [... execution logs ...]
   
✅ Success: Form submitted
```

---

## 💡 Wnioski

### Dlaczego To Działa?

1. **Separation of Concerns**
   - LLM: Myślenie (co zrobić?)
   - Python: Wykonanie (jak to zrobić?)

2. **Podobne do Human Reasoning**
   - Człowiek: "Widzę pola First/Last, więc podzielę nazwę"
   - LLM: Identyczny proces myślowy

3. **Extensible**
   - Nowa operacja = 1 dodanie do listy
   - LLM automatycznie się uczy

4. **Debuggable**
   - Widzisz plan LLM
   - Widzisz wykonanie
   - Widzisz gdzie zawiodło

### Kiedy Używać?

✅ **LLM Orchestrator:**
- Złożone formularze (split fields, conditional logic)
- Niestandardowe struktury
- Gdy deterministyczny kod zawodzi

❌ **Deterministyczny kod:**
- Proste formularze (name, email, message)
- Znane wzorce (Contact Form 7, Forminator)
- Gdy szybkość jest kluczowa

**Hybrid:** Najlepsze z obu światów! 🎯
