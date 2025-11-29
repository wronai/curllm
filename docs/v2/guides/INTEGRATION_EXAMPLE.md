# Integracja LLM Orchestrator z Form Fill

## Problem: softreck.com WPForms

### Obecne Rozwiązanie (Hardcoded)

```python
# form_fill.py - linie 220-235
# HARDCODED logic dla split name:
const firstNameEl = findField(['first','firstname'], 'input', targetForm);
const lastNameEl = findField(['last','lastname'], 'input', targetForm);

if (firstNameEl && lastNameEl) {
    res.name_first = mark(firstNameEl, 'name_first');
    res.name_last = mark(lastNameEl, 'name_last');
    res._split_name = true;
} else {
    const nameEl = findField(['name','fullname'], 'input', targetForm);
    if (nameEl) res.name = mark(nameEl, 'name');
}
```

**Problemy:**
- ❌ Trzeba przewidzieć WSZYSTKIE możliwe kombinacje
- ❌ Co jeśli jest First, Middle, Last?
- ❌ Co jeśli jest Title, First, Last, Suffix?
- ❌ Kod rośnie ekspotencjalnie

### Nowe Rozwiązanie (LLM Orchestrator)

```python
# 1. Wykryj WSZYSTKIE pola (bez logiki)
all_fields = detect_all_input_fields(page)
# → ["title", "first_name", "middle_name", "last_name", "suffix", "email"]

# 2. Pytaj LLM jak je wypełnić
plan = llm.plan_form_filling(
    instruction="name=Dr. John Michael Doe Jr.",
    fields=all_fields,
    operations=available_operations
)

# 3. LLM zwraca plan:
{
  "plan": [
    {"operation": "fill_text", "field_id": "title", "value": "Dr."},
    {"operation": "fill_text", "field_id": "first_name", "value": "John"},
    {"operation": "fill_text", "field_id": "middle_name", "value": "Michael"},
    {"operation": "fill_text", "field_id": "last_name", "value": "Doe"},
    {"operation": "fill_text", "field_id": "suffix", "value": "Jr."}
  ]
}

# 4. Wykonaj plan
execute_plan(plan, page, selectors)
```

**Zalety:**
- ✅ Nie trzeba przewidywać kombinacji
- ✅ LLM rozumie kontekst
- ✅ Kod nie rośnie

---

## Implementacja Krok po Kroku

### Krok 1: Rozszerz Detekcję Pól

Zamiast szukać konkretnych pól, wykryj WSZYSTKIE:

```python
# curllm_core/form_detector.py (NOWY MODUŁ)

async def detect_all_form_fields(page, target_form_selector=None) -> List[Dict]:
    """
    Wykrywa WSZYSTKIE pola w formularzu bez klasyfikacji.
    LLM sam zdecyduje co z nimi zrobić.
    """
    fields = await page.evaluate(
        """
        (formSelector) => {
          const form = formSelector ? document.querySelector(formSelector) : document.querySelector('form');
          if (!form) return [];
          
          const fields = [];
          const inputs = form.querySelectorAll('input, textarea, select');
          
          inputs.forEach((el, idx) => {
            // Skip hidden, submit, button types
            if (el.type === 'hidden' || el.type === 'submit' || el.type === 'button') return;
            
            // Collect metadata
            const field = {
              index: idx,
              tag: el.tagName.toLowerCase(),
              type: el.type || 'text',
              id: el.id || null,
              name: el.name || null,
              placeholder: el.placeholder || null,
              required: el.required || false,
              value: el.value || '',
              
              // Label detection
              label: null,
              label_text: null
            };
            
            // Try to find label
            if (el.id) {
              const label = document.querySelector(`label[for="${el.id}"]`);
              if (label) {
                field.label = label.innerText?.trim();
              }
            }
            
            // If no label found, check parent/previous elements
            if (!field.label) {
              const parent = el.closest('.forminator-field, .wpforms-field, .gfield');
              if (parent) {
                const label = parent.querySelector('label');
                if (label) field.label = label.innerText?.trim();
              }
            }
            
            // Extract hints from class names
            field.class_hints = [];
            if (el.className) {
              const classes = el.className.split(' ');
              classes.forEach(cls => {
                if (cls.includes('first')) field.class_hints.push('first_name');
                if (cls.includes('last')) field.class_hints.push('last_name');
                if (cls.includes('middle')) field.class_hints.push('middle_name');
                if (cls.includes('email')) field.class_hints.push('email');
                if (cls.includes('phone')) field.class_hints.push('phone');
                if (cls.includes('message')) field.class_hints.push('message');
              });
            }
            
            fields.push(field);
          });
          
          return fields;
        }
        """,
        target_form_selector
    )
    
    return fields
```

