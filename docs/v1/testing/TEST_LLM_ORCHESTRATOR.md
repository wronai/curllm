# Test LLM Orchestrator - softreck.com

## Cel Testu

Przetestować LLM Orchestrator na problemowym formularzu WPForms z softreck.com, który ma:
- ❌ Split name fields (First + Last)
- ❌ Email field wykrywany błędnie
- ✅ Message field
- ✅ GDPR checkbox

---

## Przygotowanie

### 1. Restart Serwera (OBOWIĄZKOWE!)

```bash
make stop && make clean && make start
```

To załaduje nowe moduły:
- `form_detector.py`
- `llm_form_orchestrator.py`
- Zaktualizowany `task_runner.py`

### 2. Włącz LLM Orchestrator

Dodaj do `.env`:
```bash
# Enable LLM Orchestrator for form filling
CURLLM_LLM_ORCHESTRATOR=true

# Or enable for all form tasks
CURLLM_LLM_FORM_ORCHESTRATOR=true
```

Lub użyj parametru runtime:
```bash
curllm ... -d '{
  "instruction":"...",
  "params":{"llm_form_orchestrator": true}
}'
```

---

## Test Command

### Wariant 1: Z .env

```bash
# Dodaj do .env
echo "CURLLM_LLM_ORCHESTRATOR=true" >> .env

# Uruchom test
curllm --visual --stealth --session test-llm \
  "https://softreck.com/contact/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, message=Hello test"
  }' -v
```

### Wariant 2: Runtime Parameter

```bash
curllm --visual --stealth --session test-llm \
  "https://softreck.com/contact/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, message=Hello test",
    "params":{"llm_form_orchestrator": true}
  }' -v
```

---

## Oczekiwane Logi

### Phase 1: Detection

```markdown
Tool call: form.fill

🤖 LLM Orchestrator mode enabled

🤖 LLM Form Orchestrator - Starting
   User data: {'name': 'John Doe', 'email': 'john@example.com', 'message': 'Hello test'}
   
📊 Detected: 5 fields, Form type: WPForms
```

### Phase 2: LLM Planning

```markdown
🧠 Asking LLM for filling plan...
✅ LLM responded (847 chars)
📋 Plan has 5 operations
```

### Phase 3: Execution

```markdown
🤖 Executing LLM-generated form plan:

   Step 1: fill_text
      Reasoning: First name field detected by hints
      ▶️  Filling wpforms-260-field_0
      ✅ Filled: 'John'
   
   Step 2: fill_text
      Reasoning: Last name field
      ▶️  Filling wpforms-260-field_0-last
      ✅ Filled: 'Doe'
   
   Step 3: fill_text
      Reasoning: Email field (type=email)
      ▶️  Filling wpforms-260-field_1
      ✅ Filled: 'john@example.com'
   
   Step 4: fill_text
      Reasoning: Message textarea
      ▶️  Filling wpforms-260-field_2
      ✅ Filled: 'Hello test'
   
   Step 5: check_checkbox
      Reasoning: Required consent checkbox
      ☑️  Checking checkbox: wpforms-260-field_3_1
```

### Phase 4: Result

```markdown
✅ LLM Orchestrator succeeded

{"submitted": true, "errors": null}

✅ Form successfully submitted - auto-completing task
```

---

## Oczekiwany Rezultat

### Screenshot Pokazuje:

- ✅ **Name First:** "John"
- ✅ **Name Last:** "Doe"
- ✅ **E-mail:** "john@example.com" (POPRAWNE!)
- ✅ **Message:** "Hello test"
- ✅ **GDPR Agreement:** CHECKED
- ⚠️ **hCaptcha:** Nierozwiązany (normalny blokant)

### Statystyki:

- **Steps taken:** 1 (tylko jeden step!)
- **Success:** true
- **Submitted:** true

---

## Porównanie: Przed vs Po

### PRZED (Deterministyczny)

```
⚠️  Fields in instruction but NOT in form: {'email', 'phone'}

Found selectors: ['name', 'message', 'consent', 'submit']

Wynik:
❌ Name First: PUSTE
❌ Name Last: PUSTE
❌ Email: "John Doe" (błąd!)
✅ Message: "Hello test"
```

### PO (LLM Orchestrator)

```
📊 Detected: 5 fields, Form type: WPForms

Fields:
- wpforms-260-field_0 (hints=['first_name'])
- wpforms-260-field_0-last (hints=['last_name'])
- wpforms-260-field_1 (type='email', hints=['email'])
- wpforms-260-field_2 (type='textarea', hints=['message'])
- wpforms-260-field_3_1 (type='checkbox', hints=['consent'])

Wynik:
✅ Name First: "John"
✅ Name Last: "Doe"
✅ Email: "john@example.com"
✅ Message: "Hello test"
✅ GDPR: CHECKED
```

---

## Fallback Test

Jeśli LLM zawiedzie, system automatycznie użyje deterministycznego:

```markdown
⚠️  LLM Orchestrator failed: Connection timeout, falling back to deterministic
🔧 Using deterministic form fill (fallback)

🔍 Form fill debug:
   🎯 Selected form: wpforms-form-260
   [... deterministic execution ...]
```

**Przewaga hybrydowego podejścia:** Nigdy nie zostaniesz bez działania!

---

## Debug: Zobacz Plan LLM

Jeśli chcesz zobaczyć DOKŁADNY plan LLM, dodaj do logu:

```python
# W llm_form_orchestrator.py, po parse_llm_plan:
if run_logger:
    run_logger.log_text(f"📋 LLM Plan:")
    run_logger.log_code("json", json.dumps(plan, indent=2))
```

Przykładowy plan:
```json
{
  "plan": [
    {
      "operation": "fill_text",
      "field_id": "wpforms-260-field_0",
      "value": "John",
      "reasoning": "First name field detected by hints=['first_name'] and label='First'"
    },
    {
      "operation": "fill_text",
      "field_id": "wpforms-260-field_0-last",
      "value": "Doe",
      "reasoning": "Last name field detected by hints=['last_name'] and label='Last'"
    },
    {
      "operation": "fill_text",
      "field_id": "wpforms-260-field_1",
      "value": "john@example.com",
      "reasoning": "Email field: type='email', hints=['email'], label='E-mail'"
    },
    {
      "operation": "fill_text",
      "field_id": "wpforms-260-field_2",
      "value": "Hello test",
      "reasoning": "Message field: type='textarea', label='Comment or Message'"
    },
    {
      "operation": "check_checkbox",
      "field_id": "wpforms-260-field_3_1",
      "reasoning": "Required GDPR consent checkbox"
    }
  ]
}
```

**Każda operacja ma `reasoning`** - widzisz DLACZEGO LLM wybrał daną strategię!

---

## Metryki Sukcesu

| Metryka | Target | Rzeczywiste |
|---------|--------|-------------|
| Name First wypełnione | ✅ | ? |
| Name Last wypełnione | ✅ | ? |
| Email poprawny | ✅ | ? |
| Message wypełnione | ✅ | ? |
| GDPR checked | ✅ | ? |
| Steps taken | 1 | ? |
| Submitted | true | ? |
| Success | true | ? |

---

## Troubleshooting

### Problem 1: LLM nie odpowiada

```
⚠️  LLM Orchestrator failed: Timeout
```

**Rozwiązanie:**
- Sprawdź czy Ollama działa: `curl http://localhost:11434/api/tags`
- Sprawdź czy model jest załadowany: `ollama list`
- Zwiększ timeout w konfiguracji

### Problem 2: LLM zwraca nieprawidłowy JSON

```
⚠️  Could not parse LLM plan, falling back
```

**Rozwiązanie:**
- Zobacz raw response LLM w logach
- Model może nie wspierać JSON output - użyj GPT-4 lub Claude
- Dodaj więcej przykładów w prompcie

### Problem 3: Pola nadal źle wypełnione

```
✅ LLM Orchestrator succeeded
❌ Ale pola są błędne
```

**Rozwiązanie:**
- Zobacz "Detected fields" w logu - czy hints są poprawne?
- Zobacz "LLM Plan" - czy field_id są poprawne?
- Może być problem z selektorami - sprawdź `selectors` map

---

## Konfiguracja Zaawansowana

### Użyj GPT-4 zamiast Ollama

```bash
# .env
CURLLM_USE_OPENAI=true
OPENAI_API_KEY=sk-...
CURLLM_OPENAI_MODEL=gpt-4-turbo-preview
CURLLM_LLM_ORCHESTRATOR=true
```

GPT-4 jest **ZNACZNIE lepszy** w JSON output i rozumowaniu!

### Logowanie Decyzji LLM

```bash
# .env
CURLLM_LOG_LLM_DECISIONS=true
CURLLM_LOG_LLM_PROMPTS=true
```

To zapisze w logu:
- Pełny prompt wysłany do LLM
- Raw response LLM
- Parsed plan

---

## Co Dalej?

### Po Udanym Teście:

1. **Włącz dla wszystkich formularzy:**
   ```bash
   echo "CURLLM_LLM_ORCHESTRATOR=true" >> .env
   ```

2. **Zbieraj udane plany:**
   ```python
   # Zapisuj plany do późniejszego użycia jako few-shot examples
   save_successful_plan(form_type, plan)
   ```

3. **Rozszerzaj operacje:**
   ```python
   # Dodaj nowe operacje stopniowo
   operations.append({"operation": "select_dropdown", ...})
   operations.append({"operation": "upload_file", ...})
   ```

4. **Testuj na innych formularzach:**
   - Gravity Forms
   - Elementor Forms
   - Custom HTML5 Forms

---

## Sukces Oznacza:

✅ **Name fields poprawnie rozpoznane i wypełnione**
✅ **Email w poprawnym polu**
✅ **Message wypełnione**
✅ **GDPR checkbox zaznaczony**
✅ **Tylko 1 step (auto-complete działa)**
✅ **Form submitted = true**

🎉 **LLM Orchestrator rozwiązuje problem WPForms!**