### Krok 2: Prompt dla LLM

```python
def create_form_filling_prompt(instruction: str, fields: List[Dict], user_data: Dict) -> str:
    """
    Tworzy prompt dla LLM z PEŁNYM kontekstem.
    """
    return f"""You are a web form automation expert. Analyze the detected form fields and create a plan to fill them.

USER INSTRUCTION:
{instruction}

EXTRACTED USER DATA:
{json.dumps(user_data, indent=2)}

DETECTED FORM FIELDS:
{json.dumps(fields, indent=2)}

AVAILABLE OPERATIONS:
- fill_text: Fill text input or textarea
- split_name: Split full name into components (first, middle, last, etc.)
- check_checkbox: Check a checkbox
- select_option: Select from dropdown
- click_button: Click a button

ANALYSIS GUIDELINES:

1. NAME FIELD PATTERNS:
   - If you see "first" and "last" fields → split full name
   - If you see "title", "first", "last", "suffix" → extract all components
   - If only one "name" field → use full name as-is
   - Common patterns:
     * first_name + last_name
     * title + first + middle + last + suffix
     * fullname (single field)

2. EMAIL FIELD:
   - Match by: type="email", label contains "email/e-mail/mail"
   - If not found, can append to message field

3. PHONE FIELD:
   - Match by: label contains "phone/telefon/tel"
   - Format: Keep as provided or strip non-digits if needed

4. MESSAGE/COMMENT FIELD:
   - Usually textarea
   - Label contains: message, comment, wiadomość, komentarz

5. CHECKBOXES:
   - Consent/GDPR: label contains consent, privacy, RODO, zgoda
   - Always check if required

TASK:
Create a step-by-step filling plan. Return JSON only.

EXAMPLE RESPONSE:
```json
{{
  "analysis": {{
    "form_type": "WPForms",
    "detected_pattern": "split_name_first_last",
    "required_fields": ["first_name", "last_name", "email"],
    "optional_fields": ["phone", "message"]
  }},
  "plan": [
    {{
      "operation": "fill_text",
      "field_index": 0,
      "field_id": "wpforms-260-field_0",
      "inferred_purpose": "first_name",
      "value": "John",
      "reasoning": "Field has class 'wpforms-field-name-first' and label 'First'"
    }},
    {{
      "operation": "fill_text",
      "field_index": 1,
      "field_id": "wpforms-260-field_0-last",
      "inferred_purpose": "last_name",
      "value": "Doe",
      "reasoning": "Field has class 'wpforms-field-name-last' and label 'Last'"
    }},
    {{
      "operation": "fill_text",
      "field_index": 2,
      "field_id": "wpforms-260-field_1",
      "inferred_purpose": "email",
      "value": "john@example.com",
      "reasoning": "Field type is 'email' and label is 'E-mail'"
    }},
    {{
      "operation": "check_checkbox",
      "field_index": 5,
      "field_id": "wpforms-260-field_3_1",
      "inferred_purpose": "consent",
      "reasoning": "Checkbox with label containing 'consent' and 'privacy'"
    }}
  ]
}}
```

Generate the plan now:"""
```

### Krok 3: Wykonanie Planu

```python
async def execute_llm_plan(plan: Dict, page, run_logger=None) -> Dict:
    """
    Wykonuje plan wygenerowany przez LLM.
    """
    result = {
        "executed": [],
        "errors": [],
        "submitted": False
    }
    
    if run_logger:
        run_logger.log_text("🤖 Executing LLM-generated plan:")
        run_logger.log_text(f"   Analysis: {plan.get('analysis', {})}")
    
    for step in plan.get("plan", []):
        operation = step.get("operation")
        field_id = step.get("field_id")
        value = step.get("value")
        reasoning = step.get("reasoning", "")
        
        if run_logger:
            run_logger.log_text(f"   ▶️  {operation}: {field_id}")
            run_logger.log_text(f"      Reasoning: {reasoning}")
        
        try:
            if operation == "fill_text":
                selector = f"#{field_id}" if not field_id.startswith("[") else field_id
                await page.fill(selector, value, timeout=3000)
                await page.evaluate(f"""
                    document.querySelector('{selector}')?.dispatchEvent(new Event('input', {{bubbles:true}}));
                    document.querySelector('{selector}')?.dispatchEvent(new Event('change', {{bubbles:true}}));
                """)
                result["executed"].append(step)
            
            elif operation == "check_checkbox":
                selector = f"#{field_id}"
                await page.check(selector)
                result["executed"].append(step)
        
        except Exception as e:
            if run_logger:
                run_logger.log_text(f"      ❌ Error: {str(e)}")
            result["errors"].append({
                "step": step,
                "error": str(e)
            })
    
    return result
```

### Krok 4: Integracja w task_runner.py

```python
# task_runner.py - dodaj nową opcję

async def _execute_tool(...):
    if tn == "form.fill":
        # Check if LLM orchestration is enabled
        use_llm_orchestrator = runtime.get("llm_form_orchestrator", False)
        
        if use_llm_orchestrator and getattr(executor, "llm", None):
            # LLM ORCHESTRATOR MODE
            from .form_detector import detect_all_form_fields
            from .llm_form_orchestrator import create_form_filling_prompt, execute_llm_plan
            
            # 1. Detect all fields
            fields = await detect_all_form_fields(page)
            
            # 2. Create prompt
            user_data = parse_form_pairs(instruction)
            prompt = create_form_filling_prompt(instruction, fields, user_data)
            
            # 3. Ask LLM
            llm_response = await executor.llm.generate(prompt, max_tokens=1000)
            plan = json.loads(llm_response)  # Parse JSON response
            
            # 4. Execute plan
            result = await execute_llm_plan(plan, page, run_logger)
            return {"form_fill": result}
        else:
            # DETERMINISTIC MODE (existing code)
            det = await executor._deterministic_form_fill(...)
            return {"form_fill": det}
```

---

## Przykład: softreck.com z LLM

### Input

```bash
curllm --visual --stealth \
  --llm-orchestrator \
  "https://softreck.com/contact/" \
  -d '{
    "instruction":"Fill contact form: name=John Doe, email=john@example.com, message=Hello test",
    "params":{"llm_form_orchestrator": true}
  }' -v
```

### LLM Otrzymuje

```json
{
  "user_data": {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello test"
  },
  "detected_fields": [
    {
      "index": 0,
      "tag": "input",
      "type": "text",
      "id": "wpforms-260-field_0",
      "name": "wpforms[fields][0][first]",
      "label": "First",
      "class_hints": ["first_name"],
      "required": true
    },
    {
      "index": 1,
      "tag": "input",
      "type": "text",
      "id": "wpforms-260-field_0-last",
      "name": "wpforms[fields][0][last]",
      "label": "Last",
      "class_hints": ["last_name"],
      "required": true
    },
    {
      "index": 2,
      "tag": "input",
      "type": "email",
      "id": "wpforms-260-field_1",
      "name": "wpforms[fields][1]",
      "label": "E-mail",
      "required": true
    },
    {
      "index": 3,
      "tag": "textarea",
      "id": "wpforms-260-field_2",
      "name": "wpforms[fields][2]",
      "label": "Comment or Message",
      "required": true
    },
    {
      "index": 4,
      "tag": "input",
      "type": "checkbox",
      "id": "wpforms-260-field_3_1",
      "label": "I consent to having this website store my submitted information...",
      "required": true
    }
  ]
}
```

### LLM Zwraca Plan

```json
{
  "analysis": {
    "form_type": "WPForms",
    "detected_pattern": "split_name_first_last",
    "name_strategy": "Split 'John Doe' into first='John' and last='Doe'",
    "required_fields": ["first_name", "last_name", "email", "message", "consent"],
    "confidence": "high"
  },
  "plan": [
    {
      "operation": "fill_text",
      "field_index": 0,
      "field_id": "wpforms-260-field_0",
      "inferred_purpose": "first_name",
      "value": "John",
      "reasoning": "Field name contains '[first]' and label is 'First'. Split from full name 'John Doe'."
    },
    {
      "operation": "fill_text",
      "field_index": 1,
      "field_id": "wpforms-260-field_0-last",
      "inferred_purpose": "last_name",
      "value": "Doe",
      "reasoning": "Field name contains '[last]' and label is 'Last'. Split from full name 'John Doe'."
    },
    {
      "operation": "fill_text",
      "field_index": 2,
      "field_id": "wpforms-260-field_1",
      "inferred_purpose": "email",
      "value": "john@example.com",
      "reasoning": "Field type='email' and label='E-mail'. Direct match from user data."
    },
    {
      "operation": "fill_text",
      "field_index": 3,
      "field_id": "wpforms-260-field_2",
      "inferred_purpose": "message",
      "value": "Hello test",
      "reasoning": "Textarea with label 'Comment or Message'. Direct match from user data."
    },
    {
      "operation": "check_checkbox",
      "field_index": 4,
      "field_id": "wpforms-260-field_3_1",
      "inferred_purpose": "consent",
      "reasoning": "Required checkbox with consent/privacy keywords in label."
    }
  ]
}
```

### Wykonanie

```
🤖 Executing LLM-generated plan:
   Analysis: WPForms split_name_first_last pattern detected
   
   ▶️  fill_text: wpforms-260-field_0
      Reasoning: Split from full name 'John Doe'
      ✅ Filled: 'John'
   
   ▶️  fill_text: wpforms-260-field_0-last
      Reasoning: Split from full name 'John Doe'
      ✅ Filled: 'Doe'
   
   ▶️  fill_text: wpforms-260-field_1
      Reasoning: Field type='email'
      ✅ Filled: 'john@example.com'
   
   ▶️  fill_text: wpforms-260-field_2
      Reasoning: Textarea with label 'Message'
      ✅ Filled: 'Hello test'
   
   ▶️  check_checkbox: wpforms-260-field_3_1
      Reasoning: Required consent checkbox
      ✅ Checked
   
✅ Plan executed: 5/5 operations successful
```

---

## Konfiguracja

### .env
```bash
# Włącz LLM orchestrator
CURLLM_LLM_FORM_ORCHESTRATOR=true

# Model LLM (musi wspierać JSON output)
CURLLM_MODEL=qwen2.5:14b

# Lub użyj OpenAI
CURLLM_USE_OPENAI=true
OPENAI_API_KEY=sk-...
CURLLM_OPENAI_MODEL=gpt-4-turbo-preview
```

### Runtime
```python
runtime = {
    "llm_form_orchestrator": True,  # Włącz LLM orchestrator
    "llm_orchestrator_fallback": True,  # Jeśli LLM zawiedzie, użyj deterministycznego
}
```

---

## Porównanie

| Aspekt | Deterministyczny | LLM Orchestrator |
|--------|-----------------|------------------|
| Szybkość | ⚡ Bardzo szybki | 🐌 Wolniejszy (LLM call) |
| Elastyczność | ❌ Sztywny | ✅ Bardzo elastyczny |
| Obsługa edge cases | ❌ Tylko przewidziane | ✅ Wszystkie |
| Debugowanie | ✅ Proste | ✅ Proste + reasoning |
| Koszty | 💰 Darmowy | 💰💰 Tokeny LLM |
| Maintenance | ❌ Dużo kodu | ✅ Minimalna |

**Rekomendacja: HYBRID**
- Proste formularze → Deterministyczny
- Złożone/niestandardowe → LLM Orchestrator
